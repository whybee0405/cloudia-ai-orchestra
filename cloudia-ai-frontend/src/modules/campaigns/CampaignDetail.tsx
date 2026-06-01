import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, CheckCircle, XCircle, Pause, Play, Calendar, FileText, CheckSquare } from 'lucide-react'
import {
  getCampaign,
  pauseCampaign,
  resumeCampaign,
  approveGate,
  rejectGate,
  type ApprovalGate,
  type CalendarItem,
  type AssetListItem,
} from '@/api/campaigns'
import { Card, CardBody, CardHeader } from '@/shared/components/Card'
import { Button } from '@/shared/components/Button'
import { Badge } from '@/shared/components/Badge'
import { PageLoader } from '@/shared/components/LoadingSpinner'

const STATUS_BADGE: Record<string, 'default' | 'success' | 'warning' | 'danger' | 'info'> = {
  planned: 'default', active: 'success', running: 'info', paused: 'warning',
  halted: 'danger', completed: 'success',
}

type Tab = 'overview' | 'approvals' | 'calendar' | 'assets'

function GateRow({ gate, campaignId }: { gate: ApprovalGate; campaignId: number }) {
  const qc = useQueryClient()
  const [notes, setNotes] = useState('')
  const opts = {
    onSuccess: () => qc.invalidateQueries({ queryKey: ['campaign', campaignId] }),
  }
  const { mutate: approve, isPending: approving } = useMutation({
    mutationFn: () => approveGate(gate.id, { notes: notes || undefined, reviewed_by: 'operator' }),
    ...opts,
  })
  const { mutate: reject, isPending: rejecting } = useMutation({
    mutationFn: () => rejectGate(gate.id, { notes: notes || undefined, reviewed_by: 'operator' }),
    ...opts,
  })

  if (gate.status !== 'pending') {
    return (
      <div className="flex items-center gap-3 py-2 text-sm">
        <Badge variant={gate.status === 'approved' ? 'success' : 'danger'}>{gate.status}</Badge>
        <span className="text-slate-600 font-medium">{gate.gate_name}</span>
        {gate.notes && <span className="text-slate-400">— {gate.notes}</span>}
      </div>
    )
  }

  return (
    <div className="border border-amber-200 bg-amber-50 rounded-lg p-4 space-y-3">
      <div className="flex items-center gap-2">
        <Badge variant="warning">Pending</Badge>
        <span className="text-sm font-semibold text-slate-800">{gate.gate_name}</span>
      </div>
      <textarea
        className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-500 resize-none bg-white"
        rows={2}
        value={notes}
        onChange={e => setNotes(e.target.value)}
        placeholder="Optional review notes…"
      />
      <div className="flex items-center gap-2">
        <Button size="sm" onClick={() => approve()} loading={approving}>
          <CheckCircle className="w-3.5 h-3.5" /> Approve
        </Button>
        <Button size="sm" variant="danger" onClick={() => reject()} loading={rejecting}>
          <XCircle className="w-3.5 h-3.5" /> Reject
        </Button>
      </div>
    </div>
  )
}

function CalendarRow({ item }: { item: CalendarItem }) {
  const date = new Date(item.scheduled_for)
  return (
    <div className="flex items-center gap-4 py-2.5 border-b border-slate-100 last:border-0 text-sm">
      <span className="text-slate-400 w-28 shrink-0 text-xs">
        {date.toLocaleDateString('en-ZA', { day: 'numeric', month: 'short' })}
        {' '}
        {date.toLocaleTimeString('en-ZA', { hour: '2-digit', minute: '2-digit' })}
      </span>
      <span className="text-xs px-2 py-0.5 bg-purple-50 text-purple-700 rounded-md capitalize shrink-0">
        {item.platform}
      </span>
      <span className="text-xs text-slate-400 shrink-0">{item.content_type}</span>
      {item.topic && <span className="text-slate-600 truncate">{item.topic}</span>}
      <Badge
        variant={item.status === 'published' ? 'success' : item.status === 'planned' ? 'default' : 'info'}
        className="ml-auto shrink-0"
      >
        {item.status ?? 'planned'}
      </Badge>
    </div>
  )
}

