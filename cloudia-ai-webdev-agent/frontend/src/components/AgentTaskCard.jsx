import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ChevronDown, ChevronRight, RefreshCw, Clock, DollarSign, Cpu } from 'lucide-react'
import { StatusBadge } from './StatusBadge'
import { retryTask } from '../api/projects'

function formatAgentName(name) {
  if (!name) return 'Unknown Agent'
  return name
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase())
}

function formatDuration(startedAt, completedAt) {
  if (!startedAt) return null
  const start = new Date(startedAt)
  const end = completedAt ? new Date(completedAt) : new Date()
  const seconds = Math.floor((end - start) / 1000)
  if (seconds < 60) return `${seconds}s`
  const minutes = Math.floor(seconds / 60)
  const rem = seconds % 60
  if (minutes < 60) return `${minutes}m ${rem}s`
  const hours = Math.floor(minutes / 60)
  const remMin = minutes % 60
  return `${hours}h ${remMin}m`
}

function formatTimestamp(ts) {
  if (!ts) return null
  return new Date(ts).toLocaleString('en-ZA', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function AgentTaskCard({ task, projectId }) {
  const [errorExpanded, setErrorExpanded] = useState(false)
  const [retryError, setRetryError] = useState(null)
  const queryClient = useQueryClient()

  const retryMutation = useMutation({
    mutationFn: () => retryTask(projectId, task.id),
    onSuccess: () => {
      setRetryError(null)
      queryClient.invalidateQueries({ queryKey: ['project', String(projectId)] })
      queryClient.invalidateQueries({ queryKey: ['project', Number(projectId)] })
    },
    onError: (err) => {
      setRetryError(err.message)
    },
  })

  const duration = formatDuration(task.started_at, task.completed_at)
  const isFailed = task.status === 'failed'
  const isRunning = task.status === 'running'

  return (
    <div
      id={`task-${task.id}`}
      className={`rounded-lg border p-4 transition-colors ${
        isFailed
          ? 'border-red-800/50 bg-red-950/20'
          : isRunning
          ? 'border-blue-800/50 bg-blue-950/20'
          : 'border-slate-700 bg-slate-800'
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 min-w-0">
          <div className="flex-shrink-0 w-7 h-7 rounded-full bg-slate-700 flex items-center justify-center text-xs font-mono text-slate-400 mt-0.5">
            {task.pipeline_order}
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="text-sm font-medium text-slate-100">{formatAgentName(task.agent_name)}</h3>
              <StatusBadge status={task.status} size="xs" />
              {task.retry_count > 0 && (
                <span className="text-xs text-slate-500">({task.retry_count} {task.retry_count === 1 ? 'retry' : 'retries'})</span>
              )}
            </div>

            <div className="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1">
              {task.started_at && (
                <span className="flex items-center gap-1 text-xs text-slate-500">
                  <Clock size={11} />
                  Started {formatTimestamp(task.started_at)}
                </span>
              )}
              {task.completed_at && (
                <span className="flex items-center gap-1 text-xs text-slate-500">
                  Finished {formatTimestamp(task.completed_at)}
                </span>
              )}
              {duration && (
                <span className="text-xs text-slate-500">
                  Duration: {duration}
                </span>
              )}
            </div>

            <div className="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1">
              {task.cost_usd !== null && task.cost_usd !== undefined && (
                <span className="flex items-center gap-1 text-xs text-slate-400">
                  <DollarSign size={11} />
                  ${Number(task.cost_usd).toFixed(4)}
                </span>
              )}
              {task.tokens_used !== null && task.tokens_used !== undefined && (
                <span className="flex items-center gap-1 text-xs text-slate-400">
                  <Cpu size={11} />
                  {task.tokens_used.toLocaleString()} tokens
                </span>
              )}
            </div>
          </div>
        </div>

        {isFailed && projectId && (
          <button
            onClick={() => retryMutation.mutate()}
            disabled={retryMutation.isPending}
            className="flex-shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium bg-slate-700 hover:bg-slate-600 text-slate-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <RefreshCw size={12} className={retryMutation.isPending ? 'animate-spin' : ''} />
            {retryMutation.isPending ? 'Retrying...' : 'Retry'}
          </button>
        )}
      </div>

      {retryError && (
        <p className="mt-2 text-xs text-red-400 bg-red-950/30 rounded px-2 py-1">{retryError}</p>
      )}

      {isFailed && task.error && (
        <div className="mt-3">
          <button
            onClick={() => setErrorExpanded(v => !v)}
            className="flex items-center gap-1 text-xs text-red-400 hover:text-red-300 transition-colors"
          >
            {errorExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
            {errorExpanded ? 'Hide' : 'Show'} error details
          </button>
          {errorExpanded && (
            <pre className="mt-2 p-3 rounded bg-slate-900 text-xs text-red-300 overflow-x-auto whitespace-pre-wrap break-words font-mono border border-red-900/30">
              {task.error}
            </pre>
          )}
        </div>
      )}
    </div>
  )
}
