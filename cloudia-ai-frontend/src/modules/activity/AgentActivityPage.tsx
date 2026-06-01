import { useEffect, useState } from 'react'
import { Dna, Megaphone, BarChart2, Globe, CheckCircle2, XCircle, Loader2, Radio } from 'lucide-react'
import { useAgentActivity, type AgentJob, type AgentType } from '@/shared/context/AgentActivityContext'

// ── Agent config ──────────────────────────────────────────────────────────────

const AGENTS: {
  type: AgentType
  label: string
  description: string
  icon: React.ElementType
  iconBg: string
  iconText: string
  activeBorder: string
  activeRing: string
  pulseBg: string
  tagBg: string
  tagText: string
  dotColor: string
}[] = [
  {
    type: 'brand-dna',
    label: 'Brand DNA',
    description: 'Identity & persona generation',
    icon: Dna,
    iconBg: 'bg-violet-100',
    iconText: 'text-violet-600',
    activeBorder: 'border-violet-300',
    activeRing: 'ring-2 ring-violet-400/30',
    pulseBg: 'bg-violet-500',
    tagBg: 'bg-violet-50',
    tagText: 'text-violet-700',
    dotColor: 'bg-violet-500',
  },
  {
    type: 'campaign-director',
    label: 'Campaign Director',
    description: 'Multi-platform content pipeline',
    icon: Megaphone,
    iconBg: 'bg-purple-100',
    iconText: 'text-purple-600',
    activeBorder: 'border-purple-300',
    activeRing: 'ring-2 ring-purple-400/30',
    pulseBg: 'bg-purple-500',
    tagBg: 'bg-purple-50',
    tagText: 'text-purple-700',
    dotColor: 'bg-purple-500',
  },
  {
    type: 'google-ads',
    label: 'Google Ads',
    description: 'Ad optimisation & bidding',
    icon: BarChart2,
    iconBg: 'bg-blue-100',
    iconText: 'text-blue-600',
    activeBorder: 'border-blue-300',
    activeRing: 'ring-2 ring-blue-400/30',
    pulseBg: 'bg-blue-500',
    tagBg: 'bg-blue-50',
    tagText: 'text-blue-700',
    dotColor: 'bg-blue-500',
  },
  {
    type: 'webdev',
    label: 'WebDev',
    description: 'Website & content generation',
    icon: Globe,
    iconBg: 'bg-emerald-100',
    iconText: 'text-emerald-600',
    activeBorder: 'border-emerald-300',
    activeRing: 'ring-2 ring-emerald-400/30',
    pulseBg: 'bg-emerald-500',
    tagBg: 'bg-emerald-50',
    tagText: 'text-emerald-700',
    dotColor: 'bg-emerald-500',
  },
]

const AGENT_MAP = Object.fromEntries(AGENTS.map(a => [a.type, a])) as Record<AgentType, typeof AGENTS[number]>

// ── Helpers ───────────────────────────────────────────────────────────────────

function useNow(active: boolean) {
  const [now, setNow] = useState(Date.now())
  useEffect(() => {
    if (!active) return
    const t = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(t)
  }, [active])
  return now
}

function elapsed(ms: number): string {
  const s = Math.floor(ms / 1000)
  if (s < 60) return `${s}s`
  const m = Math.floor(s / 60)
  if (m < 60) return `${m}m`
  return `${Math.floor(m / 60)}h ${m % 60}m`
}

function timeLabel(job: AgentJob, now: number): string {
  if (job.status === 'running') return elapsed(now - job.startedAt)
  if (job.completedAt) return elapsed(job.completedAt - job.startedAt) + ' · done'
  return ''
}

// ── Agent Node Card ───────────────────────────────────────────────────────────

function AgentNodeCard({ cfg, jobs, now }: {
  cfg: typeof AGENTS[number]
  jobs: AgentJob[]
  now: number
}) {
  const running = jobs.filter(j => j.status === 'running')
  const isActive = running.length > 0
  const lastDone = jobs.find(j => j.status === 'completed' || j.status === 'error')
  const Icon = cfg.icon

  return (
    <div
      className={[
        'relative bg-white rounded-2xl border p-5 transition-all duration-300',
        isActive
          ? `${cfg.activeBorder} ${cfg.activeRing} shadow-lg`
          : 'border-slate-200 shadow-sm',
      ].join(' ')}
    >
      {/* Live pulse dot */}
      {isActive && (
        <span className="absolute top-3.5 right-3.5 flex h-2.5 w-2.5">
          <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${cfg.pulseBg}`} />
          <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${cfg.pulseBg}`} />
        </span>
      )}

      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <div className={`w-11 h-11 rounded-xl ${cfg.iconBg} flex items-center justify-center flex-shrink-0 ${isActive ? 'shadow-sm' : ''}`}>
          <Icon className={`w-5 h-5 ${cfg.iconText}`} />
        </div>
        <div className="min-w-0">
          <p className="text-sm font-semibold text-slate-800">{cfg.label}</p>
          <p className="text-xs text-slate-400">{cfg.description}</p>
        </div>
      </div>

      {/* Status body */}
      {isActive ? (
        <div className="space-y-2">
          <div className="flex items-center gap-1.5 mb-2">
            <Loader2 className={`w-3.5 h-3.5 animate-spin ${cfg.iconText}`} />
            <span className={`text-xs font-semibold ${cfg.iconText}`}>
              {running.length} job{running.length !== 1 ? 's' : ''} running
            </span>
          </div>
          <div className="space-y-1.5">
            {running.slice(0, 3).map(job => (
              <div key={job.id} className={`flex items-start justify-between gap-2 rounded-lg px-2.5 py-1.5 ${cfg.tagBg}`}>
                <div className="min-w-0">
                  <p className={`text-xs font-medium truncate ${cfg.tagText}`}>{job.task}</p>
                  <p className="text-xs text-slate-400 truncate">{job.clientName}</p>
                </div>
                <span className="text-xs text-slate-400 flex-shrink-0 font-mono">
                  {elapsed(now - job.startedAt)}
                </span>
              </div>
            ))}
            {running.length > 3 && (
              <p className="text-xs text-slate-400 pl-2">+{running.length - 3} more</p>
            )}
          </div>
        </div>
      ) : (
        <div className="flex items-center justify-between">
          <span className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-400 bg-slate-50 border border-slate-200 px-2.5 py-1 rounded-full">
            <span className="w-1.5 h-1.5 rounded-full bg-slate-300" />
            Idle
          </span>
          {lastDone && (
            <p className="text-xs text-slate-400 truncate max-w-[140px]" title={lastDone.task}>
              Last: {lastDone.task}
            </p>
          )}
        </div>
      )}
    </div>
  )
}

