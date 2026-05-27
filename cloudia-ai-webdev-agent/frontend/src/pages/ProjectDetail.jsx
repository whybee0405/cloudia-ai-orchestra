import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft, ExternalLink, Globe, ShoppingBag, Loader2, AlertCircle,
  XCircle, RefreshCw, FileText, ChevronDown, ChevronRight
} from 'lucide-react'
import { fetchProject, cancelProject } from '../api/projects'
import { useProjectStatus } from '../hooks/useProjectStatus'
import { StatusBadge } from '../components/StatusBadge'
import { AgentTaskCard } from '../components/AgentTaskCard'
import { PipelineStatus } from '../components/PipelineStatus'
import { ApprovalCard } from '../components/ApprovalCard'

function formatDate(ts) {
  if (!ts) return '—'
  return new Date(ts).toLocaleString('en-ZA', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function calcTotalCost(tasks = []) {
  return tasks.reduce((sum, t) => sum + (t.cost_usd || 0), 0)
}

function calcTotalTokens(tasks = []) {
  return tasks.reduce((sum, t) => sum + (t.tokens_used || 0), 0)
}

function QAReport({ tasks }) {
  const qaTask = tasks?.find(t => t.agent_name?.toLowerCase().includes('qa'))
  const [expanded, setExpanded] = useState(false)

  if (!qaTask || qaTask.status !== 'completed') return null

  const report = qaTask.output_data || qaTask.result

  if (!report) return null

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg">
      <button
        onClick={() => setExpanded(v => !v)}
        className="w-full flex items-center justify-between px-5 py-4 text-left"
      >
        <div className="flex items-center gap-2">
          <FileText size={16} className="text-slate-400" />
          <span className="text-sm font-medium text-slate-200">QA Report</span>
        </div>
        {expanded ? <ChevronDown size={16} className="text-slate-400" /> : <ChevronRight size={16} className="text-slate-400" />}
      </button>
      {expanded && (
        <div className="px-5 pb-5 border-t border-slate-700">
          <pre className="mt-4 text-xs text-slate-300 overflow-x-auto whitespace-pre-wrap break-words font-mono bg-slate-900 rounded p-4">
            {typeof report === 'string' ? report : JSON.stringify(report, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}

export default function ProjectDetail() {
  const { id } = useParams()
  const queryClient = useQueryClient()
  const [cancelError, setCancelError] = useState(null)
  const [showCancelConfirm, setShowCancelConfirm] = useState(false)

  const { data: project, isLoading, error } = useQuery({
    queryKey: ['project', id],
    queryFn: () => fetchProject(id),
    refetchInterval: 10000,
  })

  useProjectStatus(id)

  const cancelMutation = useMutation({
    mutationFn: () => cancelProject(id),
    onSuccess: () => {
      setCancelError(null)
      setShowCancelConfirm(false)
      queryClient.invalidateQueries({ queryKey: ['project', id] })
      queryClient.invalidateQueries({ queryKey: ['projects'] })
    },
    onError: (err) => {
      setCancelError(err.message)
      setShowCancelConfirm(false)
    },
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 size={24} className="animate-spin text-slate-500" />
        <span className="ml-3 text-slate-400 text-sm">Loading project...</span>
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

  if (!project) return null

  const tasks = project.tasks || []
  const gates = project.gates || []
  const sortedTasks = [...tasks].sort((a, b) => a.pipeline_order - b.pipeline_order)
  const pendingGates = gates.filter(g => g.status === 'pending')
  const totalCost = calcTotalCost(tasks)
  const totalTokens = calcTotalTokens(tasks)
  const canCancel = ['planned', 'running', 'awaiting_content_review', 'awaiting_site_review', 'needs_input'].includes(project.status)
  const hasFailed = tasks.some(t => t.status === 'failed')
  const clientName = project.client_name || project.brief?.business_name || `Client ${project.client_id}`
  const hasContent = ['awaiting_content_review', 'awaiting_site_review', 'completed'].includes(project.status)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3">
          <Link
            to="/"
            className="flex items-center gap-1.5 text-slate-400 hover:text-slate-200 text-sm transition-colors"
          >
            <ArrowLeft size={16} />
          </Link>
          <div>
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-xl font-semibold text-slate-100">{clientName}</h1>
              <span className="text-sm text-slate-500 font-mono">#{project.id}</span>
              {project.platform && (
                <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded bg-slate-700 text-slate-300">
                  {project.platform === 'wordpress' ? <Globe size={11} /> : <ShoppingBag size={11} />}
                  {project.platform === 'wordpress' ? 'WordPress' : 'Shopify'}
                </span>
              )}
              <StatusBadge status={project.status} />
            </div>
            <div className="flex items-center gap-4 mt-1 flex-wrap">
              <span className="text-xs text-slate-500">Created {formatDate(project.created_at)}</span>
              {project.completed_at && (
                <span className="text-xs text-slate-500">Completed {formatDate(project.completed_at)}</span>
              )}
              {totalCost > 0 && (
                <span className="text-xs text-slate-500">${totalCost.toFixed(4)} total cost</span>
              )}
              {totalTokens > 0 && (
                <span className="text-xs text-slate-500">{totalTokens.toLocaleString()} tokens</span>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {hasContent && (
            <Link
              to={`/projects/${id}/content`}
              className="flex items-center gap-1.5 px-3 py-2 rounded text-sm font-medium bg-slate-700 hover:bg-slate-600 text-slate-200 transition-colors"
            >
              <FileText size={14} />
              Content Review
            </Link>
          )}
          {project.site_url && (
            <a
              href={project.site_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 px-3 py-2 rounded text-sm font-medium bg-slate-700 hover:bg-slate-600 text-slate-200 transition-colors"
            >
              <ExternalLink size={14} />
              View Site
            </a>
          )}
          {canCancel && (
            <div>
              {showCancelConfirm ? (
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-400">Confirm cancel?</span>
                  <button
                    onClick={() => cancelMutation.mutate()}
                    disabled={cancelMutation.isPending}
                    className="px-3 py-2 rounded text-sm font-medium bg-red-900/50 hover:bg-red-800 text-red-300 transition-colors disabled:opacity-50"
                  >
                    {cancelMutation.isPending ? 'Cancelling...' : 'Yes, Cancel'}
                  </button>
                  <button
                    onClick={() => setShowCancelConfirm(false)}
                    className="px-3 py-2 rounded text-sm font-medium bg-slate-700 hover:bg-slate-600 text-slate-300 transition-colors"
                  >
                    No
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setShowCancelConfirm(true)}
                  className="flex items-center gap-1.5 px-3 py-2 rounded text-sm font-medium bg-red-900/30 hover:bg-red-900/50 text-red-400 transition-colors"
                >
                  <XCircle size={14} />
                  Cancel Project
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {cancelError && (
        <div className="flex items-center gap-2 p-3 rounded bg-red-950/30 border border-red-900/40 text-red-400 text-sm">
          <AlertCircle size={14} />
          {cancelError}
        </div>
      )}

      {project.operator_notes && (
        <div className="p-4 rounded-lg bg-amber-950/20 border border-amber-800/40 text-sm text-amber-300">
          <p className="font-medium mb-1 text-xs uppercase tracking-wider text-amber-500">Operator Notes</p>
          {project.operator_notes}
        </div>
      )}

      {/* Pipeline stepper */}
      <PipelineStatus tasks={tasks} gates={gates} />

      {/* Pending approvals callout */}
      {pendingGates.length > 0 && (
        <div className="p-4 rounded-lg bg-amber-950/20 border border-amber-800/40">
          <p className="text-sm font-medium text-amber-300 mb-1">
            {pendingGates.length} approval gate{pendingGates.length > 1 ? 's' : ''} awaiting review
          </p>
          <p className="text-xs text-amber-500">Review required to continue the pipeline</p>
        </div>
      )}

      {/* Two-column layout: tasks + gates */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
        {/* Tasks */}
        <div className="lg:col-span-3 space-y-3">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400">Agent Tasks</h2>
          {sortedTasks.length === 0 ? (
            <p className="text-sm text-slate-500">No tasks yet — pipeline not started</p>
          ) : (
            sortedTasks.map(task => (
              <AgentTaskCard key={task.id} task={task} projectId={id} />
            ))
          )}
        </div>

        {/* Gates */}
        <div className="lg:col-span-2 space-y-3">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400">Approval Gates</h2>
          {gates.length === 0 ? (
            <p className="text-sm text-slate-500">No approval gates</p>
          ) : (
            [...gates]
              .sort((a, b) => a.pipeline_order - b.pipeline_order)
              .map(gate => (
                <ApprovalCard key={gate.id} gate={gate} projectId={id} />
              ))
          )}
        </div>
      </div>

      {/* QA Report */}
      <QAReport tasks={tasks} />

      {/* Action bar for failed tasks */}
      {hasFailed && (
        <div className="flex items-center gap-3 p-4 rounded-lg bg-red-950/20 border border-red-800/40">
          <AlertCircle size={16} className="text-red-400 flex-shrink-0" />
          <div>
            <p className="text-sm font-medium text-red-300">Some tasks have failed</p>
            <p className="text-xs text-red-500 mt-0.5">Use the Retry button on each failed task to re-attempt</p>
          </div>
        </div>
      )}
    </div>
  )
}
