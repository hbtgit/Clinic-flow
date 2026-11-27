import {
  Button,
  DismissibleTag,
  InlineNotification,
  Select,
  SelectItem,
  SkeletonText,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableHeader,
  TableRow,
  Tag,
  TextInput,
} from '@carbon/react'
import { Add, TrashCan } from '@carbon/icons-react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { useErrorText } from '../components/slots'
import {
  api,
  isManager,
  listAll,
  type Me,
  type Practitioner,
  type TimeOff,
  type WorkingHours,
} from '../lib/api'
import { formatDateTime, fromLocalInput } from '../lib/time'

const WEEKDAYS = [0, 1, 2, 3, 4, 5, 6]

/** Working hours, breaks and time off per practitioner (FR-010). Managers edit; others read. */
export function Schedules({ me }: { me: Me }) {
  const { t } = useTranslation()
  const practitioners = useQuery({
    queryKey: ['practitioners'],
    queryFn: () => listAll<Practitioner>('/practitioners/'),
  })
  const [chosen, setChosen] = useState('')
  const list = practitioners.data ?? []
  const current = chosen || (me.practitioner ? String(me.practitioner) : String(list[0]?.id ?? ''))
  const canEdit = isManager(me)

  return (
    <div className="page">
      <h1 className="cds--type-heading-05">{t('nav.schedules')}</h1>
      <p className="subtitle">{canEdit ? t('sched.introManager') : t('sched.introReadOnly')}</p>
      {practitioners.isLoading ? (
        <SkeletonText paragraph />
      ) : list.length === 0 ? (
        <p>{t('noPractitioners')}</p>
      ) : (
        <>
          <Select
            id="sched-practitioner"
            labelText={t('appt.practitioner')}
            value={current}
            onChange={(e) => setChosen(e.target.value)}
            className="narrow"
          >
            {list.map((p) => (
              <SelectItem key={p.id} value={String(p.id)} text={p.display_name} />
            ))}
          </Select>
          {current && (
            <>
              <HoursSection practitioner={current} canEdit={canEdit} />
              <TimeOffSection practitioner={current} canEdit={canEdit} />
            </>
          )}
        </>
      )}
    </div>
  )
}

const hhmm = (time: string) => time.slice(0, 5)

