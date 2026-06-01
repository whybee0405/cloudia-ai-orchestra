import { useParams } from 'react-router-dom'
import { useQueries } from '@tanstack/react-query'
import { Megaphone, BarChart2, Globe, Info, CheckCircle, XCircle, Clock } from 'lucide-react'
import { getDirectorClientByBrandDna, listCampaigns } from '@/api/campaigns'
import { getAccountByBrandDna, listAuditLog } from '@/api/google-ads'
import { getClientByBrandDna, listProjects } from '@/api/webdev'
import { Card, CardBody } from '@/shared/components/Card'
import { Badge } from '@/shared/components/Badge'
import { PageLoader } from '@/shared/components/LoadingSpinner'

type ServiceKey = 'campaigns' | 'google-ads' | 'webdev'

interface FeedEvent {
  id: string
  service: ServiceKey
  timestamp: string
  title: string
  description: string | null
  status: string | null
}

const SERVICE_CONFIG: Record<ServiceKey, {
  label: string
  color: string
  bg: string
  Icon: typeof Megaphone
}> = {
  'campaigns': {
    label: 'Campaigns', color: 'text-purple-600', bg: 'bg-purple-50', Icon: Megaphone,
  },
  'google-ads': {
    label: 'Google Ads', color: 'text-blue-600', bg: 'bg-blue-50', Icon: BarChart2,
  },
  'webdev': {
    label: 'Websites', color: 'text-emerald-600', bg: 'bg-emerald-50', Icon: Globe,
  },
}

const STATUS_ICONS: Record<string, typeof CheckCircle> = {
  completed: CheckCircle,
  active:    CheckCircle,
  published: CheckCircle,
  running:   Clock,
  pending:   Clock,
  planned:   Clock,
  failed:    XCircle,
  cancelled: XCircle,
  rejected:  XCircle,
}

const STATUS_BADGE: Record<string, 'success' | 'warning' | 'danger' | 'info' | 'default'> = {
  completed: 'success',
  active:    'success',
  published: 'success',
  running:   'info',
  pending:   'warning',
  planned:   'default',
  failed:    'danger',
  cancelled: 'danger',
  rejected:  'danger',
}

function FeedRow({ event }: { event: FeedEvent }) {
  const cfg = SERVICE_CONFIG[event.service]
  const StatusIcon = event.status ? (STATUS_ICONS[event.status] ?? Info) : Info
  return (
    <div className="flex items-start gap-4 py-3.5 border-b border-slate-100 last:border-0">
      <div className={`w-8 h-8 rounded-lg ${cfg.bg} flex items-center justify-center shrink-0`}>
        <cfg.Icon className={`w-3.5 h-3.5 ${cfg.color}`} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex flex-wrap items-center gap-2 mb-0.5">
          <span className="text-xs font-semibold text-slate-800">{event.title}</span>
          {event.status && (
            <Badge variant={STATUS_BADGE[event.status] ?? 'default'} className="capitalize text-xs">
              {event.status}
            </Badge>
          )}
          <span className="text-xs text-slate-400 ml-auto shrink-0">
            {new Date(event.timestamp).toLocaleDateString('en-ZA', {
              day: 'numeric', month: 'short', year: 'numeric',
            })}
          </span>
        </div>
        {event.description && (
          <p className="text-xs text-slate-500 truncate">{event.description}</p>
        )}
        <div className="flex items-center gap-1 mt-0.5">
          <StatusIcon className="w-3 h-3 text-slate-300" />
          <p className="text-xs text-slate-400">{cfg.label}</p>
        </div>
      </div>
    </div>
  )
}

