const STATUS_STYLES = {
  // Project statuses
  planned: 'bg-slate-700 text-slate-300',
  running: 'bg-blue-900/50 text-blue-300',
  awaiting_content_review: 'bg-amber-900/50 text-amber-300',
  awaiting_site_review: 'bg-amber-900/50 text-amber-300',
  completed: 'bg-green-900/50 text-green-300',
  failed: 'bg-red-900/50 text-red-300',
  cancelled: 'bg-slate-700 text-slate-400',
  needs_input: 'bg-orange-900/50 text-orange-300',
  // Gate statuses
  pending: 'bg-yellow-900/50 text-yellow-300',
  approved: 'bg-green-900/50 text-green-300',
  rejected: 'bg-red-900/50 text-red-300',
  revision_requested: 'bg-orange-900/50 text-orange-300',
  // Task statuses
  blocked: 'bg-red-900/50 text-red-400',
  skipped: 'bg-slate-700 text-slate-400',
  // Content statuses
  draft: 'bg-slate-700 text-slate-300',
  published: 'bg-green-900/50 text-green-300',
}

const STATUS_LABELS = {
  planned: 'Planned',
  running: 'Running',
  awaiting_content_review: 'Awaiting Content Review',
  awaiting_site_review: 'Awaiting Site Review',
  completed: 'Completed',
  failed: 'Failed',
  cancelled: 'Cancelled',
  needs_input: 'Needs Input',
  pending: 'Pending',
  approved: 'Approved',
  rejected: 'Rejected',
  revision_requested: 'Revision Requested',
  blocked: 'Blocked',
  skipped: 'Skipped',
  draft: 'Draft',
  published: 'Published',
}

const SIZE_CLASSES = {
  xs: 'text-xs px-1.5 py-0.5',
  sm: 'text-xs px-2 py-0.5',
  md: 'text-sm px-2.5 py-1',
}

export function StatusBadge({ status, size = 'sm' }) {
  const colorClass = STATUS_STYLES[status] || 'bg-slate-700 text-slate-300'
  const label = STATUS_LABELS[status] || (status ? status.replace(/_/g, ' ') : 'Unknown')
  const sizeClass = SIZE_CLASSES[size] || SIZE_CLASSES.sm

  return (
    <span className={`inline-flex items-center rounded-full font-medium whitespace-nowrap ${colorClass} ${sizeClass}`}>
      {status === 'running' && (
        <span className="mr-1.5 h-1.5 w-1.5 rounded-full bg-blue-400 pipeline-pulse" />
      )}
      {label}
    </span>
  )
}
