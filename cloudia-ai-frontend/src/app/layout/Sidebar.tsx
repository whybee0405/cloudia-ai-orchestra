import { NavLink, useLocation } from 'react-router-dom'
import { Users, Zap, X, Activity } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAgentActivity } from '@/shared/context/AgentActivityContext'

const nav = [
  { to: '/clients', label: 'Clients', icon: Users },
  { to: '/activity', label: 'Agent Activity', icon: Activity },
]

interface Props {
  mobileOpen: boolean
  onClose: () => void
}

export function Sidebar({ mobileOpen, onClose }: Props) {
  const location = useLocation()
  const { jobs } = useAgentActivity()
  const activeCount = jobs.filter(j => j.status === 'running').length

  return (
    <>
      {/* Mobile backdrop */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/40 md:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside className={cn(
        'w-56 flex-shrink-0 bg-slate-900 flex flex-col',
        // On mobile: fixed overlay, slides in/out
        'fixed inset-y-0 left-0 z-50 transition-transform duration-200 ease-in-out',
        mobileOpen ? 'translate-x-0' : '-translate-x-full',
        // On md+: static in flow, always visible
        'md:relative md:translate-x-0',
      )}>
        {/* Logo */}
        <div className="h-14 flex items-center justify-between px-4 border-b border-slate-800 flex-shrink-0">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-brand-500 flex items-center justify-center">
              <Zap className="w-4 h-4 text-white" strokeWidth={2.5} />
            </div>
            <span className="text-white font-semibold text-sm tracking-tight">CloudIA</span>
          </div>
          <button
            onClick={onClose}
            className="md:hidden text-slate-400 hover:text-white p-1.5 rounded transition-colors"
            aria-label="Close menu"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-2 py-3 space-y-0.5">
          {nav.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              onClick={onClose}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-2.5 px-3 py-2.5 rounded-md text-sm font-medium transition-colors',
                  isActive || location.pathname.startsWith(to)
                    ? 'bg-slate-800 text-white'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
                )
              }
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              <span className="flex-1">{label}</span>
              {to === '/activity' && activeCount > 0 && (
                <span className="flex h-2 w-2 relative">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-brand-500" />
                </span>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-slate-800 flex-shrink-0">
          <p className="text-xs text-slate-500">AI Orchestra v1.0</p>
        </div>
      </aside>
    </>
  )
}