// ── Activity Feed Item ────────────────────────────────────────────────────────

function FeedItem({ job, now }: { job: AgentJob; now: number }) {
  const cfg = AGENT_MAP[job.agentType]

  return (
    <div className="flex items-start gap-3 py-3 border-b border-slate-100 last:border-0">
      {/* Status icon */}
      <div className="flex-shrink-0 mt-0.5">
        {job.status === 'running' ? (
          <Loader2 className={`w-3.5 h-3.5 animate-spin ${cfg.iconText}`} />
        ) : job.status === 'completed' ? (
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
        ) : (
          <XCircle className="w-3.5 h-3.5 text-red-500" />
        )}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5 mb-0.5">
          <span className={`inline-block w-1.5 h-1.5 rounded-full flex-shrink-0 ${cfg.dotColor}`} />
          <span className="text-xs font-semibold text-slate-700 truncate">{cfg.label}</span>
          <span className="text-xs text-slate-300">·</span>
          <span className="text-xs text-slate-500 truncate">{job.clientName}</span>
        </div>
        <p className="text-xs text-slate-600 truncate">{job.task}</p>
        {job.status === 'error' && job.error && (
          <p className="text-xs text-red-500 mt-0.5 truncate">{job.error}</p>
        )}
      </div>

      {/* Time */}
      <span className="text-xs text-slate-400 flex-shrink-0 font-mono">
        {timeLabel(job, now)}
      </span>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export function AgentActivityPage() {
  const { jobs } = useAgentActivity()
  const hasRunning = jobs.some(j => j.status === 'running')
  const now = useNow(hasRunning)

  const runningCount = jobs.filter(j => j.status === 'running').length
  const completedCount = jobs.filter(j => j.status === 'completed').length
  const errorCount = jobs.filter(j => j.status === 'error').length

  return (
    <div className="p-4 md:p-8">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-3 mb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-xl md:text-2xl font-bold text-slate-900">Agent Activity</h1>
            {hasRunning && (
              <span className="flex h-2 w-2 mt-1">
                <span className="animate-ping absolute inline-flex h-2 w-2 rounded-full bg-brand-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-brand-500" />
              </span>
            )}
          </div>
          <p className="text-sm text-slate-500">Real-time view of all AI agents across every client</p>
        </div>

        {/* Stats chips */}
        <div className="flex flex-wrap items-center gap-2">
          <span className={`inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-full border ${
            runningCount > 0
              ? 'bg-brand-50 text-brand-700 border-brand-200'
              : 'bg-slate-50 text-slate-500 border-slate-200'
          }`}>
            <Radio className="w-3 h-3" />
            {runningCount} Running
          </span>
          <span className="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-full border bg-emerald-50 text-emerald-700 border-emerald-200">
            <CheckCircle2 className="w-3 h-3" />
            {completedCount} Completed
          </span>
          {errorCount > 0 && (
            <span className="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-full border bg-red-50 text-red-700 border-red-200">
              <XCircle className="w-3 h-3" />
              {errorCount} Error{errorCount !== 1 ? 's' : ''}
            </span>
          )}
        </div>
      </div>

      {/* Main layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Agent node grid */}
        <div className="lg:col-span-2 grid grid-cols-1 sm:grid-cols-2 gap-4 content-start">
          {AGENTS.map(cfg => (
            <AgentNodeCard
              key={cfg.type}
              cfg={cfg}
              jobs={jobs.filter(j => j.agentType === cfg.type)}
              now={now}
            />
          ))}
        </div>

        {/* Activity feed */}
        <div className="lg:sticky lg:top-8 self-start">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100">
              <h2 className="text-sm font-semibold text-slate-700">Live Feed</h2>
              <span className="text-xs text-slate-400">{jobs.length} event{jobs.length !== 1 ? 's' : ''}</span>
            </div>

            {jobs.length === 0 ? (
              <div className="py-16 px-4 text-center">
                <div className="w-10 h-10 rounded-xl bg-slate-100 flex items-center justify-center mx-auto mb-3">
                  <Radio className="w-5 h-5 text-slate-400" />
                </div>
                <p className="text-sm font-medium text-slate-600 mb-1">No activity yet</p>
                <p className="text-xs text-slate-400">
                  Activity appears here when agents start working — try generating a Brand DNA or creating a campaign.
                </p>
              </div>
            ) : (
              <div className="max-h-[calc(100vh-280px)] overflow-y-auto px-4 divide-y divide-slate-100">
                {jobs.map(job => (
                  <FeedItem key={job.id} job={job} now={now} />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
