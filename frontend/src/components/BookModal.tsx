import {
  Checkbox,
  InlineNotification,
  Modal,
  Select,
  SelectItem,
  SkeletonText,
  Stack,
  TextInput,
} from '@carbon/react'
import { useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api, isManager, type Appointment, type Me, type Practitioner, type Service } from '../lib/api'
import { clinicIso, formatTime } from '../lib/time'
import { useErrorText, useSlots } from './slots'

/** Receptionist books a patient with a practitioner, service and free time (FR-011). */
export function BookModal({
  me,
  practitioners,
  services,
  defaultDate,
  defaultPractitioner,
  onClose,
  onBooked,
}: {
  me: Me
  practitioners: Practitioner[]
  services: Service[]
  defaultDate: string
  defaultPractitioner: string
  onClose: () => void
  onBooked: (a: Appointment) => void
}) {
  const { t, i18n } = useTranslation()
  const queryClient = useQueryClient()
  const errorText = useErrorText()
  const [practitioner, setPractitioner] = useState(defaultPractitioner)
  const [service, setService] = useState(services.length === 1 ? String(services[0].id) : '')
  const [date, setDate] = useState(defaultDate)
  const [slot, setSlot] = useState('')
  const [override, setOverride] = useState(false)
  const [overrideTime, setOverrideTime] = useState('')
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const slots = useSlots(practitioner, service, date)

  const startsAt = override ? (overrideTime ? clinicIso(date, overrideTime) : '') : slot
  const ready = Boolean(practitioner && service && startsAt && name.trim())

  async function submit() {
    if (!ready || busy) return
    setBusy(true)
    setError(null)
    try {
      const appt = await api<Appointment>('/appointments/', {
        method: 'POST',
        body: JSON.stringify({
          practitioner: Number(practitioner),
          service: Number(service),
          starts_at: startsAt,
          patient_name: name.trim(),
          patient_phone: phone.trim(),
          allow_outside_hours: override,
        }),
      })
      await queryClient.invalidateQueries({ queryKey: ['appointments'] })
      await queryClient.invalidateQueries({ queryKey: ['slots'] })
      onBooked(appt)
    } catch (err) {
      setError(errorText(err))
      queryClient.invalidateQueries({ queryKey: ['slots'] })
    } finally {
      setBusy(false)
    }
  }

  const resetSlot = () => setSlot('')

  return (
    <Modal
      open
      modalHeading={t('appt.book')}
      primaryButtonText={busy ? t('appt.saving') : t('appt.book')}
      secondaryButtonText={t('appt.close')}
      primaryButtonDisabled={!ready || busy}
      onRequestClose={onClose}
      onRequestSubmit={submit}
      size="sm"
    >
      <Stack gap={5}>
        {error && <InlineNotification kind="error" lowContrast hideCloseButton title={error} />}
        <Select
          id="book-practitioner"
          labelText={t('appt.practitioner')}
          value={practitioner}
          onChange={(e) => {
            setPractitioner(e.target.value)
            resetSlot()
          }}
        >
          <SelectItem value="" text={t('appt.choose')} />
          {practitioners.map((p) => (
            <SelectItem key={p.id} value={String(p.id)} text={p.display_name} />
          ))}
        </Select>
        <Select
          id="book-service"
          labelText={t('appt.service')}
          value={service}
          onChange={(e) => {
            setService(e.target.value)
            resetSlot()
          }}
        >
          <SelectItem value="" text={t('appt.choose')} />
          {services.map((s) => (
            <SelectItem
              key={s.id}
              value={String(s.id)}
              text={t('appt.serviceWithLength', { name: s.name, minutes: s.duration_minutes })}
            />
          ))}
        </Select>
        <TextInput
          id="book-date"
          type="date"
          labelText={t('appt.date')}
          value={date}
          onChange={(e) => {
            setDate(e.target.value)
            resetSlot()
          }}
        />
        {!override &&
          (slots.isFetching ? (
            <SkeletonText />
          ) : (
            <Select
              id="book-slot"
              labelText={t('appt.time')}
              value={slot}
              disabled={!slots.data}
              helperText={
                slots.data && slots.data.length === 0 ? t('appt.noSlots') : undefined
              }
              onChange={(e) => setSlot(e.target.value)}
            >
              <SelectItem
                value=""
                text={practitioner && service ? t('appt.chooseTime') : t('appt.chooseFirst')}
              />
              {(slots.data ?? []).map((s) => (
                <SelectItem key={s} value={s} text={formatTime(s, i18n.language)} />
              ))}
            </Select>
          ))}
        {isManager(me) && (
          <Checkbox
            id="book-override"
            labelText={t('appt.overrideHours')}
            helperText={t('appt.overrideHelp')}
            checked={override}
            onChange={(_, { checked }) => setOverride(checked)}
          />
        )}
        {override && (
          <TextInput
            id="book-override-time"
            type="time"
            labelText={t('appt.time')}
            value={overrideTime}
            onChange={(e) => setOverrideTime(e.target.value)}
          />
        )}
        <TextInput
          id="book-name"
          labelText={t('appt.patientName')}
          helperText={t('appt.patientNameHelp')}
          value={name}
          maxLength={120}
          onChange={(e) => setName(e.target.value)}
        />
        <TextInput
          id="book-phone"
          type="tel"
          labelText={t('appt.phoneOptional')}
          placeholder="0911 234 567"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
        />
      </Stack>
    </Modal>
  )
}
