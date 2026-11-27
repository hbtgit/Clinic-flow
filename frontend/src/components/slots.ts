import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { api, ApiError } from '../lib/api'

/** Free start times for a practitioner and service on one day (FR-010). */
export function useSlots(practitioner: string | number, service: string | number, date: string) {
  return useQuery({
    queryKey: ['slots', String(practitioner), String(service), date],
    queryFn: () =>
      api<{ slots: string[] }>(
        `/practitioners/${practitioner}/slots/?date=${date}&service=${service}`,
      ).then((r) => r.slots),
    enabled: Boolean(practitioner && service && date),
  })
}

/** Turns an API error into a sentence in the user's language. */
export function useErrorText() {
  const { t } = useTranslation()
  return (err: unknown) => {
    if (err instanceof ApiError && err.code) {
      return t(`errors.${err.code}`, { defaultValue: err.message })
    }
    return err instanceof Error ? err.message : String(err)
  }
}
