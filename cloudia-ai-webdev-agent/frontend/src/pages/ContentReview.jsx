import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, CheckCircle2, Loader2, AlertCircle, Filter } from 'lucide-react'
import { fetchProjectContent, bulkApproveContent } from '../api/content'
import { fetchProject } from '../api/projects'
import { ContentEditor } from '../components/ContentEditor'

const STATUS_FILTERS = [
  { key: '', label: 'All' },
  { key: 'draft', label: 'Draft' },
  { key: 'approved', label: 'Approved' },
  { key: 'revision_requested', label: 'Revision Requested' },
]

export default function ContentReview() {
  const { id } = useParams()
  const queryClient = useQueryClient()
  const [statusFilter, setStatusFilter] = useState('')
  const [bulkError, setBulkError] = useState(null)
  const [bulkSuccess, setBulkSuccess] = useState(false)

  const { data: project } = useQuery({
    queryKey: ['project', id],
    queryFn: () => fetchProject(id),
  })

  const { data: contentData, isLoading, error } = useQuery({
    queryKey: ['content', id],
    queryFn: () => fetchProjectContent(id),
    refetchInterval: 15000,
  })

  const bulkMutation = useMutation({
    mutationFn: () => bulkApproveContent(id),
    onSuccess: () => {
      setBulkError(null)
      setBulkSuccess(true)
      queryClient.invalidateQueries({ queryKey: ['content', id] })
      setTimeout(() => setBulkSuccess(false), 3000)
    },
    onError: (err) => {
      setBulkError(err.message)
    },
  })

  const pieces = Array.isArray(contentData) ? contentData : contentData?.results || []
  const clientName = project?.client_name || project?.brief?.business_name || `Project #${id}`

  const filtered = statusFilter ? pieces.filter(p => p.status === statusFilter) : pieces
  const approvedCount = pieces.filter(p => p.status === 'approved').length
  const draftCount = pieces.filter(p => p.status === 'draft').length

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 size={24} className="animate-spin text-slate-500" />
        <span className="ml-3 text-slate-400 text-sm">Loading content...</span>
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
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3">
          <Link
            to={`/projects/${id}`}
            className="flex items-center gap-1.5 text-slate-400 hover:text-slate-200 text-sm transition-colors"
          >
            <ArrowLeft size={16} />
            Back to Project
          </Link>
          <div className="w-px h-4 bg-slate-700" />
          <div>
            <h1 className="text-xl font-semibold text-slate-100">Content Review</h1>
            <p className="text-sm text-slate-400 mt-0.5">
              {clientName} — {approvedCount} of {pieces.length} approved
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {draftCount > 0 && (
            <button
              onClick={() => { setBulkError(null); bulkMutation.mutate() }}
              disabled={bulkMutation.isPending}
              className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-green-800/50 hover:bg-green-700/60 text-green-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <CheckCircle2 size={15} />
              {bulkMutation.isPending ? 'Approving All...' : `Approve All (${draftCount} draft${draftCount > 1 ? 's' : ''})`}
            </button>
          )}
        </div>
      </div>

      {/* Progress bar */}
      {pieces.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs text-slate-500">{approvedCount} / {pieces.length} approved</span>
            <span className="text-xs text-slate-500">{Math.round((approvedCount / pieces.length) * 100)}%</span>
          </div>
          <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-green-600 rounded-full transition-all duration-500"
              style={{ width: `${pieces.length > 0 ? (approvedCount / pieces.length) * 100 : 0}%` }}
            />
          </div>
        </div>
      )}

      {bulkError && (
        <div className="flex items-center gap-2 p-3 rounded bg-red-950/30 border border-red-900/40 text-red-400 text-sm">
          <AlertCircle size={14} />
          {bulkError}
        </div>
      )}

      {bulkSuccess && (
        <div className="flex items-center gap-2 p-3 rounded bg-green-900/20 border border-green-800/40 text-green-300 text-sm">
          <CheckCircle2 size={14} />
          All draft content approved successfully
        </div>
      )}

      {/* Filter tabs */}
      <div className="flex items-center gap-1">
        <Filter size={14} className="text-slate-500 mr-1" />
        {STATUS_FILTERS.map(f => {
          const count = f.key ? pieces.filter(p => p.status === f.key).length : pieces.length
          return (
            <button
              key={f.key}
              onClick={() => setStatusFilter(f.key)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                statusFilter === f.key
                  ? 'bg-slate-700 text-slate-100'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
              }`}
            >
              {f.label}
              <span className="text-slate-500">({count})</span>
            </button>
          )
        })}
      </div>

      {/* Content pieces */}
      {filtered.length === 0 ? (
        <div className="text-center py-16">
          <p className="text-slate-500 text-sm">
            {statusFilter ? `No content with status "${statusFilter}"` : 'No content pieces found'}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {filtered.map(piece => (
            <ContentEditor key={piece.id} piece={piece} projectId={id} />
          ))}
        </div>
      )}
    </div>
  )
}
