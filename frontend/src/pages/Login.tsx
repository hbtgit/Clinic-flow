import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { api, type Me } from '../lib/api'

export function Login({ onSignedIn }: { onSignedIn: (me: Me) => void }) {
  const { t } = useTranslation()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function submit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const me = await api<Me>('/auth/login/', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      })
      onSignedIn(me)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="card login" onSubmit={submit}>
      <h1>{t('appName')}</h1>
      <label htmlFor="username">{t('username')}</label>
      <input id="username" autoComplete="username" value={username}
        onChange={(e) => setUsername(e.target.value)} required />
      <label htmlFor="password">{t('password')}</label>
      <input id="password" type="password" autoComplete="current-password" value={password}
        onChange={(e) => setPassword(e.target.value)} required />
      {error && <p className="error" role="alert">{error}</p>}
      <button type="submit" disabled={busy}>{busy ? t('signingIn') : t('signIn')}</button>
    </form>
  )
}
