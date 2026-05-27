import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { CheckCircle2, Clock, Loader2, AlertCircle, Inbox } from 'lucide-react'
import { fetchPendingApprovals } from '../api/approvals'
import { ApprovalCard } from '../components/ApprovalCard'

function formatRelative(ts) {
  if (!ts) return ''
  const diff = Date.now() - new Date(ts).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

function categoriseGate(gateName) {
  const name = (gateName || '').toLowerCase()
  if (name.includes('content')) return 'Content Reviews'
  if (name.includes('store') || name.includes('shopify')) return 'Store Reviews'
  if (name.includes('site') || name.includes('wordpress')) return 'Site Reviews'
  return 'Other Reviews'
}

const CATEGORY_ORDER = ['Content Reviews', 'Site Reviews', 'Store Reviews', 'Other Reviews']

export default function ApprovalQueue() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['approvals'],
    queryFn: fetchPendingApprovals,
    refetchInterval: 30000,
  })

  const approvals = Array.isArray(data) ? data : data?.results || []

  // Group by category
  const grouped = {}
  approvals.forEach(approval => {
    const cat = categoriseGate(approval.gate_name)
    if (!grouped[cat]) grouped[cat] = []
    grouped[cat].push(approval)
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 size={24} className="animate-spin text-slate-500" />
        <span className="ml-3 text-slate-400 text-sm">Loading approvals...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center gap-2 p-4 rounded-lg bg-red-950/30 border border-red-900/40 text-red-400 text-sm">
          <AlertCircle size={16} />
          {error.message}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-100">Approval Queue</h1>
          <p className="text-sm text-slate-400 mt-0.5">
            {approvals.length === 0
              ? 'No pending approvals'
              : `${approvals.length} gate${approvals.length > 1 ? 's' : ''} awaiting review`}
          </p>
        </div>
        {approvals.length > 0 && (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-amber-900/30 border border-amber-800/40">
            <Clock size={13} className="text-amber-400" />
            <span className="text-xs font-medium text-amber-300">{approvals.length} pending</span>
          </div>
        )}
      </div>

      {approvals.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 gap-4">
          <div className="w-16 h-16 rounded-full bg-green-900/20 border border-green-800/30 flex items-center justify-center">
            <CheckCircle2 size={28} className="text-green-400" />
          </div>
          <div className="text-center">
            <p className="text-slate-300 font-medium mb-1">All caught up</p>
            <p className="text-sm text-slate-500">No pending approvals at this time</p>
          </div>
        </div>
      ) : (
        <div className="space-y-8">
          {CATEGORY_ORDER.filter(cat => grouped[cat]).map(category => (
            <div key={category}>
              <div className="flex items-center gap-3 mb-4">
                <h2 className="text-sm font-semibold text-slate-300">{category}</h2>
                <span className="text-xs px-2 py-0.5 rounded-full bg-slate-700 text-slate-400">
                  {grouped[category].length}
                </span>
              </div>
              <div className="space-y-3">
                {grouped[category].map(approval => (
                  <div key={approval.id} className="space-y-2">
                    {/* Project context header */}
                    <div className="flex items-center gap-3 px-1">
                      <Link
                        to={`/projects/${approval.project_id}`}
                        className="text-xs text-blue-400 hover:text-blue-300 transition-colors font-mono"
                      >
                        #{approval.project_id || '—'}
                      </Link>
                      {approval.client_name && (
                        <span className="text-xs text-slate-400">{approval.client_name}</span>
                      )}
                      <span className="text-xs text-slate-500 ml-auto flex items-center gap-1">
                        <Clock size={10} />
                        Waiting {formatRelative(approval.created_at)}
                      </span>
                    </div>
                    <ApprovalCard
                      gate={approval}
                      projectId={approval.project_id}
                      compact={false}
                    />
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
