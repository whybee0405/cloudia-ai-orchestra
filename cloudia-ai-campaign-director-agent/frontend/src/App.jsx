import { createBrowserRouter, RouterProvider, NavLink, Outlet } from 'react-router-dom';
import {
  LayoutDashboard,
  Calendar,
  Image,
  Clock,
  BarChart2,
  Settings,
  Link2,
  Plus,
} from 'lucide-react';

import Dashboard from './pages/Dashboard';
import NewCampaign from './pages/NewCampaign';
import CampaignDetail from './pages/CampaignDetail';
import ContentReview from './pages/ContentReview';
import ContentCalendar from './pages/ContentCalendar';
import AssetLibrary from './pages/AssetLibrary';
import Scheduler from './pages/Scheduler';
import Analytics from './pages/Analytics';
import PlatformAccounts from './pages/PlatformAccounts';
import BrandGuidelines from './pages/BrandGuidelines';
import SettingsPage from './pages/Settings';

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/calendar', label: 'Calendar', icon: Calendar },
  { to: '/assets', label: 'Assets', icon: Image },
  { to: '/scheduler', label: 'Scheduler', icon: Clock },
  { to: '/analytics', label: 'Analytics', icon: BarChart2 },
  { to: '/accounts', label: 'Accounts', icon: Link2 },
  { to: '/settings', label: 'Settings', icon: Settings },
];

function Layout() {
  return (
    <div className="min-h-screen bg-gray-50 flex">
      <aside className="w-56 bg-white border-r border-gray-200 flex flex-col shrink-0 sticky top-0 h-screen">
        <div className="px-5 py-4 border-b border-gray-100">
          <span className="text-base font-semibold text-gray-900">CloudIA</span>
          <span className="text-xs text-gray-400 block mt-0.5">Content Director</span>
        </div>

        <nav className="flex-1 py-3 overflow-y-auto">
          {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-4 py-2.5 text-sm font-medium transition-colors mx-2 rounded-lg mb-0.5 ${
                  isActive
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-800'
                }`
              }
            >
              <Icon className="w-4 h-4 shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="p-3 border-t border-gray-100">
          <NavLink
            to="/campaigns/new"
            className="flex items-center justify-center gap-1.5 w-full px-3 py-2 text-sm font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            <Plus className="w-4 h-4" />
            New Campaign
          </NavLink>
        </div>
      </aside>

      <main className="flex-1 min-w-0 p-6 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  );
}

const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: 'campaigns/new', element: <NewCampaign /> },
      { path: 'campaigns/:id', element: <CampaignDetail /> },
      { path: 'campaigns/:id/review', element: <ContentReview /> },
      { path: 'calendar', element: <ContentCalendar /> },
      { path: 'assets', element: <AssetLibrary /> },
      { path: 'scheduler', element: <Scheduler /> },
      { path: 'analytics', element: <Analytics /> },
      { path: 'accounts', element: <PlatformAccounts /> },
      { path: 'guidelines/:clientId', element: <BrandGuidelines /> },
      { path: 'settings', element: <SettingsPage /> },
    ],
  },
]);

export default function App() {
  return <RouterProvider router={router} />;
}
