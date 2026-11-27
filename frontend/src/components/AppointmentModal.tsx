import {
  Button,
  Checkbox,
  ComposedModal,
  InlineNotification,
  ModalBody,
  ModalFooter,
  ModalHeader,
  Select,
  SelectItem,
  SkeletonText,
  Stack,
  Tag,
  TextInput,
} from '@carbon/react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { TFunction } from 'i18next'
import {
  api,
  isFrontDesk,
  isManager,
  type Appointment,
  type HistoryEntry,
  type Me,
  type Practitioner,
} from '../lib/api'
import { clinicDate, clinicIso, formatDateTime, formatTime } from '../lib/time'
import { useErrorText, useSlots } from './slots'
import { StatusTag } from './StatusTag'

type Mode = 'view' | 'reschedule' | 'cancel'

/** One appointment: details, history and the actions staff may take (FR-013, FR-016). */
export function AppointmentModal({
  me,
  appointment: a,
  practitioners,
  onChange,
  onClose,
}: {
  me: Me
  appointment: Appointment
  practitioners: Practitioner[]
  onChange: (a: Appointment) => void
  onClose: () => void
}) {
  const { t, i18n } = useTranslation()
  const lang = i18n.language
  const queryClient = useQueryClient()
  const errorText = useErrorText()
  const [mode, setMode] = useState<Mode>('view')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const history = useQuery({
    queryKey: ['appointments', 'history', a.id, a.status, a.starts_at],
    queryFn: () => api<HistoryEntry[]>(`/appointments/${a.id}/history/`),
  })

  const active = a.status === 'booked' || a.status === 'confirmed'
  const canAct = isFrontDesk(me) && active
  const [now] = useState(() => Date.now())
  const started = Date.parse(a.starts_at) <= now

  async function post(path: string, body: object = {}) {
    setBusy(true)
    setError(null)
    try {
      const updated = await api<Appointment>(`/appointments/${a.id}/${path}/`, {
        method: 'POST',
        body: JSON.stringify(body),
      })
      await queryClient.invalidateQueries({ queryKey: ['appointments'] })
      await queryClient.invalidateQueries({ queryKey: ['slots'] })
      onChange(updated)
      setMode('view')
    } catch (err) {
      setError(errorText(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <ComposedModal open onClose={onClose} size="sm" preventCloseOnClickOutside={mode !== 'view'}>
      <ModalHeader
        label={`${t('appt.reference')} ${a.reference}`}
        title={a.patient_name}
        closeModal={onClose}
      />
      <ModalBody>
        <Stack gap={5}>
          {error && <InlineNotification kind="error" lowContrast hideCloseButton title={error} />}
          <dl className="details">
            <dt>{t('status')}</dt>
            <dd>
              <StatusTag status={a.status} />
              {a.outside_hours && (
                <Tag type="purple" size="sm">
                  {t('appt.outsideHours')}
                </Tag>
              )}
            </dd>
            <dt>{t('appt.when')}</dt>
            <dd>
              {formatDateTime(a.starts_at, lang)}–{formatTime(a.ends_at, lang)}
            </dd>
            <dt>{t('appt.practitioner')}</dt>
            <dd>{a.practitioner_name}</dd>
            <dt>{t('appt.service')}</dt>
            <dd>{a.service_name}</dd>
            {a.patient_phone && (
              <>
                <dt>{t('appt.phone')}</dt>
                <dd>
                  <a href={`tel:${a.patient_phone}`}>{a.patient_phone}</a>
                </dd>
              </>
            )}
            {a.cancel_reason && (
              <>
                <dt>{t('appt.cancelReason')}</dt>
                <dd>{a.cancel_reason}</dd>
              </>
            )}
          </dl>

          {mode === 'reschedule' && (
            <Reschedule
              me={me}
              appointment={a}
              practitioners={practitioners}
              busy={busy}
              onSubmit={(body) => post('reschedule', body)}
              onCancel={() => setMode('view')}
            />
          )}
          {mode === 'cancel' && (
            <CancelForm
              busy={busy}
              onSubmit={(reason) => post('cancel', { reason })}
              onCancel={() => setMode('view')}
            />
          )}

          <section>
            <h3 className="cds--type-heading-compact-01 section-title">{t('appt.history')}</h3>
            {history.isLoading ? (
              <SkeletonText paragraph lineCount={2} />
            ) : (
              <ol className="history">
                {(history.data ?? []).map((h, i) => (
                  <li key={i}>
                    <span className="history__what">{describe(h, t, lang)}</span>
                    <span className="history__who">
                      {formatDateTime(h.at, lang)}
                      {h.actor ? ` · ${h.actor}` : ''}
                    </span>
                  </li>
                ))}
              </ol>
            )}
          </section>
        </Stack>
      </ModalBody>
      {canAct && mode === 'view' && (
        <ModalFooter className="appt-actions">
          <Button kind="danger--ghost" disabled={busy} onClick={() => setMode('cancel')}>
            {t('appt.cancel')}
          </Button>
          {started ? (
            <Button kind="secondary" disabled={busy} onClick={() => post('no-show')}>
              {t('appt.markNoShow')}
            </Button>
          ) : (
            <Button kind="secondary" disabled={busy} onClick={() => setMode('reschedule')}>
              {t('appt.reschedule')}
            </Button>
          )}
          {a.status === 'booked' && (
            <Button kind="primary" disabled={busy} onClick={() => post('confirm')}>
              {t('appt.confirm')}
            </Button>
          )}
        </ModalFooter>
      )}
    </ComposedModal>
  )
}

function describe(h: HistoryEntry, t: TFunction, lang: string): string {
  const d = h.detail
  switch (h.action) {
    case 'appointment.create':
      return t('history.created')
    case 'appointment.reschedule':
      return t('history.moved', {
        from: typeof d.from_starts_at === 'string' ? formatDateTime(d.from_starts_at, lang) : '',
        to: typeof d.starts_at === 'string' ? formatDateTime(d.starts_at, lang) : '',
      })
    case 'appointment.status':
      return t('history.status', { status: t(`statuses.${String(d.to)}`) })
    case 'appointment.update':
      return t('history.edited')
    default:
      return h.action
  }
}

function Reschedule({
  me,
  appointment: a,
  practitioners,
  busy,
  onSubmit,
  onCancel,
}: {
  me: Me
  appointment: Appointment
  practitioners: Practitioner[]
  busy: boolean
  onSubmit: (body: object) => void
  onCancel: () => void
}) {
  const { t, i18n } = useTranslation()
  const today = clinicDate()
  const [practitioner, setPractitioner] = useState(String(a.practitioner))
  const [date, setDate] = useState(clinicDate(a.starts_at) < today ? today : clinicDate(a.starts_at))
  const [slot, setSlot] = useState('')
  const [override, setOverride] = useState(false)
  const [overrideTime, setOverrideTime] = useState('')
  const slots = useSlots(practitioner, a.service, date)
  const startsAt = override ? (overrideTime ? clinicIso(date, overrideTime) : '') : slot

  return (
    <div className="inline-form">
      <h3 className="cds--type-heading-compact-01 section-title">{t('appt.newTime')}</h3>
      <Stack gap={5}>
        <Select
          id="move-practitioner"
          labelText={t('appt.practitioner')}
          value={practitioner}
          onChange={(e) => {
            setPractitioner(e.target.value)
            setSlot('')
          }}
        >
          {practitioners.map((p) => (
            <SelectItem key={p.id} value={String(p.id)} text={p.display_name} />
          ))}
        </Select>
        <TextInput
          id="move-date"
          type="date"
          labelText={t('appt.date')}
          value={date}
          min={today}
          onChange={(e) => {
            setDate(e.target.value)
            setSlot('')
          }}
        />
        {override ? (
          <TextInput
            id="move-time"
            type="time"
            labelText={t('appt.time')}
            value={overrideTime}
            onChange={(e) => setOverrideTime(e.target.value)}
          />
        ) : slots.isFetching ? (
          <SkeletonText />
        ) : (
          <Select
            id="move-slot"
            labelText={t('appt.time')}
            value={slot}
            helperText={slots.data && slots.data.length === 0 ? t('appt.noSlots') : undefined}
            onChange={(e) => setSlot(e.target.value)}
          >
            <SelectItem value="" text={t('appt.chooseTime')} />
            {(slots.data ?? []).map((s) => (
              <SelectItem key={s} value={s} text={formatTime(s, i18n.language)} />
            ))}
          </Select>
        )}
        {isManager(me) && (
          <Checkbox
            id="move-override"
            labelText={t('appt.overrideHours')}
            checked={override}
            onChange={(_, { checked }) => setOverride(checked)}
          />
        )}
        <div className="button-row">
          <Button kind="ghost" size="md" onClick={onCancel}>
            {t('appt.back')}
          </Button>
          <Button
            size="md"
            disabled={!startsAt || busy}
            onClick={() =>
              onSubmit({
                starts_at: startsAt,
                practitioner: Number(practitioner),
                allow_outside_hours: override,
              })
            }
          >
            {t('appt.saveNewTime')}
          </Button>
        </div>
      </Stack>
    </div>
  )
}

function CancelForm({
  busy,
  onSubmit,
  onCancel,
}: {
  busy: boolean
  onSubmit: (reason: string) => void
  onCancel: () => void
}) {
  const { t } = useTranslation()
  const [reason, setReason] = useState('')
  return (
    <div className="inline-form">
      <Stack gap={5}>
        <TextInput
          id="cancel-reason"
          labelText={t('appt.cancelReasonOptional')}
          value={reason}
          maxLength={200}
          onChange={(e) => setReason(e.target.value)}
        />
        <div className="button-row">
          <Button kind="ghost" size="md" onClick={onCancel}>
            {t('appt.back')}
          </Button>
          <Button kind="danger" size="md" disabled={busy} onClick={() => onSubmit(reason)}>
            {t('appt.confirmCancel')}
          </Button>
        </div>
      </Stack>
    </div>
  )
}
