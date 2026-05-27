import { CheckCircle2, Circle, XCircle, Loader2, MinusCircle, Shield } from 'lucide-react'

function formatLabel(name) {
  if (!name) return ''
  return name
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase())
}

function StepIcon({ status, size = 18 }) {
  if (status === 'completed') return <CheckCircle2 size={size} className="text-green-400" />
  if (status === 'failed') return <XCircle size={size} className="text-red-400" />
  if (status === 'running') return <Loader2 size={size} className="text-blue-400 animate-spin" />
  if (status === 'skipped') return <MinusCircle size={size} className="text-slate-500" />
  if (status === 'blocked') return <XCircle size={size} className="text-red-600" />
  return <Circle size={size} className="text-slate-600" />
}

function GateMarker({ gate }) {
  const colors = {
    approved: 'text-green-400 border-green-700',
    rejected: 'text-red-400 border-red-700',
    revision_requested: 'text-orange-400 border-orange-700',
    pending: 'text-yellow-400 border-yellow-800',
  }
  const colorClass = colors[gate.status] || 'text-slate-400 border-slate-600'

  return (
    <div className="flex flex-col items-center mx-1">
      <div className={`rounded border px-1.5 py-0.5 flex items-center gap-1 bg-slate-900 ${colorClass}`}>
        <Shield size={10} />
        <span className="text-xs font-medium whitespace-nowrap">{formatLabel(gate.gate_name)}</span>
      </div>
    </div>
  )
}

function ConnectorLine({ status }) {
  const colorMap = {
    completed: 'bg-green-500',
    running: 'bg-blue-500 pipeline-pulse',
    failed: 'bg-red-500',
    skipped: 'bg-slate-600',
    blocked: 'bg-red-800',
    pending: 'bg-slate-700',
  }
  const color = colorMap[status] || 'bg-slate-700'
  return <div className={`h-0.5 flex-1 min-w-4 ${color} transition-colors`} />
}

export function PipelineStatus({ tasks = [], gates = [] }) {
  if (!tasks.length) return null

  const sorted = [...tasks].sort((a, b) => a.pipeline_order - b.pipeline_order)

  // Build interleaved list of tasks and gates
  const items = []
  for (let i = 0; i < sorted.length; i++) {
    const task = sorted[i]
    items.push({ type: 'task', data: task })

    // Find gates that sit between this task and the next
    const nextOrder = sorted[i + 1]?.pipeline_order ?? Infinity
    const gatesHere = gates.filter(
      g => g.pipeline_order > task.pipeline_order && g.pipeline_order <= nextOrder
    )
    gatesHere.forEach(g => items.push({ type: 'gate', data: g }))
  }

  const scrollToTask = (taskId) => {
    const el = document.getElementById(`task-${taskId}`)
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' })
      el.classList.add('ring-2', 'ring-blue-500')
      setTimeout(() => el.classList.remove('ring-2', 'ring-blue-500'), 2000)
    }
  }

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg p-4">
      <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-4">Pipeline</h2>
      <div className="overflow-x-auto">
        <div className="flex items-center min-w-max pb-2">
          {items.map((item, idx) => (
            <div key={`${item.type}-${item.data.id}`} className="flex items-center">
              {idx > 0 && item.type === 'task' && (
                <ConnectorLine status={items[idx - 1]?.data?.status || 'pending'} />
              )}
              {idx > 0 && item.type === 'gate' && (
                <ConnectorLine status={items[idx - 1]?.data?.status || 'pending'} />
              )}

              {item.type === 'task' && (
                <button
                  onClick={() => scrollToTask(item.data.id)}
                  className="flex flex-col items-center group"
                  title={`Go to ${formatLabel(item.data.agent_name)}`}
                >
                  <div className="relative flex items-center justify-center w-8 h-8 rounded-full bg-slate-900 border-2 border-slate-700 group-hover:border-slate-500 transition-colors">
                    <StepIcon status={item.data.status} size={14} />
                    <span className="absolute -top-1 -right-1 text-xs bg-slate-700 rounded-full w-4 h-4 flex items-center justify-center text-slate-300 font-mono leading-none">
                      {item.data.pipeline_order}
                    </span>
                  </div>
                  <span className="mt-1.5 text-xs text-slate-400 group-hover:text-slate-200 transition-colors max-w-16 text-center leading-tight">
                    {formatLabel(item.data.agent_name).split(' ')[0]}
                  </span>
                </button>
              )}

              {item.type === 'gate' && (
                <>
                  <ConnectorLine status="pending" />
                  <GateMarker gate={item.data} />
                </>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
