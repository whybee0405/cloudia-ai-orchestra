import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft, LayoutDashboard, FileText, CheckSquare,
  RotateCcw, CheckCircle, XCircle, MessageSquare, Globe, ShoppingBag,
} from 'lucide-react'
import {
  getProject,
  approveGate,
  rejectGate,
  requestRevision,
  retryTask,
  type ApprovalGate,
  type AgentTask,
  type Project,
} from '@/api/webdev'
import { Card, CardBody, CardHeader } from '@/shared/components/Card'
import { Button } from '@/shared/components/Button'
import { Badge } from '@/shared/components/Badge'
import { PageLoader } from '@/shared/components/LoadingSpinner'
import { ContentReview } from './ContentReview'

type Tab = 'pipeline' | 'content' | 'gates'

const TABS: { key: Tab; label: string; icon: typeof LayoutDashboard }[] = [
  { key: 'pipeline', label: 'Pipeline', icon: LayoutDashboard },
  { key: 'content', label: 'Content', icon: FileText },
  { key: 'gates', label: 'Approval Gates', icon: CheckSquare },
]

const TASK_STATUS_BADGE: Record<string, 'default' | 'success' | 'warning' | 'danger' | 'info'> = {
  pending: 'default',
  running: 'info',
  completed: 'success',
  failed: 'danger',
  skipped: 'default',
}

const GATE_STATUS_BADGE: Record<string, 'default' | 'success' | 'warning' | 'danger' | 'info'> = {
  pending: 'warning',
  approved: 'success',
  rejected: 'danger',
  revision_requested: 'info',
}

// ── Pipeline tab ───────────────────────────────────────────────────────────

function TaskRow({ task, project }: { task: AgentTask; project: Project }) {
  const qc = useQueryClient()
  const { mutate: retry, isPending: retrying } = useMutation({
    mutationFn: () => retryTask(project.id, task.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['webdev-project', project.id] }),
  })

  return (
    <div className="py-3 border-b border-slate-100 last:border-0">
      <div className="flex items-center gap-3">
        <span className="text-xs text-slate-400 w-5 text-right shrink-0">{task.pipeline_order}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <Badge variant={TASK_STATUS_BADGE[task.status] ?? 'default'} className="capitalize">
              {task.status}
            </Badge>
            <span className="text-sm font-medium text-slate-700">{task.agent_name}</span>
          </div>
          {task.error && (
            <p className="text-xs text-red-500 mt-1 truncate">{task.error}</p>
          )}
          {task.cost_usd != null && (
            <p className="text-xs text-slate-400 mt-0.5">${task.cost_usd.toFixed(4)}</p>
          )}
        </div>
        {task.status === 'failed' && (
          <Button size="sm" variant="secondary" onClick={() => retry()} loading={retrying}>
            <RotateCcw className="w-3.5 h-3.5" /> Retry
          </Button>
        )}
      </div>
    </div>
  )
}

function PipelineTab({ project }: { project: Project }) {
  const tasks = [...(project.tasks ?? [])].sort((a, b) => a.pipeline_order - b.pipeline_order)
  return (
    <div className="space-y-4">
      {project.pipeline_plan && (
        <Card>
          <CardHeader><h2 className="text-sm font-semibold text-slate-700">Pipeline Plan</h2></CardHeader>
          <CardBody>
            <pre className="text-xs text-slate-600 bg-slate-50 rounded-lg p-3 overflow-x-auto">
              {JSON.stringify(project.pipeline_plan, null, 2)}
            </pre>
          </CardBody>
        </Card>
      )}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-700">Agent Tasks</h2>
            <span className="text-xs text-slate-400">{tasks.length} task{tasks.length !== 1 ? 's' : ''}</span>
          </div>
        </CardHeader>
        <CardBody className="py-0">
          {tasks.length === 0 && (
            <div className="py-8 text-center text-sm text-slate-400">No tasks yet.</div>
          )}
          {tasks.map(t => <TaskRow key={t.id} task={t} project={project} />)}
        </CardBody>
      </Card>
    </div>
  )
}

// ── Gates tab ──────────────────────────────────────────────────────────────

