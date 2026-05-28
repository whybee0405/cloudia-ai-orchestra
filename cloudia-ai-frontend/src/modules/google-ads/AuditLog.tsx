import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, Info } from 'lucide-react'
import { listAuditLog, type AuditEntry } from '@/api/google-ads'
import { Card, CardBody, CardHeader } from '@/shared/components/Card'
import { Badge } from '@/shared/components/Badge'
import { PageLoader } from '@/shared/components/LoadingSpinner'

const SEVERITY_BADGE: Record<string, 'default' | 'success' | 'warning' | 'danger' | 'info'> = {
  LOW: 'default',
  MEDIUM: 'info',
  HIGH: 'warning',
  CRITICAL: 'danger',
}

const SEVERITY_ICON: Record<string, typeof AlertTriangle> = {
  LOW: Info,
  MEDIUM: Info,
  HIGH: AlertTriangle,
  CRITICAL: AlertTriangle,
}

const SEVERITIES = ['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'] as const

function AuditRow({ entry }: { entry: AuditEntry }) {
  const sev = entry.severity ?? 'LOW'
  const Icon = SEVERITY_ICON[sev] ?? Info

  return (
    <div className="py-4 border-b border-slate-100 last:border-0">
      <div className="flex items-start gap-3">
        <Icon className={`w-4 h-4 mt-0.5 shrink-0 ${sev === 'CRITICAL' || sev === 'HIGH' ? 'text-red-500' : sev === 'MEDIUM' ? 'text-blue-500' : 'text-slate-400'}`} />
        <div className="flex-1 min-w-0 space-y-1.5">
          <div className="flex items-center gap-2">
            <Badge variant={SEVERITY_BADGE[sev] ?? 'default'}>{sev}</Badge>
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
        </div>
      </div>
    </div>
  )
}

export function AuditLog({ accountId }: { accountId: number }) {
  const [severity, setSeverity] = useState<string>('ALL')

  const { data: entries, isLoading } = useQuery({
    queryKey: ['ads-audit', accountId, severity],
    queryFn: () => listAuditLog(accountId, severity === 'ALL' ? undefined : severity),
  })

  if (isLoading) return <PageLoader />

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-700">Audit Log</h2>
            <div className="flex items-center gap-1 bg-slate-100 rounded-lg p-1">
              {SEVERITIES.map(s => (
                <button
                  key={s}
                  onClick={() => setSeverity(s)}
                  className={`text-xs px-2.5 py-1 rounded-md capitalize transition-colors ${
                    severity === s
                      ? 'bg-white text-slate-800 shadow-sm font-medium'
                      : 'text-slate-500 hover:text-slate-700'
                  }`}
                >
                  {s === 'ALL' ? 'All' : s.charAt(0) + s.slice(1).toLowerCase()}
                </button>
              ))}
            </div>
          </div>
        </CardHeader>
        <CardBody className="py-0">
          {entries?.length === 0 && (
            <div className="py-12 text-center">
              <p className="text-sm text-slate-400">No anomalies recorded yet.</p>
            </div>
          )}
          {entries?.map(e => <AuditRow key={e.id} entry={e} />)}
        </CardBody>
      </Card>
    </div>
  )
}
