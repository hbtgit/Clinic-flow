/**
 * Dates and times are always shown in clinic time (Addis Ababa, UTC+3 all year, no daylight
 * saving), whatever the computer's own clock is set to. Amharic users see the Ethiopian
 * calendar date alongside the Gregorian one.
 */
export const CLINIC_TZ = 'Africa/Addis_Ababa'
export const CLINIC_OFFSET = '+03:00'

const ymdFormat = new Intl.DateTimeFormat('en-CA', {
  timeZone: CLINIC_TZ,
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
})

/** YYYY-MM-DD in clinic time. */
export function clinicDate(d: Date | string = new Date()): string {
  return ymdFormat.format(typeof d === 'string' ? new Date(d) : d)
}

function utcNoon(ymd: string): Date {
  return new Date(`${ymd}T12:00:00Z`)
}

export function addDays(ymd: string, days: number): string {
  const d = utcNoon(ymd)
  d.setUTCDate(d.getUTCDate() + days)
  return d.toISOString().slice(0, 10)
}

/** Monday of the week containing `ymd`. */
export function weekStart(ymd: string): string {
  const dow = (utcNoon(ymd).getUTCDay() + 6) % 7
  return addDays(ymd, -dow)
}

/** Monday = 0 ... Sunday = 6, matching the API. */
export function weekdayIndex(ymd: string): number {
  return (utcNoon(ymd).getUTCDay() + 6) % 7
}

function locale(lang: string) {
  return lang === 'am' ? 'am-ET' : 'en-GB'
}

export function formatTime(iso: string, lang: string): string {
  return new Intl.DateTimeFormat(locale(lang), {
    timeZone: CLINIC_TZ,
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(iso))
}

/** A day label. In Amharic the Ethiopian calendar date comes first. */
export function formatDay(ymd: string, lang: string, opts: { short?: boolean } = {}): string {
  const d = utcNoon(ymd)
  const base: Intl.DateTimeFormatOptions = opts.short
    ? { timeZone: 'UTC', weekday: 'short', day: 'numeric', month: 'short' }
    : { timeZone: 'UTC', weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }
  const greg = new Intl.DateTimeFormat(locale(lang), base).format(d)
  if (lang !== 'am') return greg
  const eth = new Intl.DateTimeFormat('am-ET-u-ca-ethiopic', {
    ...base,
    weekday: undefined,
  }).format(d)
  return `${eth} (${greg})`
}

export function formatDateTime(iso: string, lang: string): string {
  return `${formatDay(clinicDate(iso), lang, { short: true })} ${formatTime(iso, lang)}`
}

/** "2026-12-07" + "09:30" -> an ISO string in clinic time. */
export function clinicIso(ymd: string, hhmm: string): string {
  return `${ymd}T${hhmm}:00${CLINIC_OFFSET}`
}

/** For <input type="datetime-local">: an API time -> "2026-12-07T09:30" in clinic time. */
export function toLocalInput(iso: string): string {
  const time = new Intl.DateTimeFormat('en-GB', {
    timeZone: CLINIC_TZ,
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  }).format(new Date(iso))
  return `${clinicDate(iso)}T${time}`
}

export function fromLocalInput(value: string): string {
  return `${value}:00${CLINIC_OFFSET}`
}
