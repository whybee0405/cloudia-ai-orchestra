import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
  PieChart, Pie, Cell,
} from 'recharts'
import { FileText, ShieldCheck, AlertCircle } from 'lucide-react'
import { getDirectorClientByBrandDna } from '@/api/campaigns'
import { getAssetReport } from '@/api/reports'
import { Card, CardBody, CardHeader } from '@/shared/components/Card'
import { PageLoader } from '@/shared/components/LoadingSpinner'
import { DateRangePicker } from './components/DateRangePicker'

const STATUS_COLORS: Record<string, string> = {
  approved:  '#9333ea',
  published: '#059669',
  draft:     '#94a3b8',
  rejected:  '#ef4444',
  unknown:   '#cbd5e1',
}

const TYPE_COLORS = ['#9333ea', '#c084fc', '#e879f9', '#f0abfc', '#fae8ff']

function defaultFrom() {
  const d = new Date()
  d.setDate(d.getDate() - 30)
  return d.toISOString().slice(0, 10)
}

function defaultTo() {
  return new Date().toISOString().slice(0, 10)
}

export function CampaignOutputLog() {
  const { clientId } = useParams<{ clientId: string }>()
  const [dateFrom, setDateFrom] = useState(defaultFrom)
  const [dateTo,   setDateTo]   = useState(defaultTo)

  const { data: directorClient, isLoading: clientLoading, error: clientError } = useQuery({
    queryKey: ['director-client', clientId],
    queryFn: () => getDirectorClientByBrandDna(clientId!),
    retry: false,
    enabled: !!clientId,
  })

  const { data: report, isLoading: reportLoading } = useQuery({
    queryKey: ['reports-output', directorClient?.id, dateFrom, dateTo],
    queryFn: () => getAssetReport(directorClient!.id, { date_from: dateFrom, date_to: dateTo }),
    enabled: !!directorClient?.id,
  })

  if (clientLoading) return <PageLoader />

  const is404 = clientError instanceof Error && clientError.message.startsWith('404')
  if (is404 || !directorClient) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <FileText className="w-8 h-8 text-slate-300 mb-3" />
        <p className="text-sm text-slate-500">No Campaign Director account linked to this client.</p>
      </div>
    )
  }

  const statusData = Object.entries(report?.by_status ?? {}).map(([name, value]) => ({ name, value }))
  const typeData   = Object.entries(report?.by_type ?? {}).map(([name, value]) => ({ name, value }))

  return (
    <div className="space-y-5">
      {/* Controls */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 className="text-sm font-medium text-slate-700">Campaign Asset Production</h3>
        <DateRangePicker
          dateFrom={dateFrom} dateTo={dateTo}
          onFromChange={setDateFrom} onToChange={setDateTo}
        />
      </div>

      {reportLoading ? (
        <PageLoader />
      ) : (
        <>
          {/* Stat cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="rounded-xl border border-slate-200 bg-white px-4 py-3">
              <p className="text-xs text-slate-500 mb-1">Total Assets</p>
              <p className="text-2xl font-bold text-slate-900">{report?.total_assets ?? 0}</p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white px-4 py-3">
              <p className="text-xs text-slate-500 mb-1">Total Tokens</p>
              <p className="text-2xl font-bold text-slate-900">
                {((report?.tokens_total ?? 0) / 1000).toFixed(1)}k
              </p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white px-4 py-3">
              <p className="text-xs text-slate-500 mb-1">Total Cost</p>
              <p className="text-2xl font-bold text-purple-700">
                ${(report?.cost_usd_total ?? 0).toFixed(2)}
              </p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white px-4 py-3">
              {report?.brand_check_pass_rate != null ? (
                <>
                  <div className="flex items-center gap-1 mb-1">
                    <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
                    <p className="text-xs text-slate-500">Brand Check</p>
                  </div>
                  <p className={`text-2xl font-bold ${report.brand_check_pass_rate >= 0.8 ? 'text-emerald-600' : 'text-amber-600'}`}>
                    {(report.brand_check_pass_rate * 100).toFixed(0)}%
                  </p>
                </>
              ) : (
                <>
                  <div className="flex items-center gap-1 mb-1">
                    <AlertCircle className="w-3.5 h-3.5 text-slate-300" />
                    <p className="text-xs text-slate-500">Brand Check</p>
                  </div>
                  <p className="text-sm text-slate-400">No data</p>
                </>
              )}
            </div>
          </div>

          {/* Output by date chart */}
          {(report?.by_date.length ?? 0) > 0 && (
            <Card>
              <CardHeader>
                <h3 className="text-sm font-semibold text-slate-700">Assets Created by Date</h3>
              </CardHeader>
              <CardBody>
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={report!.by_date} barCategoryGap="30%">
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                    <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={d => d.slice(5)} />
                    <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                    <Tooltip contentStyle={{ fontSize: 11, borderRadius: 8, border: '1px solid #e2e8f0' }} />
                    <Bar dataKey="count" fill="#9333ea" radius={[4,4,0,0]} name="Assets" />
                  </BarChart>
                </ResponsiveContainer>
              </CardBody>
            </Card>
          )}

          {/* Status + Type breakdown */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {statusData.length > 0 && (
              <Card>
                <CardHeader><h3 className="text-sm font-semibold text-slate-700">By Status</h3></CardHeader>
                <CardBody>
                  <ResponsiveContainer width="100%" height={200}>
                    <PieChart>
                      <Pie data={statusData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={70} label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`} labelLine={false}>
                        {statusData.map((entry) => (
                          <Cell key={entry.name} fill={STATUS_COLORS[entry.name] ?? '#cbd5e1'} />
                        ))}
                      </Pie>
                      <Tooltip contentStyle={{ fontSize: 11, borderRadius: 8 }} />
                    </PieChart>
                  </ResponsiveContainer>
                </CardBody>
              </Card>
            )}

            {typeData.length > 0 && (
              <Card>
                <CardHeader><h3 className="text-sm font-semibold text-slate-700">By Asset Type</h3></CardHeader>
                <CardBody>
                  <ResponsiveContainer width="100%" height={200}>
                    <PieChart>
                      <Pie data={typeData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={70} label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`} labelLine={false}>
                        {typeData.map((entry, i) => (
                          <Cell key={entry.name} fill={TYPE_COLORS[i % TYPE_COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip contentStyle={{ fontSize: 11, borderRadius: 8 }} />
                    </PieChart>
                  </ResponsiveContainer>
                </CardBody>
              </Card>
            )}
          </div>

          {report?.total_assets === 0 && (
            <div className="py-12 text-center">
              <FileText className="w-7 h-7 text-slate-300 mx-auto mb-2" />
              <p className="text-sm text-slate-500">No assets created in this date range.</p>
            </div>
          )}
        </>
      )}
    </div>
  )
}
