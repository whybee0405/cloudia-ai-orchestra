import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { CheckCircle, XCircle, Play, ChevronDown, ChevronUp } from 'lucide-react'
import {
  listQueue,
  approveQueueItem,
  rejectQueueItem,
  executeQueueItem,
  type QueueItem,
} from '@/api/google-ads'
import { Card, CardBody, CardHeader } from '@/shared/components/Card'
import { Button } from '@/shared/components/Button'
import { Badge } from '@/shared/components/Badge'
import { PageLoader } from '@/shared/components/LoadingSpinner'

const STATUS_BADGE: Record<string, 'default' | 'success' | 'warning' | 'danger' | 'info'> = {
  pending: 'warning',
  approved: 'info',
  rejected: 'danger',
  executed: 'success',
  failed: 'danger',
}

function PayloadViewer({ payload }: { payload: Record<string, unknown> | null }) {
  const [open, setOpen] = useState(false)
  if (!payload) return null
  return (
    <div className="mt-2">
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-1 text-xs text-slate-400 hover:text-slate-600 transition-colors"
      >
        {open ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        {open ? 'Hide' : 'Show'} payload
      </button>
      {open && (
        <pre className="mt-2 text-xs bg-slate-50 border border-slate-100 rounded-lg p-3 overflow-x-auto text-slate-600">
          {JSON.stringify(payload, null, 2)}
        </pre>
      )}
    </div>
  )
}

function QueueCard({ item, onAction }: { item: QueueItem; onAction: () => void }) {
  const [reviewer, setReviewer] = useState('operator')

  const opts = { onSuccess: onAction }
  const { mutate: approve, isPending: approving } = useMutation({
    mutationFn: () => approveQueueItem(item.id, reviewer),
    ...opts,
  })
  const { mutate: reject, isPending: rejecting } = useMutation({
    mutationFn: () => rejectQueueItem(item.id, reviewer),
    ...opts,
  })
  const { mutate: execute, isPending: executing } = useMutation({
    mutationFn: () => executeQueueItem(item.id),
    ...opts,
  })

  const status = item.status
  const isPending = status === 'pending'
  const isApproved = status === 'approved'

  return (
    <Card className={isPending ? 'border-amber-200 bg-amber-50/30' : ''}>
      <CardBody className="space-y-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <Badge variant={STATUS_BADGE[status] ?? 'default'}>{status}</Badge>
              <span className="text-xs text-slate-400">{item.agent_name}</span>
            </div>
            <p className="text-sm font-semibold text-slate-800">{item.action_type.replace(/_/g, ' ')}</p>
          </div>
          <span className="text-xs text-slate-400 shrink-0">
            {new Date(item.created_at).toLocaleDateString('en-ZA', {
              day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
            })}
          </span>
        </div>

        {item.reasoning && (
          <p className="text-xs text-slate-600 leading-relaxed">{item.reasoning}</p>
        )}

        <PayloadViewer payload={item.action_payload} />

        {item.reviewed_by && (
          <p className="text-xs text-slate-400">
            Reviewed by <strong>{item.reviewed_by}</strong>
            {item.reviewed_at && ` · ${new Date(item.reviewed_at).toLocaleDateString('en-ZA')}`}
          </p>
        )}

        {isPending && (
          <div className="flex items-center gap-2 pt-1">
            <input
              className="flex-1 text-xs border border-slate-200 rounded-md px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-brand-500"
              placeholder="Reviewer name / email"
              value={reviewer}
              onChange={e => setReviewer(e.target.value)}
            />
            <Button size="sm" onClick={() => approve()} loading={approving} disabled={!reviewer.trim()}>
              <CheckCircle className="w-3.5 h-3.5" /> Approve
            </Button>
            <Button size="sm" variant="danger" onClick={() => reject()} loading={rejecting} disabled={!reviewer.trim()}>
              <XCircle className="w-3.5 h-3.5" /> Reject
            </Button>
          </div>
        )}

        {isApproved && (
          <div className="pt-1">
            <Button size="sm" variant="secondary" onClick={() => execute()} loading={executing}>
              <Play className="w-3.5 h-3.5" /> Execute in Google Ads
            </Button>
          </div>
        )}
      </CardBody>
    </Card>
  )
}

export function ApprovalQueue({ accountId }: { accountId: number }) {
  const qc = useQueryClient()
  const [statusFilter, setStatusFilter] = useState<'pending' | 'approved' | 'all'>('pending')

  const { data: items, isLoading } = useQuery({
    queryKey: ['ads-queue', accountId],
    queryFn: () => listQueue(accountId),
    refetchInterval: 30_000,
  })

  if (isLoading) return <PageLoader />

  const filtered = (items ?? []).filter(i => {
    if (statusFilter === 'pending') return i.status === 'pending'
    if (statusFilter === 'approved') return i.status === 'approved'
    return true
  })

  const pendingCount = (items ?? []).filter(i => i.status === 'pending').length

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-semibold text-slate-700">Approval Queue</h2>
              {pendingCount > 0 && (
                <span className="bg-amber-100 text-amber-700 text-xs font-medium px-2 py-0.5 rounded-full">
                  {pendingCount} pending
                </span>
              )}
            </div>
            <div className="flex items-center gap-1 bg-slate-100 rounded-lg p-1">
              {(['pending', 'approved', 'all'] as const).map(f => (
                <button
                  key={f}
                  onClick={() => setStatusFilter(f)}
                  className={`text-xs px-2.5 py-1 rounded-md capitalize transition-colors ${
                    statusFilter === f
                      ? 'bg-white text-slate-800 shadow-sm font-medium'
                      : 'text-slate-500 hover:text-slate-700'
                  }`}
                >
                  {f}
                </button>
              ))}
            </div>
          </div>
        </CardHeader>
      </Card>

      {filtered.length === 0 && (
        <Card>
          <CardBody className="py-12 text-center">
            <p className="text-sm text-slate-400">
              {statusFilter === 'pending' ? 'No pending items — all clear!' : 'No items found.'}
            </p>
          </CardBody>
        </Card>
      )}

      {filtered.map(item => (
        <QueueCard
          key={item.id}
          item={item}
          onAction={() => qc.invalidateQueries({ queryKey: ['ads-queue', accountId] })}
        />
      ))}
    </div>
  )
}
