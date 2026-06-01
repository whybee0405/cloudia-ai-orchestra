import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from 'recharts'
import { AlertTriangle, Info, CheckCircle } from 'lucide-react'
import { getAccountByBrandDna, listAuditLog, type AuditEntry } from '@/api/google-ads'
import { Card, CardBody, CardHeader } from '@/shared/components/Card'
import { Badge } from '@/shared/components/Badge'
import { PageLoader } from '@/shared/components/LoadingSpinner'

const SEVERITIES = ['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'] as const
type SeverityFilter = typeof SEVERITIES[number]

const SEV_BADGE: Record<string, 'default' | 'success' | 'warning' | 'danger' | 'info'> = {
  LOW: 'default', MEDIUM: 'info', HIGH: 'warning', CRITICAL: 'danger',
}

const SEV_COLOR: Record<string, string> = {
  CRITICAL: '#ef4444',
  HIGH:     '#f97316',
  MEDIUM:   '#3b82f6',
  LOW:      '#94a3b8',
}

function buildWeeklyChart(entries: AuditEntry[]) {
  const buckets: Record<string, Record<string, number>> = {}
  for (const e of entries) {
    const d = new Date(e.run_time)
    const monday = new Date(d)
    monday.setDate(d.getDate() - ((d.getDay() + 6) % 7))
    const key = monday.toLocaleDateString('en-ZA', { day: 'numeric', month: 'short' })
    if (!buckets[key]) buckets[key] = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 }
    buckets[key][(e.severity ?? 'LOW')]++
  }
  return Object.entries(buckets)
    .slice(-10)
    .map(([week, counts]) => ({ week, ...counts }))
}

function AuditRow({ entry }: { entry: AuditEntry }) {
  const sev = entry.severity ?? 'LOW'
  const Icon = sev === 'CRITICAL' || sev === 'HIGH' ? AlertTriangle : Info

  return (
    <div className="py-3.5 border-b border-slate-100 last:border-0">
      <div className="flex items-start gap-3">
        <Icon className={`w-4 h-4 mt-0.5 shrink-0 ${sev === 'CRITICAL' || sev === 'HIGH' ? 'text-red-500' : sev === 'MEDIUM' ? 'text-blue-500' : 'text-slate-400'}`} />
        <div className="flex-1 min-w-0 space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={SEV_BADGE[sev] ?? 'default'}>{sev}</Badge>
            {entry.anomaly_type && (
              <span className="text-xs font-medium text-slate-700">
                {entry.anomaly_type.replace(/_/g, ' ')}
              </span>
            )}
            {entry.campaign_id && (
              <span className="text-xs text-slate-400">Campaign {entry.campaign_id}</span>
            )}
            <span className="text-xs text-slate-400 ml-auto shrink-0">
              {new Date(entry.run_time).toLocaleDateString('en-ZA', {
                day: 'numeric', month: 'short', year: 'numeric',
                hour: '2-digit', minute: '2-digit',
              })}
            </span>
          </div>
          {entry.diagnosis && (
            <p className="text-xs text-slate-600 leading-relaxed">{entry.diagnosis}</p>
          )}
          {entry.recommended_action && (
            <p className="text-xs text-slate-500 italic">{entry.recommended_action}</p>
          )}
          {entry.acknowledged && (
            <div className="flex items-center gap-1 mt-1">
              <CheckCircle className="w-3 h-3 text-emerald-500" />
              <span className="text-xs text-emerald-600">Acknowledged</span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export function AnomalyHistoryReport() {
  const { clientId } = useParams<{ clientId: string }>()
  const [severity, setSeverity] = useState<SeverityFilter>('ALL')

  const { data: account, isLoading: accountLoading, error: accountError } = useQuery({
    queryKey: ['ads-account', clientId],
    queryFn: () => getAccountByBrandDna(clientId!),
    retry: false,
    enabled: !!clientId,
  })

  const { data: entries = [], isLoading: entriesLoading } = useQuery({
    queryKey: ['reports-anomalies', account?.id, severity],
    queryFn: () => listAuditLog(account!.id, severity === 'ALL' ? undefined : severity),
    enabled: !!account?.id,
  })

  if (accountLoading) return <PageLoader />

  const is404 = accountError instanceof Error && accountError.message.startsWith('404')
  if (is404 || !account) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <AlertTriangle className="w-8 h-8 text-slate-300 mb-3" />
        <p className="text-sm text-slate-500">No Google Ads account linked to this client.</p>
        <p className="text-xs text-slate-400 mt-1">Connect an account from the Google Ads module to see anomaly history.</p>
      </div>
    )
  }

  const chartData = buildWeeklyChart(entries)
  return (
    <div className="space-y-5">
      {/* Stats strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {(['CRITICAL','HIGH','MEDIUM','LOW'] as const).map(s => {
          const count = entries.filter(e => e.severity === s).length
          return (
            <div key={s} className="rounded-xl border border-slate-200 bg-white px-4 py-3">
              <p className="text-xs text-slate-500 mb-1">{s}</p>
              <p className="text-2xl font-bold" style={{ color: SEV_COLOR[s] }}>{count}</p>
            </div>
          )
        })}
      </div>

      {/* Weekly chart */}
      {chartData.length > 0 && (
        <Card>
          <CardHeader>
            <h3 className="text-sm font-semibold text-slate-700">Anomalies by Week</h3>
          </CardHeader>
          <CardBody>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={chartData} barCategoryGap="30%">
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="week" tick={{ fontSize: 11 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                <Tooltip contentStyle={{ fontSize: 11, borderRadius: 8, border: '1px solid #e2e8f0' }} />
                {(['CRITICAL','HIGH','MEDIUM','LOW'] as const).map(s => (
                  <Bar key={s} dataKey={s} stackId="a" fill={SEV_COLOR[s]} radius={s === 'LOW' ? [4,4,0,0] : [0,0,0,0]} />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </CardBody>
        </Card>
      )}

      {/* Log table */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-700">
              Anomaly Log
              {account.customer_id && (
                <span className="ml-2 text-xs font-normal text-slate-400">Account {account.customer_id}</span>
              )}
            </h3>
            <div className="flex items-center gap-1 bg-slate-100 rounded-lg p-1">
              {SEVERITIES.map(s => (
                <button
                  key={s}
                  onClick={() => setSeverity(s)}
                  className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors ${
                    severity === s ? 'bg-white shadow-sm text-slate-800' : 'text-slate-500 hover:text-slate-700'
                  }`}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        </CardHeader>
        <CardBody>
          {entriesLoading ? (
            <PageLoader />
          ) : entries.length === 0 ? (
            <div className="py-8 text-center">
              <CheckCircle className="w-7 h-7 text-emerald-400 mx-auto mb-2" />
              <p className="text-sm text-slate-500">No anomalies found.</p>
            </div>
          ) : (
            <div>
              {entries.map(e => <AuditRow key={e.id} entry={e} />)}
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  )
}
