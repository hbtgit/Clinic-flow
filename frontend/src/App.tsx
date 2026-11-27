import {
  Content,
  Header,
  HeaderGlobalAction,
  HeaderGlobalBar,
  HeaderMenuItem,
  HeaderName,
  HeaderNavigation,
  Loading,
  SkipToContent,
  Theme,
} from '@carbon/react'
import { Language, Logout } from '@carbon/icons-react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { setLanguage } from './i18n'
import { api, ApiError, type Me } from './lib/api'
import { Appointments } from './pages/Appointments'
import { Home } from './pages/Home'
import { Login } from './pages/Login'
import { Schedules } from './pages/Schedules'

const PAGES = ['appointments', 'schedules', 'practitioners'] as const
type PageName = (typeof PAGES)[number]

function pageFromHash(): PageName {
  const name = window.location.hash.replace(/^#\/?/, '')
  return (PAGES as readonly string[]).includes(name) ? (name as PageName) : 'appointments'
}

export default function App() {
  const { t, i18n } = useTranslation()
  const queryClient = useQueryClient()
  const [page, setPage] = useState<PageName>(pageFromHash)
  const me = useQuery({
    queryKey: ['me'],
    queryFn: () => api<Me>('/auth/me/'),
    retry: (count, err) => !(err instanceof ApiError && err.status === 403) && count < 2,
  })

  useEffect(() => {
    const onHash = () => setPage(pageFromHash())
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  async function signOut() {
    await api('/auth/logout/', { method: 'POST' })
    queryClient.setQueryData(['me'], null)
  }

  const otherLang = i18n.language === 'am' ? 'en' : 'am'

  return (
    <>
      <Theme theme="g100">
        <Header aria-label={t('appName')}>
          <SkipToContent>{t('skipToContent')}</SkipToContent>
          <HeaderName href="#/appointments" prefix="">
            {t('appName')}
          </HeaderName>
          {me.data && (
            <HeaderNavigation aria-label={t('appName')}>
              {PAGES.map((name) => (
                <HeaderMenuItem key={name} href={`#/${name}`} isActive={page === name}>
                  {t(`nav.${name}`)}
                </HeaderMenuItem>
              ))}
            </HeaderNavigation>
          )}
          <HeaderGlobalBar>
            {me.data?.clinic_name && <span className="clinic-name">{me.data.clinic_name}</span>}
            <HeaderGlobalAction
              aria-label={otherLang === 'am' ? 'አማርኛ' : 'English'}
              tooltipAlignment="end"
              onClick={() => setLanguage(otherLang)}
            >
              <Language size={20} />
            </HeaderGlobalAction>
            {me.data && (
              <HeaderGlobalAction aria-label={t('signOut')} tooltipAlignment="end" onClick={signOut}>
                <Logout size={20} />
              </HeaderGlobalAction>
            )}
          </HeaderGlobalBar>
        </Header>
      </Theme>
      <Content id="main-content">
        {me.isLoading ? (
          <div className="centered">
            <Loading withOverlay={false} description={t('loading')} />
          </div>
        ) : me.data ? (
          <>
            {/* HeaderNavigation hides on small screens, so phones get these tabs instead. */}
            <nav className="mobile-nav" aria-label={t('appName')}>
              {PAGES.map((name) => (
                <a key={name} href={`#/${name}`} aria-current={page === name ? 'page' : undefined}>
                  {t(`nav.${name}`)}
                </a>
              ))}
            </nav>
            {page === 'appointments' && <Appointments me={me.data} />}
            {page === 'schedules' && <Schedules me={me.data} />}
            {page === 'practitioners' && <Home me={me.data} />}
          </>
        ) : (
          <Login onSignedIn={(user) => queryClient.setQueryData(['me'], user)} />
        )}
      </Content>
    </>
  )
}
