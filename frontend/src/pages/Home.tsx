import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { api, type Me, type Page, type Practitioner } from '../lib/api'

export function Home({ me }: { me: Me }) {
  const { t } = useTranslation()
  const practitioners = useQuery({
    queryKey: ['practitioners'],
    queryFn: () => api<Page<Practitioner>>('/practitioners/'),
  })

  return (
    <section className="card">
      <h2>{t('practitioners')}</h2>
      <p className="muted">{me.clinic_name}</p>
      {practitioners.isLoading && <p>{t('loading')}</p>}
      {practitioners.data?.results.length === 0 && <p>{t('noPractitioners')}</p>}
      <ul>
        {practitioners.data?.results.map((p) => (
          <li key={p.id}>
            {p.display_name} {p.title && <span className="muted">· {p.title}</span>}
          </li>
        ))}
      </ul>
    </section>
  )
}
