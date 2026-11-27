function getCookie(name: string): string | undefined {
  return document.cookie
    .split('; ')
    .find((row) => row.startsWith(`${name}=`))
    ?.split('=')[1]
}

export class ApiError extends Error {
  status: number
  /** Stable reason from the API, such as "conflict" or "outside_hours", when it sends one. */
  code?: string
  constructor(status: number, message: string, code?: string) {
    super(message)
    this.status = status
    this.code = code
  }
}

/** DRF sends {detail} for most errors and {field: [messages]} for validation errors. */
function errorMessage(data: unknown, fallback: string): string {
  if (data && typeof data === 'object') {
    const d = data as Record<string, unknown>
    if (typeof d.detail === 'string') return d.detail
    for (const value of Object.values(d)) {
      if (Array.isArray(value) && typeof value[0] === 'string') return value[0]
      if (typeof value === 'string') return value
    }
  }
  return fallback
}

/** Calls the Django API with the session cookie and CSRF token. */
export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method ?? 'GET').toUpperCase()
  if (method !== 'GET' && !getCookie('csrftoken')) {
    await fetch('/api/auth/csrf/', { credentials: 'same-origin' })
  }
  const headers = new Headers(init.headers)
  headers.set('Accept', 'application/json')
  if (init.body) headers.set('Content-Type', 'application/json')
  if (method !== 'GET') headers.set('X-CSRFToken', getCookie('csrftoken') ?? '')

  const res = await fetch(`/api${path}`, { ...init, headers, credentials: 'same-origin' })
  if (res.status === 204) return undefined as T
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new ApiError(res.status, errorMessage(data, res.statusText), data.code)
  return data as T
}

export type Me = {
  id: number
  username: string
  first_name: string
  role: string
  clinic: number | null
  clinic_name: string | null
  preferred_language: 'en' | 'am'
  practitioner: number | null
}

export type Practitioner = { id: number; display_name: string; title: string; is_active: boolean }
export type Page<T> = { count: number; results: T[] }
export type Service = { id: number; name: string; duration_minutes: number; is_active: boolean }

export type AppointmentStatus = 'booked' | 'confirmed' | 'cancelled' | 'no_show'
export type Appointment = {
  id: number
  reference: string
  practitioner: number
  practitioner_name: string
  service: number
  service_name: string
  starts_at: string
  ends_at: string
  status: AppointmentStatus
  patient_name: string
  patient_phone: string
  outside_hours: boolean
  cancel_reason: string
  created_at: string
}
export type Summary = Record<AppointmentStatus, number> & { total: number }
export type HistoryEntry = {
  action: string
  actor: string | null
  at: string
  detail: Record<string, unknown>
}

export type WorkingHours = {
  id: number
  practitioner: number
  weekday: number
  start_time: string
  end_time: string
}
export type TimeOff = {
  id: number
  practitioner: number
  starts_at: string
  ends_at: string
  reason: string
  clashing_appointments: string[]
}

export const MANAGER_ROLES = ['clinic_manager', 'tenant_admin']
export const FRONT_DESK_ROLES = ['receptionist', ...MANAGER_ROLES]
export const isManager = (me: Me) => MANAGER_ROLES.includes(me.role)
export const isFrontDesk = (me: Me) => FRONT_DESK_ROLES.includes(me.role)

/** Reads a list endpoint whether or not it is paginated. A clinic's lists fit on one page. */
export async function listAll<T>(path: string): Promise<T[]> {
  const data = await api<Page<T> | T[]>(path)
  return Array.isArray(data) ? data : data.results
}