export function CrossServiceFeed() {
  const { clientId } = useParams<{ clientId: string }>()
  const id = clientId!

  // Resolve service-specific IDs
  const [directorQ, adsAccountQ, webdevClientQ] = useQueries({
    queries: [
      {
        queryKey: ['director-client', id],
        queryFn: () => getDirectorClientByBrandDna(id),
        retry: false,
      },
      {
        queryKey: ['ads-account', id],
        queryFn: () => getAccountByBrandDna(id),
        retry: false,
      },
      {
        queryKey: ['webdev-client', id],
        queryFn: () => getClientByBrandDna(id),
        retry: false,
      },
    ],
  })

  const directorId  = directorQ.data?.id
  const adsId       = adsAccountQ.data?.id
  const webdevId    = webdevClientQ.data?.id

  // Fetch service data
  const [campaignsQ, auditQ, projectsQ] = useQueries({
    queries: [
      {
        queryKey: ['reports-feed-campaigns', directorId],
        queryFn: () => listCampaigns(directorId!),
        enabled: !!directorId,
      },
      {
        queryKey: ['reports-feed-audit', adsId],
        queryFn: () => listAuditLog(adsId),
        enabled: !!adsId,
      },
      {
        queryKey: ['reports-feed-projects', webdevId],
        queryFn: () => listProjects(webdevId),
        enabled: !!webdevId,
      },
    ],
  })

  const anyLoading =
    directorQ.isLoading || adsAccountQ.isLoading || webdevClientQ.isLoading ||
    campaignsQ.isLoading || auditQ.isLoading || projectsQ.isLoading

  // Build unified event list
  const events: FeedEvent[] = []

  for (const c of campaignsQ.data ?? []) {
    events.push({
      id: `campaign-${c.id}`,
      service: 'campaigns',
      timestamp: c.created_at ?? new Date(0).toISOString(),
      title: c.name,
      description: c.goal ?? null,
      status: c.status,
    })
  }

  for (const e of auditQ.data ?? []) {
    events.push({
      id: `audit-${e.id}`,
      service: 'google-ads',
      timestamp: e.run_time,
      title: e.anomaly_type ? e.anomaly_type.replace(/_/g, ' ') : 'Anomaly detected',
      description: e.diagnosis,
      status: e.severity?.toLowerCase() ?? null,
    })
  }

  for (const p of projectsQ.data ?? []) {
    events.push({
      id: `project-${p.id}`,
      service: 'webdev',
      timestamp: p.created_at,
      title: `${p.platform ? p.platform.charAt(0).toUpperCase() + p.platform.slice(1) : 'Website'} project`,
      description: p.site_url ?? null,
      status: p.status,
    })
  }

  events.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())

  const connectedCount = [directorQ.data, adsAccountQ.data, webdevClientQ.data].filter(Boolean).length

  return (
    <div className="space-y-5">
      {/* Service connection status */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {(
          [
            { key: 'campaigns' as ServiceKey, label: 'Campaigns',  ok: !!directorQ.data  },
            { key: 'google-ads' as ServiceKey, label: 'Google Ads', ok: !!adsAccountQ.data },
            { key: 'webdev'    as ServiceKey, label: 'Websites',   ok: !!webdevClientQ.data },
          ] as const
        ).map(({ key, label, ok }) => (
            <div key={key} className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3">
              <CheckCircle className={`w-4 h-4 shrink-0 ${ok ? 'text-emerald-500' : 'text-slate-300'}`} />
              <div>
                <p className="text-xs font-medium text-slate-700">{label}</p>
                <p className="text-xs text-slate-400">{ok ? 'Showing activity' : 'Not connected'}</p>
              </div>
            </div>
        ))}
      </div>

      {anyLoading && <PageLoader />}

      {!anyLoading && events.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <Info className="w-8 h-8 text-slate-300 mb-3" />
          <p className="text-sm text-slate-500">No activity found yet.</p>
          <p className="text-xs text-slate-400 mt-1">
            {connectedCount === 0
              ? 'Connect at least one service to see activity here.'
              : 'Activity will appear here as campaigns, projects, and anomalies are created.'}
          </p>
        </div>
      )}

      {!anyLoading && events.length > 0 && (
        <Card>
          <CardBody>
            <div>
              {events.map(e => <FeedRow key={e.id} event={e} />)}
            </div>
          </CardBody>
        </Card>
      )}
    </div>
  )
}
