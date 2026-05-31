import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Plus, Globe, ShoppingBag, ArrowLeft } from 'lucide-react'
import { listProjects, type Project } from '@/api/webdev'
import { Card, CardBody } from '@/shared/components/Card'
import { Button } from '@/shared/components/Button'
import { Badge } from '@/shared/components/Badge'
import { PageLoader } from '@/shared/components/LoadingSpinner'

const STATUS_BADGE: Record<string, 'default' | 'success' | 'warning' | 'danger' | 'info'> = {
  planned: 'default',
  running: 'info',
  awaiting_approval: 'warning',
  completed: 'success',
  failed: 'danger',
  cancelled: 'default',
}

const PLATFORM_ICON = {
  wordpress: Globe,
  shopify: ShoppingBag,
}

function ProjectCard({ project }: { project: Project }) {
  const { clientId } = useParams<{ clientId: string }>()
  const navigate = useNavigate()
  const PlatformIcon = PLATFORM_ICON[project.platform as keyof typeof PLATFORM_ICON] ?? Globe

  const pendingGates = project.gates.filter(g => g.status === 'pending').length
  const failedTasks = project.tasks.filter(t => t.status === 'failed').length

  return (
    <Card
      className="cursor-pointer hover:border-slate-300 transition-colors"
      onClick={() => navigate(`/clients/${clientId}/webdev/${project.id}`)}
    >
      <CardBody className="space-y-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center shrink-0">
              <PlatformIcon className="w-4 h-4 text-slate-500" />
            </div>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-slate-800 truncate">
                {(project.brief?.project_name as string) ?? `Project #${project.id}`}
              </p>
              <p className="text-xs text-slate-400 capitalize">{project.platform ?? 'unknown platform'}</p>
            </div>
          </div>
          <Badge variant={STATUS_BADGE[project.status] ?? 'default'} className="shrink-0 capitalize">
            {project.status.replace(/_/g, ' ')}
          </Badge>
        </div>

        {(pendingGates > 0 || failedTasks > 0) && (
          <div className="flex items-center gap-2">
            {pendingGates > 0 && (
              <span className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full font-medium">
                {pendingGates} gate{pendingGates > 1 ? 's' : ''} pending
              </span>
            )}
            {failedTasks > 0 && (
              <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full font-medium">
                {failedTasks} task{failedTasks > 1 ? 's' : ''} failed
              </span>
            )}
          </div>
        )}

        <div className="flex items-center justify-between text-xs text-slate-400">
          <span>{project.tasks.length} agent task{project.tasks.length !== 1 ? 's' : ''}</span>
          <span>{new Date(project.created_at).toLocaleDateString('en-ZA', { day: 'numeric', month: 'short', year: 'numeric' })}</span>
        </div>
      </CardBody>
    </Card>
  )
}

export function ProjectList({ webdevClientId }: { webdevClientId: number }) {
  const { clientId } = useParams<{ clientId: string }>()
  const navigate = useNavigate()

  const { data: projects, isLoading } = useQuery({
    queryKey: ['webdev-projects', webdevClientId],
    queryFn: () => listProjects(webdevClientId),
    refetchInterval: 30_000,
  })

  if (isLoading) return <PageLoader />

  return (
    <div className="p-8">
      <button
        onClick={() => navigate(`/clients/${clientId}`)}
        className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 mb-6"
      >
        <ArrowLeft className="w-4 h-4" /> Back to Hub
      </button>

      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-purple-100 flex items-center justify-center">
            <Globe className="w-5 h-5 text-purple-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Website Projects</h1>
            <p className="text-sm text-slate-500">{projects?.length ?? 0} project{projects?.length !== 1 ? 's' : ''}</p>
          </div>
        </div>
        <Button onClick={() => navigate(`/clients/${clientId}/webdev/new`)}>
          <Plus className="w-4 h-4" /> New Project
        </Button>
      </div>

      {projects?.length === 0 && (
        <Card>
          <CardBody className="py-16 text-center">
            <Globe className="w-10 h-10 text-slate-200 mx-auto mb-3" />
            <p className="text-sm text-slate-400">No projects yet — create one to get started.</p>
          </CardBody>
        </Card>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
        {projects?.map(p => <ProjectCard key={p.id} project={p} />)}
      </div>
    </div>
  )
}
