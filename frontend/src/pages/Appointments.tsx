import {
  Button,
  ContentSwitcher,
  DataTableSkeleton,
  IconButton,
  InlineNotification,
  Search,
  Select,
  SelectItem,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableHeader,
  TableRow,
  Tag,
} from '@carbon/react'
import { Add, ChevronLeft, ChevronRight } from '@carbon/icons-react'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { AppointmentModal } from '../components/AppointmentModal'
import { BookModal } from '../components/BookModal'
import { StatusTag } from '../components/StatusTag'
import {
  api,
  isFrontDesk,
  listAll,
  type Appointment,
  type Me,
  type Practitioner,
  type Service,
  type Summary,
} from '../lib/api'
import { addDays, clinicDate, formatDay, formatTime, weekStart } from '../lib/time'

export function Appointments({ me }: { me: Me }) {
  const { t, i18n } = useTranslation()
  const lang = i18n.language
  const [view, setView] = useState<'day' | 'week'>('day')
  const [date, setDate] = useState(clinicDate)
  const [practitioner, setPractitioner] = useState('')
  const [booking, setBooking] = useState(false)
  const [selected, setSelected] = useState<Appointment | null>(null)
  const [notFound, setNotFound] = useState<string | null>(null)

  const from = view === 'day' ? date : weekStart(date)
  const to = view === 'day' ? date : addDays(from, 6)
  const filter = `date_from=${from}&date_to=${to}${practitioner ? `&practitioner=${practitioner}` : ''}`

  const practitioners = useQuery({
    queryKey: ['practitioners'],
    queryFn: () => listAll<Practitioner>('/practitioners/'),
  })
  const services = useQuery({
    queryKey: ['services'],
    queryFn: () => listAll<Service>('/services/'),
  })
  const appointments = useQuery({
    queryKey: ['appointments', filter],
    queryFn: () => api<Appointment[]>(`/appointments/?${filter}`),
  })
  const summary = useQuery({
    queryKey: ['appointments', 'summary', filter],
    queryFn: () => api<Summary>(`/appointments/summary/?${filter}`),
  })

  async function findReference(value: string) {
    const ref = value.trim()
    setNotFound(null)
    if (!ref) return
    const found = await api<Appointment[]>(`/appointments/?reference=${encodeURIComponent(ref)}`)
    if (found.length) setSelected(found[0])
    else setNotFound(ref)
  }

  const step = view === 'day' ? 1 : 7
  const rangeLabel =
    view === 'day'
      ? formatDay(date, lang)
      : `${formatDay(from, lang, { short: true })} – ${formatDay(to, lang, { short: true })}`
  const list = appointments.data ?? []
  const canBook = isFrontDesk(me)

  return (
    <div className="page page--wide">
      <div className="page-head">
        <div>
          <h1 className="cds--type-heading-05">{t('nav.appointments')}</h1>
          <p className="subtitle">{rangeLabel}</p>
        </div>
        {canBook && (
          <Button renderIcon={Add} onClick={() => setBooking(true)}>
            {t('appt.book')}
          </Button>
        )}
      </div>

      <div className="toolbar">
        <ContentSwitcher
          size="md"
          selectedIndex={view === 'day' ? 0 : 1}
          onChange={({ name }) => setView(name === 'week' ? 'week' : 'day')}
          className="toolbar__switch"
        >
          <Switch name="day" text={t('appt.day')} />
          <Switch name="week" text={t('appt.week')} />
        </ContentSwitcher>
        <div className="toolbar__dates">
          <IconButton
            kind="ghost"
            label={t('appt.previous')}
            onClick={() => setDate(addDays(date, -step))}
          >
            <ChevronLeft />
          </IconButton>
          <Button kind="tertiary" size="md" onClick={() => setDate(clinicDate())}>
            {t('appt.today')}
          </Button>
          <IconButton kind="ghost" label={t('appt.next')} onClick={() => setDate(addDays(date, step))}>
            <ChevronRight />
          </IconButton>
          <input
            className="cds--text-input date-jump"
            type="date"
            aria-label={t('appt.date')}
            value={date}
            onChange={(e) => e.target.value && setDate(e.target.value)}
          />
        </div>
        <Select
          id="filter-practitioner"
          labelText={t('appt.practitioner')}
          hideLabel
          inline={false}
          value={practitioner}
          onChange={(e) => setPractitioner(e.target.value)}
          className="toolbar__select"
        >
          <SelectItem value="" text={t('appt.allPractitioners')} />
          {(practitioners.data ?? []).map((p) => (
            <SelectItem key={p.id} value={String(p.id)} text={p.display_name} />
          ))}
        </Select>
        <Search
          size="md"
          labelText={t('appt.findReference')}
          placeholder={t('appt.findReference')}
          closeButtonLabelText={t('appt.clear')}
          className="toolbar__search"
          onKeyDown={(e) => {
            if (e.key === 'Enter') findReference((e.target as HTMLInputElement).value)
          }}
        />
      </div>

      {notFound && (
        <InlineNotification
          kind="warning"
          lowContrast
          title={t('appt.notFound', { ref: notFound })}
          onClose={() => setNotFound(null)}
        />
      )}

      {summary.data && (
        <div className="summary" aria-label={t('appt.summary')}>
          {(['booked', 'confirmed', 'cancelled', 'no_show'] as const).map((s) => (
            <div key={s} className="summary__item">
              <span className="summary__count">{summary.data[s]}</span>
              <StatusTag status={s} />
            </div>
          ))}
          <div className="summary__item">
            <span className="summary__count">{summary.data.total}</span>
            <span className="summary__label">{t('appt.total')}</span>
          </div>
        </div>
      )}

      {appointments.isLoading ? (
        <DataTableSkeleton columnCount={6} rowCount={5} showToolbar={false} showHeader={false} />
      ) : view === 'day' ? (
        <DayTable appointments={list} onOpen={setSelected} />
      ) : (
        <WeekGrid from={from} appointments={list} onOpen={setSelected} />
      )}

      {booking && (
        <BookModal
          me={me}
          practitioners={(practitioners.data ?? []).filter((p) => p.is_active)}
          services={(services.data ?? []).filter((s) => s.is_active)}
          defaultDate={date < clinicDate() ? clinicDate() : date}
          defaultPractitioner={practitioner}
          onClose={() => setBooking(false)}
          onBooked={(appt) => {
            setBooking(false)
            setSelected(appt)
          }}
        />
      )}
      {selected && (
        <AppointmentModal
          me={me}
          appointment={selected}
          practitioners={(practitioners.data ?? []).filter((p) => p.is_active)}
          onChange={setSelected}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  )
}

function DayTable({
  appointments,
  onOpen,
}: {
  appointments: Appointment[]
  onOpen: (a: Appointment) => void
}) {
  const { t, i18n } = useTranslation()
  return (
    <TableContainer>
      <Table aria-label={t('nav.appointments')} size="md">
        <TableHead>
          <TableRow>
            <TableHeader>{t('appt.time')}</TableHeader>
            <TableHeader>{t('appt.patient')}</TableHeader>
            <TableHeader>{t('appt.practitioner')}</TableHeader>
            <TableHeader>{t('appt.service')}</TableHeader>
            <TableHeader>{t('appt.reference')}</TableHeader>
            <TableHeader>{t('status')}</TableHeader>
          </TableRow>
        </TableHead>
        <TableBody>
          {appointments.length === 0 && (
            <TableRow>
              <TableCell colSpan={6}>{t('appt.none')}</TableCell>
            </TableRow>
          )}
          {appointments.map((a) => (
            <TableRow key={a.id} className={a.status === 'cancelled' ? 'row--muted' : undefined}>
              <TableCell>
                {formatTime(a.starts_at, i18n.language)}–{formatTime(a.ends_at, i18n.language)}
              </TableCell>
              <TableCell>
                <button type="button" className="link-button" onClick={() => onOpen(a)}>
                  {a.patient_name}
                </button>
              </TableCell>
              <TableCell>{a.practitioner_name}</TableCell>
              <TableCell>{a.service_name}</TableCell>
              <TableCell className="mono">{a.reference}</TableCell>
              <TableCell>
                <StatusTag status={a.status} />
                {a.outside_hours && (
                  <Tag type="purple" size="sm">
                    {t('appt.outsideHours')}
                  </Tag>
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  )
}

function WeekGrid({
  from,
  appointments,
  onOpen,
}: {
  from: string
  appointments: Appointment[]
  onOpen: (a: Appointment) => void
}) {
  const { t, i18n } = useTranslation()
  const days = Array.from({ length: 7 }, (_, i) => addDays(from, i))
  const today = clinicDate()
  return (
    <div className="week">
      {days.map((day) => {
        const items = appointments.filter((a) => clinicDate(a.starts_at) === day)
        return (
          <section key={day} className={`week__day${day === today ? ' week__day--today' : ''}`}>
            <h2 className="week__head">{formatDay(day, i18n.language, { short: true })}</h2>
            {items.length === 0 && <p className="week__empty">{t('appt.noneShort')}</p>}
            {items.map((a) => (
              <button
                key={a.id}
                type="button"
                className={`week__item week__item--${a.status}`}
                onClick={() => onOpen(a)}
              >
                <span className="week__time">{formatTime(a.starts_at, i18n.language)}</span>
                <span className="week__patient">{a.patient_name}</span>
                <span className="week__meta">
                  {a.practitioner_name} · {a.service_name}
                </span>
              </button>
            ))}
          </section>
        )
      })}
    </div>
  )
}
