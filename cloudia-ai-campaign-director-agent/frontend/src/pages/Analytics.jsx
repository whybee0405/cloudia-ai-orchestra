import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Download, BarChart2, TrendingUp, Users, Eye } from 'lucide-react';
import { getAnalytics } from '../api/analytics';
import { getCampaigns } from '../api/campaigns';
import AnalyticsChart from '../components/AnalyticsChart';
import PlatformBadge from '../components/PlatformBadge';

const today = new Date();
const thirtyDaysAgo = new Date(today);
thirtyDaysAgo.setDate(today.getDate() - 30);

function fmt(n) {
  if (n == null) return '—';
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toLocaleString();
}

function SummaryCard({ icon: Icon, label, value, color = 'text-blue-600', change }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-5">
      <div className="flex items-center gap-3 mb-3">
        <div className={`p-2 rounded-lg bg-gray-50 ${color}`}>
          <Icon className="w-4 h-4" />
        </div>
        <p className="text-xs text-gray-500">{label}</p>
      </div>
      <p className="text-2xl font-semibold text-gray-900">{value}</p>
      {change != null && (
        <p className={`text-xs mt-1 ${change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
          {change >= 0 ? '+' : ''}{change}% vs previous period
        </p>
      )}
    </div>
  );
}

export default function Analytics() {
  const [filters, setFilters] = useState({
    start_date: thirtyDaysAgo.toISOString().slice(0, 10),
    end_date: today.toISOString().slice(0, 10),
    campaign_id: 'all',
    platform: 'all',
  });

  const queryFilters = {};
  if (filters.start_date) queryFilters.start_date = filters.start_date;
  if (filters.end_date) queryFilters.end_date = filters.end_date;
  if (filters.campaign_id !== 'all') queryFilters.campaign_id = filters.campaign_id;
  if (filters.platform !== 'all') queryFilters.platform = filters.platform;

  const { data, isLoading } = useQuery({
    queryKey: ['analytics', queryFilters],
    queryFn: () => getAnalytics(queryFilters),
    staleTime: 60000,
  });

  const { data: campaignsData } = useQuery({
    queryKey: ['campaigns'],
    queryFn: getCampaigns,
    staleTime: 60000,
  });

  const campaigns = campaignsData?.campaigns || campaignsData || [];
  const summary = data?.summary || {};
  const daily = data?.daily || [];
  const topPosts = data?.top_posts || [];
  const byPlatform = data?.by_platform || [];

  const setFilter = (k, v) => setFilters((f) => ({ ...f, [k]: v }));

  const exportCSV = () => {
    if (!topPosts.length) return;
    const headers = ['Title', 'Platform', 'Reach', 'Impressions', 'Engagements', 'Engagement Rate', 'Published At'];
    const rows = topPosts.map((p) => [
      `"${(p.title || '').replace(/"/g, '""')}"`,
      p.platform || '',
      p.reach || 0,
      p.impressions || 0,
      p.engagements || 0,
      p.engagement_rate ? (p.engagement_rate * 100).toFixed(2) + '%' : '',
      p.published_at || '',
    ]);
    const csv = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `analytics-${filters.start_date}-${filters.end_date}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Analytics</h1>
          <p className="text-sm text-gray-500 mt-0.5">Performance overview</p>
        </div>
        <button
          onClick={exportCSV}
          disabled={!topPosts.length}
          className="inline-flex items-center gap-1.5 px-3 py-2 text-sm border border-gray-300 text-gray-700 rounded hover:bg-gray-50 disabled:opacity-40"
        >
          <Download className="w-4 h-4" />
          Export CSV
        </button>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl p-4">
        <div className="flex flex-wrap gap-4">
          <div className="flex items-center gap-2">
            <label className="text-xs text-gray-600 whitespace-nowrap">From</label>
            <input
              type="date"
              value={filters.start_date}
              onChange={(e) => setFilter('start_date', e.target.value)}
              className="text-sm border border-gray-200 rounded px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div className="flex items-center gap-2">
            <label className="text-xs text-gray-600 whitespace-nowrap">To</label>
            <input
              type="date"
              value={filters.end_date}
              onChange={(e) => setFilter('end_date', e.target.value)}
              className="text-sm border border-gray-200 rounded px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div className="flex items-center gap-2">
            <label className="text-xs text-gray-600">Campaign</label>
            <select
              value={filters.campaign_id}
              onChange={(e) => setFilter('campaign_id', e.target.value)}
              className="text-sm border border-gray-200 rounded px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="all">All Campaigns</option>
              {campaigns.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-2">
            <label className="text-xs text-gray-600">Platform</label>
            <select
              value={filters.platform}
              onChange={(e) => setFilter('platform', e.target.value)}
              className="text-sm border border-gray-200 rounded px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              {['all', 'instagram', 'facebook', 'twitter', 'linkedin', 'tiktok', 'youtube'].map((p) => (
                <option key={p} value={p}>{p === 'all' ? 'All Platforms' : p}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="bg-white border border-gray-200 rounded-xl h-28 animate-pulse" />
          ))}
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <SummaryCard icon={Users} label="Total Reach" value={fmt(summary.total_reach)} color="text-blue-600" change={summary.reach_change} />
            <SummaryCard icon={Eye} label="Impressions" value={fmt(summary.total_impressions)} color="text-purple-600" change={summary.impressions_change} />
            <SummaryCard icon={TrendingUp} label="Engagements" value={fmt(summary.total_engagements)} color="text-green-600" change={summary.engagements_change} />
            <SummaryCard
              icon={BarChart2}
              label="Avg Engagement Rate"
              value={summary.avg_engagement_rate != null ? `${(summary.avg_engagement_rate * 100).toFixed(2)}%` : '—'}
              color="text-orange-600"
              change={summary.engagement_rate_change}
            />
          </div>

          {daily.length > 0 && (
            <div className="bg-white border border-gray-200 rounded-xl p-5">
              <h2 className="text-sm font-semibold text-gray-800 mb-4">Daily Performance</h2>
              <AnalyticsChart
                type="line"
                data={daily.map((d) => ({ ...d, label: d.date?.slice(5) || d.label }))}
                series={[
                  { key: 'reach', label: 'Reach', color: '#3b5bdb' },
                  { key: 'impressions', label: 'Impressions', color: '#8b5cf6' },
                  { key: 'engagements', label: 'Engagements', color: '#10b981' },
                ]}
                height={220}
              />
            </div>
          )}

          {byPlatform.length > 0 && (
            <div className="bg-white border border-gray-200 rounded-xl p-5">
              <h2 className="text-sm font-semibold text-gray-800 mb-4">By Platform</h2>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
                {byPlatform.map((p) => (
                  <div key={p.platform} className="text-center p-3 bg-gray-50 rounded-lg">
                    <PlatformBadge platform={p.platform} className="mb-2" />
                    <p className="text-base font-semibold text-gray-800">{fmt(p.engagements)}</p>
                    <p className="text-xs text-gray-400">engagements</p>
                    {p.engagement_rate != null && (
                      <p className="text-xs text-gray-500 mt-0.5">{(p.engagement_rate * 100).toFixed(1)}%</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {topPosts.length > 0 && (
            <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
              <div className="px-5 py-4 border-b border-gray-100">
                <h2 className="text-sm font-semibold text-gray-800">Top Posts</h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-100 bg-gray-50 text-xs text-gray-500 uppercase tracking-wide">
                      <th className="text-left px-5 py-3">Post</th>
                      <th className="text-left px-4 py-3">Platform</th>
                      <th className="text-right px-4 py-3">Reach</th>
                      <th className="text-right px-4 py-3">Impressions</th>
                      <th className="text-right px-4 py-3">Engagements</th>
                      <th className="text-right px-5 py-3">Rate</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {topPosts.map((post, idx) => (
                      <tr key={post.id || idx} className="hover:bg-gray-50">
                        <td className="px-5 py-3 text-gray-800 max-w-xs truncate">{post.title || `Post #${post.id}`}</td>
                        <td className="px-4 py-3">
                          {post.platform && <PlatformBadge platform={post.platform} />}
                        </td>
                        <td className="px-4 py-3 text-right text-gray-700">{fmt(post.reach)}</td>
                        <td className="px-4 py-3 text-right text-gray-700">{fmt(post.impressions)}</td>
                        <td className="px-4 py-3 text-right text-gray-700">{fmt(post.engagements)}</td>
                        <td className="px-5 py-3 text-right text-gray-700">
                          {post.engagement_rate != null
                            ? `${(post.engagement_rate * 100).toFixed(2)}%`
                            : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {!isLoading && !daily.length && !topPosts.length && (
            <div className="text-center py-16 border border-dashed border-gray-200 rounded-xl text-gray-400 text-sm">
              No analytics data for the selected period
            </div>
          )}
        </>
      )}
    </div>
  );
}
