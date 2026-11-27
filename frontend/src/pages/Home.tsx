import {
  DataTable,
  DataTableSkeleton,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableHeader,
  TableRow,
  Tag,
} from '@carbon/react'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { api, type Me, type Page, type Practitioner } from '../lib/api'

export function Home({ me }: { me: Me }) {
  const { t } = useTranslation()
  const practitioners = useQuery({
    queryKey: ['practitioners'],
    queryFn: () => api<Page<Practitioner>>('/practitioners/'),
  })

  const headers = [
    { key: 'name', header: t('name') },
    { key: 'title', header: t('title') },
    { key: 'status', header: t('status') },
  ]
  const rows = (practitioners.data?.results ?? []).map((p) => ({
    id: String(p.id),
    name: p.display_name,
    title: p.title,
    status: p.is_active,
  }))

  return (
    <div className="page">
      <h1 className="cds--type-heading-05">{t('practitioners')}</h1>
      <p className="subtitle">{me.clinic_name}</p>
      {practitioners.isLoading ? (
        <DataTableSkeleton headers={headers} columnCount={3} rowCount={4} showToolbar={false} />
      ) : (
        <DataTable rows={rows} headers={headers}>
          {({ rows, headers, getTableProps, getHeaderProps, getRowProps }) => (
            <TableContainer>
              <Table {...getTableProps()} aria-label={t('practitioners')}>
                <TableHead>
                  <TableRow>
                    {headers.map((h) => {
                      const { key, ...props } = getHeaderProps({ header: h })
                      return (
                        <TableHeader key={key} {...props}>
                          {h.header}
                        </TableHeader>
                      )
                    })}
                  </TableRow>
                </TableHead>
                <TableBody>
                  {rows.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={3}>{t('noPractitioners')}</TableCell>
                    </TableRow>
                  )}
                  {rows.map((row) => {
                    const { key, ...props } = getRowProps({ row })
                    return (
                      <TableRow key={key} {...props}>
                        {row.cells.map((cell) => (
                          <TableCell key={cell.id}>
                            {cell.info.header === 'status' ? (
                              <Tag type={cell.value ? 'green' : 'gray'} size="sm">
                                {cell.value ? t('active') : t('inactive')}
                              </Tag>
                            ) : (
                              cell.value
                            )}
                          </TableCell>
                        ))}
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </DataTable>
      )}
    </div>
  )
}
