import { NavLink, useLocation } from 'react-router-dom'
import { Users, Zap } from 'lucide-react'
import { cn } from '@/lib/utils'

const nav = [
  { to: '/clients', label: 'Clients', icon: Users },
]

export function Sidebar() {
  const location = useLocation()

  return (
    <aside className="w-56 flex-shrink-0 bg-slate-900 flex flex-col">
      {/* Logo */}
      <div className="h-14 flex items-center px-4 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-brand-500 flex items-center justify-center">
            <Zap className="w-4 h-4 text-white" strokeWidth={2.5} />
          </div>
          <span className="text-white font-semibold text-sm tracking-tight">CloudIA</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-2 py-3 space-y-0.5">
        {nav.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-2.5 px-3 py-2 rounded-md text-sm font-medium transition-colors',
                isActive || location.pathname.startsWith(to)
                  ? 'bg-slate-800 text-white'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
              )
            }
          >
            <Icon className="w-4 h-4 flex-shrink-0" />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-slate-800">
        <p className="text-xs text-slate-500">AI Orchestra v1.0</p>
      </div>
    </aside>
  )
}
