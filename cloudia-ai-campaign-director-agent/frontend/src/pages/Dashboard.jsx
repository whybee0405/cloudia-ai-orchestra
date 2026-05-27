import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Plus, Bell, BarChart2, Calendar, CheckSquare } from 'lucide-react';
import { getCampaigns } from '../api/campaigns';
import { getApprovals } from '../api/approvals';
import StatusBadge from '../components/StatusBadge';
import PlatformBadge from '../components/PlatformBadge';

const PLATFORM_ICONS = {
  instagram: '📸',
  facebook: '👤',
  twitter: '🐦',
  x: '𝕏',
  linkedin: '💼',
  tiktok: '🎵',
  youtube: '▶',
  pinterest: '📌',
};

function StatCard({ icon: Icon, label, value, color = 'text-blue-600' }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-5 flex items-center gap-4">
      <div className={`p-3 rounded-lg bg-gray-50 ${color}`}>
        <Icon className="w-5 h-5" />
      </div>
      <div>
        <p className="text-2xl font-semibold text-gray-900">{value ?? '—'}</p>
        <p className="text-xs text-gray-500 mt-0.5">{label}</p>
      </div>
    </div>
  );
}

function CampaignCard({ campaign }) {
  const platforms = campaign.platforms || [];
  const progress = campaign.progress ?? 0;

  return (
    <Link
      to={`/campaigns/${campaign.id}`}
      className="bg-white border border-gray-200 rounded-xl p-5 hover:border-blue-400 hover:shadow-sm transition-all block"
    >
      <div className="flex items-start justify-between gap-2 mb-3">
        <div>
          <p className="text-xs text-gray-400 uppercase tracking-wide">{campaign.client_name || campaign.client_id}</p>
          <h3 className="text-sm font-semibold text-gray-900 mt-0.5">{campaign.name}</h3>
        </div>
        <StatusBadge status={campaign.status} />
      </div>

      {campaign.goal && (
        <p className="text-xs text-gray-500 mb-3">{campaign.goal}</p>
      )}

      <div className="flex flex-wrap gap-1 mb-3">
        {platforms.map((p) => (
          <span key={p} title={p} className="text-base">
            {PLATFORM_ICONS[p] || p}
          </span>
        ))}
      </div>

      <div className="space-y-1">
        <div className="flex items-center justify-between text-xs text-gray-500">
          <span>Progress</span>
          <span>{progress}%</span>
        </div>
        <div className="w-full bg-gray-100 rounded-full h-1.5">
          <div
            className="bg-blue-500 h-1.5 rounded-full transition-all"
            style={{ width: `${Math.min(progress, 100)}%` }}
          />
        </div>
      </div>

      {campaign.posts_this_week !== undefined && (
        <p className="text-xs text-gray-400 mt-2">
          {campaign.posts_this_week} posts this week
        </p>
      )}
    </Link>
  );
}

export default function Dashboard() {
  const { data: campaignsData, isLoading: loadingCampaigns } = useQuery({
    queryKey: ['campaigns'],
    queryFn: () => getCampaigns(),
    staleTime: 30000,
  });

  const { data: approvalsData } = useQuery({
    queryKey: ['approvals'],
    queryFn: getApprovals,
    staleTime: 15000,
  });

  const campaigns = campaignsData?.campaigns || campaignsData || [];
  const approvals = approvalsData?.gates || approvalsData || [];
  const pendingApprovals = approvals.filter((a) => a.status === 'pending').length;

  const activeCampaigns = campaigns.filter((c) => c.status === 'active').length;
  const postsThisWeek = campaigns.reduce((sum, c) => sum + (c.posts_this_week || 0), 0);
  const postsThisMonth = campaigns.reduce((sum, c) => sum + (c.posts_this_month || 0), 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Dashboard</h1>
          <p className="text-sm text-gray-500 mt-0.5">Campaign overview</p>
        </div>
        <div className="flex items-center gap-3">
          {pendingApprovals > 0 && (
            <Link
              to="/campaigns"
              className="inline-flex items-center gap-1.5 px-3 py-2 text-sm bg-orange-50 border border-orange-200 text-orange-700 rounded-lg hover:bg-orange-100"
            >
              <Bell className="w-4 h-4" />
              {pendingApprovals} pending review{pendingApprovals !== 1 ? 's' : ''}
            </Link>
          )}
          <Link
            to="/campaigns/new"
            className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            <Plus className="w-4 h-4" />
            New Campaign
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard icon={BarChart2} label="Active Campaigns" value={activeCampaigns} color="text-blue-600" />
        <StatCard icon={Calendar} label="Posts This Week" value={postsThisWeek} color="text-green-600" />
        <StatCard icon={CheckSquare} label="Posts This Month" value={postsThisMonth} color="text-purple-600" />
      </div>

      {loadingCampaigns ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-white border border-gray-200 rounded-xl p-5 animate-pulse">
              <div className="h-3 bg-gray-200 rounded w-1/3 mb-2" />
              <div className="h-4 bg-gray-200 rounded w-2/3 mb-4" />
              <div className="h-2 bg-gray-200 rounded w-full" />
            </div>
          ))}
        </div>
      ) : campaigns.length === 0 ? (
        <div className="text-center py-16 border border-dashed border-gray-200 rounded-xl">
          <p className="text-gray-400 text-sm mb-4">No campaigns yet</p>
          <Link
            to="/campaigns/new"
            className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            <Plus className="w-4 h-4" />
            Create your first campaign
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {campaigns.map((c) => (
            <CampaignCard key={c.id} campaign={c} />
          ))}
        </div>
      )}
    </div>
  );
}
