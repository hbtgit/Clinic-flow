import { Tag } from '@carbon/react'
import { useTranslation } from 'react-i18next'
import type { AppointmentStatus } from '../lib/api'

const STATUS_TAG: Record<AppointmentStatus, 'blue' | 'green' | 'gray' | 'red'> = {
  booked: 'blue',
  confirmed: 'green',
  cancelled: 'gray',
  no_show: 'red',
}

export function StatusTag({ status }: { status: AppointmentStatus }) {
  const { t } = useTranslation()
  return (
    <Tag type={STATUS_TAG[status]} size="sm">
      {t(`statuses.${status}`)}
    </Tag>
  )
}