function GateCard({ gate, projectId }: { gate: ApprovalGate; projectId: number }) {
  const qc = useQueryClient()
  const [reviewer, setReviewer] = useState('operator')
  const [notes, setNotes] = useState('')
  const [showRevision, setShowRevision] = useState(false)

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['webdev-gates', projectId] })
    qc.invalidateQueries({ queryKey: ['webdev-project', projectId] })
  }

  const { mutate: approve, isPending: approving } = useMutation({
    mutationFn: () => approveGate(gate.id, reviewer, notes || undefined),
    onSuccess: invalidate,
  })
  const { mutate: reject, isPending: rejecting } = useMutation({
    mutationFn: () => rejectGate(gate.id, notes || 'Rejected', reviewer),
    onSuccess: invalidate,
  })
  const { mutate: revise, isPending: revising } = useMutation({
    mutationFn: () => requestRevision(gate.id, notes || 'Revision requested', reviewer),
    onSuccess: invalidate,
  })

  const isPending = gate.status === 'pending'

  return (
    <Card className={isPending ? 'border-amber-200 bg-amber-50/30' : ''}>
      <CardBody className="space-y-3">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Badge variant={GATE_STATUS_BADGE[gate.status] ?? 'default'} className="capitalize">
                {gate.status.replace(/_/g, ' ')}
              </Badge>
              <span className="text-xs text-slate-400">Order {gate.pipeline_order}</span>
            </div>
            <p className="text-sm font-semibold text-slate-800">{gate.gate_name}</p>
          </div>
          <span className="text-xs text-slate-400 shrink-0">
            {new Date(gate.created_at).toLocaleDateString('en-ZA', {
              day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
            })}
          </span>
        </div>

        {gate.notes && <p className="text-xs text-slate-500 italic">{gate.notes}</p>}

        {gate.reviewed_by && (
          <p className="text-xs text-slate-400">
            Reviewed by <strong>{gate.reviewed_by}</strong>
            {gate.reviewed_at && ` · ${new Date(gate.reviewed_at).toLocaleDateString('en-ZA')}`}
          </p>
        )}

        {isPending && (
          <div className="space-y-2 pt-1">
            <div className="flex items-center gap-2">
              <input
                className="flex-1 text-xs border border-slate-200 rounded-md px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-brand-500"
                placeholder="Reviewer name / email"
                value={reviewer}
                onChange={e => setReviewer(e.target.value)}
              />
            </div>
            {(notes || showRevision) && (
              <textarea
                rows={2}
                className="w-full text-xs border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-1 focus:ring-brand-500 resize-none"
                placeholder="Notes (required for reject / revision)"
                value={notes}
                onChange={e => setNotes(e.target.value)}
              />
            )}
            <div className="flex items-center gap-2 flex-wrap">
              <Button size="sm" onClick={() => approve()} loading={approving} disabled={!reviewer.trim()}>
                <CheckCircle className="w-3.5 h-3.5" /> Approve
              </Button>
              <Button
                size="sm"
                variant="secondary"
                onClick={() => { setShowRevision(true) }}
                disabled={approving || rejecting || revising}
              >
                <MessageSquare className="w-3.5 h-3.5" /> Request Revision
              </Button>
              {showRevision && (
                <Button size="sm" onClick={() => revise()} loading={revising} disabled={!notes.trim()}>
                  Submit Revision
                </Button>
              )}
              <Button size="sm" variant="danger" onClick={() => reject()} loading={rejecting} disabled={!reviewer.trim()}>
                <XCircle className="w-3.5 h-3.5" /> Reject
              </Button>
            </div>
          </div>
        )}
      </CardBody>
    </Card>
  )
}

function GatesTab({ gates, projectId }: { gates: ApprovalGate[]; projectId: number }) {
  const sorted = [...gates].sort((a, b) => a.pipeline_order - b.pipeline_order)

  return (
    <div className="space-y-4">
      {sorted.length === 0 && (
        <Card>
          <CardBody className="py-12 text-center">
            <p className="text-sm text-slate-400">No approval gates yet.</p>
          </CardBody>
        </Card>
      )}
      {sorted.map(g => <GateCard key={g.id} gate={g} projectId={projectId} />)}
    </div>
  )
}

// ── Root ───────────────────────────────────────────────────────────────────

const PLATFORM_ICON = {
  wordpress: Globe,
  shopify: ShoppingBag,
}

export function ProjectDetail() {
  const { clientId, projectId } = useParams<{ clientId: string; projectId: string }>()
  const navigate = useNavigate()
  const [tab, setTab] = useState<Tab>('pipeline')

  const { data: project, isLoading } = useQuery({
    queryKey: ['webdev-project', Number(projectId)],
    queryFn: () => getProject(Number(projectId)),
    refetchInterval: 15_000,
  })

  if (isLoading || !project) return <PageLoader />

  const PlatformIcon = PLATFORM_ICON[project.platform as keyof typeof PLATFORM_ICON] ?? Globe
  const pendingGates = project.gates.filter(g => g.status === 'pending').length

  return (
    <div className="p-4 md:p-8">
      <button
        onClick={() => navigate(`/clients/${clientId}/webdev`)}
        className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 mb-6"
      >
        <ArrowLeft className="w-4 h-4" /> Back to Projects
      </button>

      <div className="flex flex-wrap items-start justify-between gap-3 mb-6">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-10 h-10 rounded-xl bg-purple-100 flex items-center justify-center flex-shrink-0">
            <PlatformIcon className="w-5 h-5 text-purple-600" />
          </div>
          <div className="min-w-0">
            <h1 className="text-xl md:text-2xl font-bold text-slate-900 truncate">
              {(project.brief?.project_name as string) ?? `Project #${project.id}`}
            </h1>
            <p className="text-sm text-slate-500 capitalize">
              {project.platform} · {project.status.replace(/_/g, ' ')}
              {project.site_url && ` · ${project.site_url}`}
            </p>
          </div>
        </div>
      </div>

      {pendingGates > 0 && (
        <div
          className="mb-6 bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 text-sm text-amber-800 flex items-center justify-between cursor-pointer"
          onClick={() => setTab('gates')}
        >
          <span><strong>{pendingGates} approval gate{pendingGates > 1 ? 's' : ''}</strong> waiting for review.</span>
          <span className="text-xs font-medium underline">Review now →</span>
        </div>
      )}

      <div className="flex items-center gap-1 border-b border-slate-200 mb-6 overflow-x-auto">
        {TABS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
              tab === key
                ? 'border-purple-600 text-purple-700'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            <Icon className="w-3.5 h-3.5" />
            {label}
            {key === 'gates' && pendingGates > 0 && (
              <span className="ml-1 bg-amber-100 text-amber-700 text-xs font-medium px-1.5 py-0.5 rounded-full">
                {pendingGates}
              </span>
            )}
          </button>
        ))}
      </div>

      {tab === 'pipeline' && <PipelineTab project={project} />}
      {tab === 'content' && <ContentReview projectId={project.id} />}
      {tab === 'gates' && <GatesTab gates={project.gates} projectId={project.id} />}
    </div>
  )
}
