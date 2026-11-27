import { Button, Form, InlineNotification, PasswordInput, Stack, TextInput, Tile } from '@carbon/react'
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
    <div className="login-wrap">
      <Tile className="login-tile">
        <Form onSubmit={submit}>
          <Stack gap={6}>
            <h1 className="cds--type-heading-04">{t('signIn')}</h1>
            <TextInput
              id="username"
              labelText={t('username')}
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
            <PasswordInput
              id="password"
              labelText={t('password')}
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              showPasswordLabel={t('showPassword')}
              hidePasswordLabel={t('hidePassword')}
              required
            />
            {error && (
              <InlineNotification
                kind="error"
                role="alert"
                title={error}
                hideCloseButton
                lowContrast
              />
            )}
            <Button type="submit" disabled={busy}>
              {busy ? t('signingIn') : t('signIn')}
            </Button>
          </Stack>
        </Form>
      </Tile>
    </div>
  )
}
