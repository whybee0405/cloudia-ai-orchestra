import { NavLink, Outlet, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, LayoutDashboard, AlertTriangle, Activity, FileText, DollarSign, Dna } from 'lucide-react'
import { useClient } from '@/shared/hooks/useClient'
import { PageLoader } from '@/shared/components/LoadingSpinner'

const TABS = [
  { to: 'dashboard',  label: 'Dashboard',        icon: LayoutDashboard },
  { to: 'anomalies',  label: 'Anomaly History',   icon: AlertTriangle   },
  { to: 'activity',   label: 'Activity Feed',     icon: Activity        },
  { to: 'output-log', label: 'Campaign Output',   icon: FileText        },
  { to: 'costs',      label: 'Agent Costs',       icon: DollarSign      },
  { to: 'brand-dna',  label: 'Brand DNA Audit',   icon: Dna             },
]

export function ReportsModule() {
  const { clientId } = useParams<{ clientId: string }>()
  const navigate = useNavigate()
  const { data: client, isLoading } = useClient(clientId!)

  if (isLoading) return <PageLoader />
  if (!client) return <div className="p-8 text-sm text-red-600">Client not found.</div>

  return (
    <div className="p-4 md:p-8">
      <button
        onClick={() => navigate(`/clients/${clientId}`)}
        className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 mb-5 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Hub
      </button>

      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Reports</h1>
        <p className="text-sm text-slate-500 mt-0.5">{client.name}</p>
      </div>

      {/* Tab strip */}
      <div className="flex items-center gap-1 border-b border-slate-200 mb-6 overflow-x-auto">
        {TABS.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-2 px-4 py-2 text-sm font-medium whitespace-nowrap transition-colors border-b-2 -mb-px ${
                isActive
                  ? 'border-slate-700 text-slate-900'
                  : 'border-transparent text-slate-500 hover:text-slate-700'
              }`
            }
          >
            <Icon className="w-3.5 h-3.5" />
            {label}
          </NavLink>
        ))}
      </div>

      <Outlet />
    </div>
  )
}