function AssetRow({ asset }: { asset: AssetListItem }) {
  return (
    <div className="flex items-center gap-4 py-2.5 border-b border-slate-100 last:border-0 text-sm">
      <FileText className="w-4 h-4 text-slate-300 shrink-0" />
      <span className="font-medium text-slate-700 truncate">{asset.title ?? `${asset.asset_type} asset`}</span>
      {asset.content_type && <span className="text-xs text-slate-400">{asset.content_type}</span>}
      <Badge
        variant={asset.status === 'approved' ? 'success' : asset.status === 'draft' ? 'default' : 'warning'}
        className="ml-auto shrink-0"
      >
        {asset.status ?? 'draft'}
      </Badge>
    </div>
  )
}

export function CampaignDetail({ campaignId }: { campaignId: number }) {
  const { clientId } = useParams<{ clientId: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [tab, setTab] = useState<Tab>('overview')

  const { data: campaign, isLoading } = useQuery({
    queryKey: ['campaign', campaignId],
    queryFn: () => getCampaign(campaignId),
  })

  const { mutate: pause, isPending: pausing } = useMutation({
    mutationFn: () => pauseCampaign(campaignId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['campaign', campaignId] }),
  })
  const { mutate: resume, isPending: resuming } = useMutation({
    mutationFn: () => resumeCampaign(campaignId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['campaign', campaignId] }),
  })

  if (isLoading) return <PageLoader />
  if (!campaign) return <div className="p-8 text-sm text-red-600">Campaign not found.</div>

  const status = campaign.status ?? 'planned'
  const pendingGates = campaign.approval_gates.filter(g => g.status === 'pending')
  const tabs: { key: Tab; label: string; count?: number }[] = [
    { key: 'overview', label: 'Overview' },
    { key: 'approvals', label: 'Approvals', count: pendingGates.length || undefined },
    { key: 'calendar', label: 'Calendar', count: campaign.calendar_items.length || undefined },
    { key: 'assets', label: 'Assets', count: campaign.content_assets.length || undefined },
  ]

  return (
    <div className="p-4 md:p-8">
      <button
        onClick={() => navigate(`/clients/${clientId}/campaigns`)}
        className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 mb-6"
      >
        <ArrowLeft className="w-4 h-4" /> Back to Campaigns
      </button>

      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-3 mb-6">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2 md:gap-3 mb-1">
            <h1 className="text-xl md:text-2xl font-bold text-slate-900">{campaign.name}</h1>
            <Badge variant={STATUS_BADGE[status] ?? 'default'}>{status}</Badge>
          </div>
          {campaign.goal && <p className="text-sm text-slate-500">{campaign.goal}</p>}
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {(status === 'active' || status === 'running') && (
            <Button variant="secondary" size="sm" onClick={() => pause()} loading={pausing}>
              <Pause className="w-3.5 h-3.5" /> Pause
            </Button>
          )}
          {status === 'paused' && (
            <Button size="sm" onClick={() => resume()} loading={resuming}>
              <Play className="w-3.5 h-3.5" /> Resume
            </Button>
          )}
        </div>
      </div>

      {/* Pending approval banner */}
      {pendingGates.length > 0 && (
        <div className="mb-5 flex flex-wrap items-center gap-2 bg-amber-50 border border-amber-200 text-amber-800 text-sm rounded-lg px-4 py-3">
          <CheckSquare className="w-4 h-4 shrink-0" />
          <span>
            <strong>{pendingGates.length}</strong> approval gate{pendingGates.length > 1 ? 's' : ''} waiting for review.
          </span>
          <button onClick={() => setTab('approvals')} className="ml-1 underline underline-offset-2">
            Review now →
          </button>
        </div>
      )}

      {/* Tabs — scrollable on mobile */}
      <div className="flex items-center gap-1 border-b border-slate-200 mb-5 overflow-x-auto">
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-3 md:px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px whitespace-nowrap ${
              tab === t.key
                ? 'border-purple-600 text-purple-700'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            {t.label}
            {t.count != null && (
              <span className="ml-1.5 bg-slate-100 text-slate-600 text-xs px-1.5 py-0.5 rounded-full">
                {t.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === 'overview' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <Card>
            <CardHeader><h2 className="text-sm font-semibold text-slate-700">Details</h2></CardHeader>
            <CardBody className="space-y-3 text-sm">
              {campaign.platforms?.length > 0 && (
                <div>
                  <span className="text-xs text-slate-400 block mb-1">Platforms</span>
                  <div className="flex flex-wrap gap-1">
                    {campaign.platforms.map(p => (
                      <span key={p} className="text-xs px-2 py-0.5 bg-purple-50 text-purple-700 rounded-md capitalize">{p}</span>
                    ))}
                  </div>
                </div>
              )}
              {campaign.duration_days && (
                <div>
                  <span className="text-xs text-slate-400 block mb-0.5">Duration</span>
                  <span>{campaign.duration_days} days</span>
                </div>
              )}
              {campaign.posts_per_week && (
                <div>
                  <span className="text-xs text-slate-400 block mb-0.5">Posting frequency</span>
                  <span>{campaign.posts_per_week}× per week</span>
                </div>
              )}
              {campaign.start_date && (
                <div>
                  <span className="text-xs text-slate-400 block mb-0.5">Start date</span>
                  <span>{new Date(campaign.start_date).toLocaleDateString('en-ZA', { weekday: 'short', day: 'numeric', month: 'long', year: 'numeric' })}</span>
                </div>
              )}
            </CardBody>
          </Card>
          <Card>
            <CardHeader><h2 className="text-sm font-semibold text-slate-700">Brief</h2></CardHeader>
            <CardBody className="space-y-3 text-sm">
              {campaign.target_audience && (
                <div>
                  <span className="text-xs text-slate-400 block mb-0.5">Target audience</span>
                  <p className="text-slate-600">{campaign.target_audience}</p>
                </div>
              )}
              {Object.entries(campaign.brief ?? {}).map(([k, v]) => (
                <div key={k}>
                  <span className="text-xs text-slate-400 block mb-0.5 capitalize">{k.replace(/_/g, ' ')}</span>
                  <p className="text-slate-600">{String(v)}</p>
                </div>
              ))}
              {campaign.operator_notes && (
                <div>
                  <span className="text-xs text-slate-400 block mb-0.5">Operator notes</span>
                  <p className="text-slate-500 italic">{campaign.operator_notes}</p>
                </div>
              )}
            </CardBody>
          </Card>
        </div>
      )}

      {tab === 'approvals' && (
        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold text-slate-700">Approval Gates</h2>
          </CardHeader>
          <CardBody className="space-y-3">
            {campaign.approval_gates.length === 0 && (
              <p className="text-sm text-slate-400 py-4 text-center">No approval gates for this campaign.</p>
            )}
            {campaign.approval_gates
              .slice()
              .sort((a, b) => (a.pipeline_order ?? 0) - (b.pipeline_order ?? 0))
              .map(gate => (
                <GateRow key={gate.id} gate={gate} campaignId={campaignId} />
              ))}
          </CardBody>
        </Card>
      )}

      {tab === 'calendar' && (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4 text-slate-400" />
              <h2 className="text-sm font-semibold text-slate-700">Content Calendar</h2>
            </div>
          </CardHeader>
          <CardBody>
            {campaign.calendar_items.length === 0 && (
              <p className="text-sm text-slate-400 py-4 text-center">Calendar not generated yet.</p>
            )}
            {campaign.calendar_items
              .slice()
              .sort((a, b) => new Date(a.scheduled_for).getTime() - new Date(b.scheduled_for).getTime())
              .map(item => <CalendarRow key={item.id} item={item} />)}
          </CardBody>
        </Card>
      )}

      {tab === 'assets' && (
        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold text-slate-700">Content Assets</h2>
          </CardHeader>
          <CardBody>
            {campaign.content_assets.length === 0 && (
              <p className="text-sm text-slate-400 py-4 text-center">No assets generated yet.</p>
            )}
            {campaign.content_assets.map(asset => <AssetRow key={asset.id} asset={asset} />)}
          </CardBody>
        </Card>
      )}
    </div>
  )
}
