const STATUS_STYLES = {
  planned: 'bg-gray-100 text-gray-700',
  creating: 'bg-blue-100 text-blue-700',
  planning: 'bg-blue-100 text-blue-700',
  approved: 'bg-green-100 text-green-700',
  active: 'bg-emerald-100 text-emerald-700',
  failed: 'bg-red-100 text-red-700',
  rejected: 'bg-red-100 text-red-700',
  published: 'bg-purple-100 text-purple-700',
  scheduled: 'bg-yellow-100 text-yellow-700',
  pending_review: 'bg-orange-100 text-orange-700',
  paused: 'bg-gray-100 text-gray-600',
  cancelled: 'bg-gray-100 text-gray-500',
  draft: 'bg-slate-100 text-slate-600',
};

export default function StatusBadge({ status, className = '' }) {
  const style = STATUS_STYLES[status] || 'bg-gray-100 text-gray-600';
  const label = status ? status.replace(/_/g, ' ') : 'unknown';
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize ${style} ${className}`}
    >
      {label}
    </span>
  );
}
