import { Routes, Route, NavLink, useLocation } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { LayoutDashboard, CheckSquare, Settings as SettingsIcon, Cloud, Bell } from 'lucide-react'
import Dashboard from './pages/Dashboard'
import NewProject from './pages/NewProject'
import ProjectDetail from './pages/ProjectDetail'
import ContentReview from './pages/ContentReview'
import ApprovalQueue from './pages/ApprovalQueue'
import Settings from './pages/Settings'
import { fetchPendingApprovals } from './api/approvals'

const NAV_ITEMS = [
  {
    to: '/',
    label: 'Dashboard',
    icon: LayoutDashboard,
    exact: true,
  },
  {
    to: '/approvals',
    label: 'Approvals',
    icon: CheckSquare,
    badge: true,
  },
  {
    to: '/settings',
    label: 'Settings',
    icon: SettingsIcon,
  },
]

function Sidebar() {
  const location = useLocation()

  const { data: approvals = [] } = useQuery({
    queryKey: ['approvals'],
    queryFn: fetchPendingApprovals,
    refetchInterval: 30000,
  })
  const pendingCount = (Array.isArray(approvals) ? approvals : approvals?.results || []).length

  return (
    <aside className="flex flex-col w-56 flex-shrink-0 bg-slate-800 border-r border-slate-700 min-h-screen">
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-5 py-5 border-b border-slate-700">
        <div className="w-7 h-7 rounded-lg bg-blue-600 flex items-center justify-center flex-shrink-0">
          <Cloud size={15} className="text-white" />
        </div>
        <div>
          <span className="text-sm font-bold text-slate-100 tracking-tight">CloudIA</span>
          <span className="block text-xs text-slate-500 leading-none mt-0.5">Agent Dashboard</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV_ITEMS.map(({ to, label, icon: Icon, exact, badge }) => {
          const isActive = exact
            ? location.pathname === to
            : location.pathname.startsWith(to)

          return (
            <NavLink
              key={to}
              to={to}
              end={exact}
              className={({ isActive: navActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors group ${
                  navActive
                    ? 'bg-slate-700 text-slate-100'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700/50'
                }`
              }
            >
              <Icon size={16} />
              <span className="flex-1">{label}</span>
              {badge && pendingCount > 0 && (
                <span className="flex-shrink-0 min-w-5 h-5 px-1.5 rounded-full bg-amber-500 text-slate-900 text-xs font-bold flex items-center justify-center">
                  {pendingCount > 99 ? '99+' : pendingCount}
                </span>
              )}
            </NavLink>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="px-5 py-4 border-t border-slate-700">
        <p className="text-xs text-slate-600">CloudIA v1.0.0</p>
      </div>
    </aside>
  )
}

export default function App() {
  return (
    <div className="flex min-h-screen bg-slate-900">
      <Sidebar />
      <main className="flex-1 min-w-0 overflow-auto">
        <div className="max-w-7xl mx-auto px-6 py-8">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/new" element={<NewProject />} />
            <Route path="/projects/:id" element={<ProjectDetail />} />
            <Route path="/projects/:id/content" element={<ContentReview />} />
            <Route path="/approvals" element={<ApprovalQueue />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </div>
      </main>
    </div>
  )
}