function HoursSection({ practitioner, canEdit }: { practitioner: string; canEdit: boolean }) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const errorText = useErrorText()
  const key = ['working-hours', practitioner]
  const hours = useQuery({
    queryKey: key,
    queryFn: () => listAll<WorkingHours>(`/working-hours/?practitioner=${practitioner}`),
  })
  const [weekday, setWeekday] = useState('0')
  const [start, setStart] = useState('08:30')
  const [end, setEnd] = useState('12:30')
  const [error, setError] = useState<string | null>(null)

  async function refresh() {
    await queryClient.invalidateQueries({ queryKey: key })
    await queryClient.invalidateQueries({ queryKey: ['slots'] })
  }

  async function add(e: FormEvent) {
    e.preventDefault()
    setError(null)
    try {
      await api('/working-hours/', {
        method: 'POST',
        body: JSON.stringify({
          practitioner: Number(practitioner),
          weekday: Number(weekday),
          start_time: start,
          end_time: end,
        }),
      })
      await refresh()
    } catch (err) {
      setError(errorText(err))
    }
  }

  async function remove(id: number) {
    setError(null)
    try {
      await api(`/working-hours/${id}/`, { method: 'DELETE' })
      await refresh()
    } catch (err) {
      setError(errorText(err))
    }
  }

  return (
    <section className="section">
      <h2 className="cds--type-heading-03 section-title">{t('sched.hours')}</h2>
      <p className="helper">{t('sched.hoursHelp')}</p>
      {hours.isLoading ? (
        <SkeletonText paragraph />
      ) : (
        <TableContainer>
          <Table size="md" aria-label={t('sched.hours')}>
            <TableHead>
              <TableRow>
                <TableHeader>{t('sched.day')}</TableHeader>
                <TableHeader>{t('sched.hours')}</TableHeader>
              </TableRow>
            </TableHead>
            <TableBody>
              {WEEKDAYS.map((d) => {
                const blocks = (hours.data ?? []).filter((h) => h.weekday === d)
                return (
                  <TableRow key={d}>
                    <TableCell>{t(`weekdays.${d}`)}</TableCell>
                    <TableCell>
                      {blocks.length === 0 && <span className="muted">{t('sched.notWorking')}</span>}
                      {blocks.map((b) => {
                        const label = `${hhmm(b.start_time)}–${hhmm(b.end_time)}`
                        return canEdit ? (
                          <DismissibleTag
                            key={b.id}
                            type="teal"
                            size="md"
                            text={label}
                            dismissTooltipLabel={t('sched.remove')}
                            onClose={() => remove(b.id)}
                          />
                        ) : (
                          <Tag key={b.id} type="teal" size="md">
                            {label}
                          </Tag>
                        )
                      })}
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </TableContainer>
      )}
      {canEdit && (
        <form className="inline-row" onSubmit={add}>
          <Select
            id="hours-day"
            labelText={t('sched.day')}
            value={weekday}
            onChange={(e) => setWeekday(e.target.value)}
          >
            {WEEKDAYS.map((d) => (
              <SelectItem key={d} value={String(d)} text={t(`weekdays.${d}`)} />
            ))}
          </Select>
          <TextInput
            id="hours-start"
            type="time"
            labelText={t('sched.from')}
            value={start}
            onChange={(e) => setStart(e.target.value)}
          />
          <TextInput
            id="hours-end"
            type="time"
            labelText={t('sched.to')}
            value={end}
            onChange={(e) => setEnd(e.target.value)}
          />
          <Button type="submit" kind="tertiary" size="md" renderIcon={Add}>
            {t('sched.addHours')}
          </Button>
        </form>
      )}
      {error && (
        <InlineNotification kind="error" lowContrast title={error} onClose={() => setError(null)} />
      )}
    </section>
  )
}

function TimeOffSection({ practitioner, canEdit }: { practitioner: string; canEdit: boolean }) {
  const { t, i18n } = useTranslation()
  const queryClient = useQueryClient()
  const errorText = useErrorText()
  const key = ['time-off', practitioner]
  const timeOff = useQuery({
    queryKey: key,
    queryFn: () => listAll<TimeOff>(`/time-off/?practitioner=${practitioner}`),
  })
  const [start, setStart] = useState('')
  const [end, setEnd] = useState('')
  const [reason, setReason] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [clashes, setClashes] = useState<string[]>([])

  async function refresh() {
    await queryClient.invalidateQueries({ queryKey: key })
    await queryClient.invalidateQueries({ queryKey: ['slots'] })
  }

  async function add(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setClashes([])
    try {
      const created = await api<TimeOff>('/time-off/', {
        method: 'POST',
        body: JSON.stringify({
          practitioner: Number(practitioner),
          starts_at: fromLocalInput(start),
          ends_at: fromLocalInput(end),
          reason,
        }),
      })
      setClashes(created.clashing_appointments)
      setStart('')
      setEnd('')
      setReason('')
      await refresh()
    } catch (err) {
      setError(errorText(err))
    }
  }

  async function remove(id: number) {
    setError(null)
    try {
      await api(`/time-off/${id}/`, { method: 'DELETE' })
      await refresh()
    } catch (err) {
      setError(errorText(err))
    }
  }

  const rows = timeOff.data ?? []
  const lang = i18n.language

  return (
    <section className="section">
      <h2 className="cds--type-heading-03 section-title">{t('sched.timeOff')}</h2>
      <p className="helper">{t('sched.timeOffHelp')}</p>
      {timeOff.isLoading ? (
        <SkeletonText paragraph />
      ) : (
        <TableContainer>
          <Table size="md" aria-label={t('sched.timeOff')}>
            <TableHead>
              <TableRow>
                <TableHeader>{t('sched.from')}</TableHeader>
                <TableHeader>{t('sched.to')}</TableHeader>
                <TableHeader>{t('sched.reason')}</TableHeader>
                <TableHeader>{t('sched.toMove')}</TableHeader>
                {canEdit && <TableHeader aria-label={t('sched.remove')} />}
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.length === 0 && (
                <TableRow>
                  <TableCell colSpan={canEdit ? 5 : 4}>{t('sched.noTimeOff')}</TableCell>
                </TableRow>
              )}
              {rows.map((r) => (
                <TableRow key={r.id}>
                  <TableCell>{formatDateTime(r.starts_at, lang)}</TableCell>
                  <TableCell>{formatDateTime(r.ends_at, lang)}</TableCell>
                  <TableCell>{r.reason}</TableCell>
                  <TableCell className="mono">
                    {r.clashing_appointments.length ? r.clashing_appointments.join(', ') : '–'}
                  </TableCell>
                  {canEdit && (
                    <TableCell>
                      <Button
                        kind="ghost"
                        size="sm"
                        hasIconOnly
                        renderIcon={TrashCan}
                        iconDescription={t('sched.remove')}
                        onClick={() => remove(r.id)}
                      />
                    </TableCell>
                  )}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
      {clashes.length > 0 && (
        <InlineNotification
          kind="warning"
          lowContrast
          title={t('sched.clashTitle')}
          subtitle={t('sched.clashBody', { refs: clashes.join(', ') })}
          onClose={() => setClashes([])}
        />
      )}
      {canEdit && (
        <form className="inline-row" onSubmit={add}>
          <TextInput
            id="off-start"
            type="datetime-local"
            labelText={t('sched.from')}
            value={start}
            onChange={(e) => setStart(e.target.value)}
          />
          <TextInput
            id="off-end"
            type="datetime-local"
            labelText={t('sched.to')}
            value={end}
            onChange={(e) => setEnd(e.target.value)}
          />
          <TextInput
            id="off-reason"
            labelText={t('sched.reasonOptional')}
            value={reason}
            maxLength={200}
            onChange={(e) => setReason(e.target.value)}
          />
          <Button
            type="submit"
            kind="tertiary"
            size="md"
            renderIcon={Add}
            disabled={!start || !end}
          >
            {t('sched.addTimeOff')}
          </Button>
        </form>
      )}
      {error && (
        <InlineNotification kind="error" lowContrast title={error} onClose={() => setError(null)} />
      )}
    </section>
  )
}
