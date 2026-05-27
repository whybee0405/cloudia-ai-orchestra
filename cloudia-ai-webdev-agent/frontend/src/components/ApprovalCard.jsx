import { useState } from 'react'
import { CheckCircle2, XCircle, RotateCcw, Clock, User } from 'lucide-react'
import { StatusBadge } from './StatusBadge'
import { useApprovals } from '../hooks/useApprovals'

function formatGateName(name) {
  if (!name) return 'Review'
  return name
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase())
}

function formatRelative(ts) {
  if (!ts) return ''
  const diff = Date.now() - new Date(ts).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.floor(hours / 24)}d ago`
}

function formatTimestamp(ts) {
  if (!ts) return ''
  return new Date(ts).toLocaleString('en-ZA', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function ApprovalCard({ gate, projectId, compact = false, reviewerName = 'operator' }) {
  const [action, setAction] = useState(null) // 'approve' | 'reject' | 'revision'
  const [notes, setNotes] = useState('')
  const [notesError, setNotesError] = useState('')
  const { approve, reject, requestRevision, isApproving, isRejecting, isRequestingRevision, error, clearError } = useApprovals(projectId)

  const isPending = gate.status === 'pending'
  const isLoading = isApproving || isRejecting || isRequestingRevision

  const handleApprove = async () => {
    clearError()
    await approve(gate.id, reviewerName)
    setAction(null)
  }

  const handleSubmitNotes = async (e) => {
    e.preventDefault()
    if (!notes.trim()) {
      setNotesError('Notes are required')
      return
    }
    setNotesError('')
    clearError()
    if (action === 'reject') {
      await reject(gate.id, notes.trim(), reviewerName)
    } else if (action === 'revision') {
      await requestRevision(gate.id, notes.trim(), reviewerName)
    }
    setNotes('')
    setAction(null)
  }

  const handleCancel = () => {
    setAction(null)
    setNotes('')
    setNotesError('')
    clearError()
  }

  return (
    <div className={`rounded-lg border ${
      gate.status === 'pending' ? 'border-yellow-800/40 bg-yellow-950/10' :
      gate.status === 'approved' ? 'border-green-800/40 bg-green-950/10' :
      gate.status === 'rejected' ? 'border-red-800/40 bg-red-950/10' :
      'border-orange-800/40 bg-orange-950/10'
    } ${compact ? 'p-3' : 'p-5'}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className={`font-medium text-slate-100 ${compact ? 'text-sm' : 'text-base'}`}>
              {formatGateName(gate.gate_name)}
            </h3>
            <StatusBadge status={gate.status} size="xs" />
          </div>
          <div className="mt-1 flex items-center gap-3 flex-wrap">
            <span className="flex items-center gap-1 text-xs text-slate-500">
              <Clock size={11} />
              Created {formatRelative(gate.created_at)}
            </span>
            {gate.reviewed_by && (
              <span className="flex items-center gap-1 text-xs text-slate-500">
                <User size={11} />
                {gate.reviewed_by}
              </span>
            )}
            {gate.reviewed_at && (
              <span className="text-xs text-slate-500">
                {formatTimestamp(gate.reviewed_at)}
              </span>
            )}
          </div>
        </div>
      </div>

      {gate.notes && !isPending && (
        <div className="mt-3 p-3 rounded bg-slate-900/50 border border-slate-700">
          <p className="text-xs text-slate-400 font-medium mb-1">Notes</p>
          <p className="text-sm text-slate-300">{gate.notes}</p>
        </div>
      )}

      {isPending && (
        <div className="mt-4">
          {error && (
            <p className="mb-3 text-xs text-red-400 bg-red-950/30 rounded px-2 py-1">{error}</p>
          )}

          {action === null && (
            <div className={`flex flex-wrap gap-2 ${compact ? '' : ''}`}>
              <button
                onClick={handleApprove}
                disabled={isLoading}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium bg-green-800/50 hover:bg-green-700/60 text-green-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <CheckCircle2 size={13} />
                {isApproving ? 'Approving...' : 'Approve'}
              </button>
              <button
                onClick={() => setAction('revision')}
                disabled={isLoading}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium bg-orange-900/40 hover:bg-orange-800/50 text-orange-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <RotateCcw size={13} />
                Request Revision
              </button>
              <button
                onClick={() => setAction('reject')}
                disabled={isLoading}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium bg-red-900/40 hover:bg-red-800/50 text-red-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <XCircle size={13} />
                Reject
              </button>
            </div>
          )}

          {(action === 'reject' || action === 'revision') && (
            <form onSubmit={handleSubmitNotes} className="space-y-2">
              <label className="block text-xs text-slate-400 font-medium">
                {action === 'reject' ? 'Rejection reason' : 'Revision notes'}{' '}
                <span className="text-red-400">*</span>
              </label>
              <textarea
                value={notes}
                onChange={e => { setNotes(e.target.value); setNotesError('') }}
                rows={3}
                placeholder={action === 'reject' ? 'Why is this being rejected?' : 'What needs to be changed?'}
                className="w-full rounded bg-slate-700 border border-slate-600 text-slate-100 text-sm px-3 py-2 focus:outline-none focus:border-blue-500 placeholder-slate-500 resize-none"
              />
              {notesError && <p className="text-xs text-red-400">{notesError}</p>}
              <div className="flex gap-2">
                <button
                  type="submit"
                  disabled={isLoading}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
                    action === 'reject'
                      ? 'bg-red-900/40 hover:bg-red-800/50 text-red-300'
                      : 'bg-orange-900/40 hover:bg-orange-800/50 text-orange-300'
                  }`}
                >
                  {action === 'reject'
                    ? (isRejecting ? 'Rejecting...' : 'Confirm Reject')
                    : (isRequestingRevision ? 'Requesting...' : 'Send Revision Request')}
                </button>
                <button
                  type="button"
                  onClick={handleCancel}
                  disabled={isLoading}
                  className="px-3 py-1.5 rounded text-xs font-medium bg-slate-700 hover:bg-slate-600 text-slate-300 transition-colors disabled:opacity-50"
                >
                  Cancel
                </button>
              </div>
            </form>
          )}
        </div>
      )}
    </div>
  )
}
