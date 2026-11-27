import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { setLanguage } from './i18n'
import { api, ApiError, type Me } from './lib/api'
import { Home } from './pages/Home'
import { Login } from './pages/Login'

export default function App() {
  const { t, i18n } = useTranslation()
  const queryClient = useQueryClient()
  const me = useQuery({
    queryKey: ['me'],
    queryFn: () => api<Me>('/auth/me/'),
    retry: (count, err) => !(err instanceof ApiError && err.status === 403) && count < 2,
  })

  async function signOut() {
    await api('/auth/logout/', { method: 'POST' })
    queryClient.setQueryData(['me'], null)
  }

  return (
    <div className="shell">
      <header className="topbar">
        <strong>{t('appName')}</strong>
        <div className="actions">
          <label htmlFor="lang" className="visually-hidden">{t('language')}</label>
          <select id="lang" value={i18n.language}
            onChange={(e) => setLanguage(e.target.value as 'en' | 'am')}>
            <option value="en">English</option>
            <option value="am">አማርኛ</option>
          </select>
          {me.data && <button onClick={signOut}>{t('signOut')}</button>}
        </div>
      </header>
      <main>
        {me.isLoading ? (
          <p>{t('loading')}</p>
        ) : me.data ? (
          <Home me={me.data} />
        ) : (
          <Login onSignedIn={(user) => queryClient.setQueryData(['me'], user)} />
        )}
      </main>
    </div>
  )
}
