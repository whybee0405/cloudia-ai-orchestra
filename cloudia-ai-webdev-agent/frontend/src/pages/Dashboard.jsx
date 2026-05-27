import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Plus, Globe, ShoppingBag, Calendar, FileText, DollarSign, AlertCircle, Loader2 } from 'lucide-react'
import { fetchProjects } from '../api/projects'
import { fetchPendingApprovals } from '../api/approvals'
import { StatusBadge } from '../components/StatusBadge'

const STATUS_FILTERS = [
  { key: '', label: 'All' },
  { key: 'running', label: 'Running' },
  { key: 'awaiting_content_review', label: 'Awaiting Review' },
  { key: 'awaiting_site_review', label: 'Awaiting Site Review' },
  { key: 'completed', label: 'Completed' },
  { key: 'failed', label: 'Failed' },
]

function formatDate(ts) {
  if (!ts) return '—'
  return new Date(ts).toLocaleDateString('en-ZA', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
}

function calcProjectCost(tasks = []) {
  return tasks.reduce((sum, t) => sum + (t.cost_usd || 0), 0)
}

function PlatformBadge({ platform }) {
  if (!platform) return <span className="text-xs text-slate-500">—</span>
  return (
    <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded bg-slate-700 text-slate-300">
      {platform === 'wordpress' ? <Globe size={11} /> : <ShoppingBag size={11} />}
      {platform === 'wordpress' ? 'WordPress' : 'Shopify'}
    </span>
  )
}

function ProjectCard({ project }) {
  const cost = calcProjectCost(project.tasks || [])

  return (
    <Link
      to={`/projects/${project.id}`}
      className="block bg-slate-800 border border-slate-700 rounded-lg p-5 hover:border-slate-600 transition-colors group"
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className="text-xs text-slate-500 font-mono">#{project.id}</span>
            <PlatformBadge platform={project.platform} />
          </div>
          <h3 className="text-sm font-medium text-slate-100 group-hover:text-blue-300 transition-colors truncate">
            {project.client_name || project.brief?.business_name || `Client ${project.client_id}`}
          </h3>
        </div>
        <StatusBadge status={project.status} size="xs" />
      </div>

      <div className="space-y-1.5">
        <div className="flex items-center gap-1.5 text-xs text-slate-500">
          <Calendar size={11} />
          Created {formatDate(project.created_at)}
        </div>
        {project.estimated_pages && (
          <div className="flex items-center gap-1.5 text-xs text-slate-500">
            <FileText size={11} />
            {project.actual_pages ?? project.estimated_pages} pages
            {project.actual_pages && project.estimated_pages && project.actual_pages !== project.estimated_pages && (
              <span className="text-slate-600">(est. {project.estimated_pages})</span>
            )}
          </div>
        )}
        {cost > 0 && (
          <div className="flex items-center gap-1.5 text-xs text-slate-500">
            <DollarSign size={11} />
            ${cost.toFixed(4)} so far
          </div>
        )}
        {project.site_url && (
          <div className="text-xs text-blue-400 truncate">{project.site_url}</div>
        )}
      </div>
    </Link>
  )
}

function StatCard({ label, value, accent }) {
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg px-5 py-4">
      <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">{label}</p>
      <p className={`text-2xl font-bold ${accent || 'text-slate-100'}`}>{value}</p>
    </div>
  )
}

export default function Dashboard() {
  const [statusFilter, setStatusFilter] = useState('')

  const { data: allProjects = [], isLoading: projectsLoading, error: projectsError } = useQuery({
    queryKey: ['projects'],
    queryFn: () => fetchProjects(),
    refetchInterval: 30000,
  })

  const { data: approvals = [] } = useQuery({
    queryKey: ['approvals'],
    queryFn: fetchPendingApprovals,
    refetchInterval: 30000,
  })

  const projects = Array.isArray(allProjects) ? allProjects : allProjects?.results || []
  const approvalsArr = Array.isArray(approvals) ? approvals : approvals?.results || []

  const activeCount = projects.filter(p => p.status === 'running').length
  const pendingApprovalCount = approvalsArr.length
  const now = new Date()
  const completedThisMonth = projects.filter(p => {
    if (p.status !== 'completed' || !p.completed_at) return false
    const d = new Date(p.completed_at)
    return d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth()
  }).length

  const filtered = statusFilter
    ? projects.filter(p => p.status === statusFilter)
    : projects

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-slate-100">Projects</h1>
          <p className="text-sm text-slate-400 mt-0.5">Monitor and manage all agent pipelines</p>
        </div>
        <Link
          to="/new"
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium transition-colors"
        >
          <Plus size={16} />
          New Project
        </Link>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard label="Active Pipelines" value={activeCount} accent="text-blue-400" />
        <StatCard label="Pending Approvals" value={pendingApprovalCount} accent={pendingApprovalCount > 0 ? 'text-amber-400' : 'text-slate-100'} />
        <StatCard label="Completed This Month" value={completedThisMonth} accent="text-green-400" />
      </div>

      {/* Filter tabs */}
      <div className="flex items-center gap-1 overflow-x-auto pb-1">
        {STATUS_FILTERS.map(f => (
          <button
            key={f.key}
            onClick={() => setStatusFilter(f.key)}
            className={`flex-shrink-0 px-3 py-1.5 rounded text-xs font-medium transition-colors ${
              statusFilter === f.key
                ? 'bg-slate-700 text-slate-100'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Project grid */}
      {projectsLoading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 size={24} className="animate-spin text-slate-500" />
          <span className="ml-3 text-slate-400 text-sm">Loading projects...</span>
        </div>
      ) : projectsError ? (
        <div className="flex items-center gap-2 p-4 rounded-lg bg-red-950/30 border border-red-900/40 text-red-400 text-sm">
          <AlertCircle size={16} />
          {projectsError.message}
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16">
          <p className="text-slate-500 text-sm mb-4">
            {statusFilter ? `No projects with status "${statusFilter}"` : 'No projects yet'}
          </p>
          {!statusFilter && (
            <Link
              to="/new"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium transition-colors"
            >
              <Plus size={16} />
              Create First Project
            </Link>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map(project => (
            <ProjectCard key={project.id} project={project} />
          ))}
        </div>
      )}
    </div>
  )
}
