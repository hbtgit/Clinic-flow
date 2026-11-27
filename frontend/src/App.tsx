import {
  Content,
  Header,
  HeaderGlobalAction,
  HeaderGlobalBar,
  HeaderName,
  Loading,
  SkipToContent,
  Theme,
} from '@carbon/react'
import { Language, Logout } from '@carbon/icons-react'
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

  const otherLang = i18n.language === 'am' ? 'en' : 'am'

  return (
    <>
      <Theme theme="g100">
        <Header aria-label={t('appName')}>
          <SkipToContent>{t('skipToContent')}</SkipToContent>
          <HeaderName href="#" prefix="">
            {t('appName')}
          </HeaderName>
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
          <Home me={me.data} />
        ) : (
          <Login onSignedIn={(user) => queryClient.setQueryData(['me'], user)} />
        )}
      </Content>
    </>
  )
}
