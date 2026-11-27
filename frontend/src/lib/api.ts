function getCookie(name: string): string | undefined {
  return document.cookie
    .split('; ')
    .find((row) => row.startsWith(`${name}=`))
    ?.split('=')[1]
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
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
  if (!res.ok) throw new ApiError(res.status, data.detail ?? res.statusText)
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
}

export type Practitioner = { id: number; display_name: string; title: string; is_active: boolean }
export type Page<T> = { count: number; results: T[] }
