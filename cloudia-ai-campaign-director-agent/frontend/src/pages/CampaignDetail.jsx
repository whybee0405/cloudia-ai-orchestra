import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Pause, Play, ClipboardList, RefreshCw } from 'lucide-react';
import { useCampaignStatus } from '../hooks/useCampaignStatus';
import { pauseCampaign, resumeCampaign } from '../api/campaigns';
import { useAssets } from '../hooks/useAssets';
import { useAnalytics } from '../hooks/useAnalytics';
import { useQuery } from '@tanstack/react-query';
import { getCalendar } from '../api/calendar';
import PipelineStatus from '../components/PipelineStatus';
import StatusBadge from '../components/StatusBadge';
import AssetCard from '../components/AssetCard';
import AssetPreview from '../components/AssetPreview';
import CalendarView from '../components/CalendarView';
import AnalyticsChart from '../components/AnalyticsChart';

function StatCard({ label, value }) {
  return (
    <div className="bg-gray-50 rounded-lg p-4">
      <p className="text-xs text-gray-500">{label}</p>
      <p className="text-xl font-semibold text-gray-900 mt-0.5">{value ?? '—'}</p>
    </div>
  );
}

export default function CampaignDetail() {
  const { id } = useParams();
  const queryClient = useQueryClient();
  const [tab, setTab] = useState('calendar');
  const [selectedAsset, setSelectedAsset] = useState(null);

  const { data: campaign, isLoading, error } = useCampaignStatus(id);
  const { data: assetsData } = useAssets({ campaign_id: id });
  const { data: analyticsData } = useAnalytics({ campaign_id: id });
  const { data: calendarData } = useQuery({
    queryKey: ['calendar', { campaign_id: id }],
    queryFn: () => getCalendar({ campaign_id: id }),
    staleTime: 15000,
  });

  const assets = assetsData?.assets || assetsData || [];
  const calendarItems = calendarData?.items || calendarData || [];
  const analytics = analyticsData?.summary || analyticsData || {};

  const pauseMutation = useMutation({
    mutationFn: () => pauseCampaign(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['campaign', id] }),
  });

  const resumeMutation = useMutation({
    mutationFn: () => resumeCampaign(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['campaign', id] }),
  });

  if (isLoading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-6 bg-gray-200 rounded w-1/3" />
        <div className="h-16 bg-gray-200 rounded" />
        <div className="h-40 bg-gray-200 rounded" />
      </div>
    );
  }

  if (error || !campaign) {
    return (
      <div className="text-center py-16">
        <p className="text-red-600 text-sm">Failed to load campaign</p>
        <Link to="/" className="text-blue-600 text-sm mt-2 inline-block">Back to Dashboard</Link>
      </div>
    );
  }

  const TABS = [
    { key: 'calendar', label: 'Calendar' },
    { key: 'assets', label: `Assets (${assets.length})` },
    { key: 'analytics', label: 'Analytics' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Link to="/" className="text-xs text-gray-400 hover:text-gray-600">Dashboard</Link>
            <span className="text-xs text-gray-300">/</span>
            <span className="text-xs text-gray-600">{campaign.name}</span>
          </div>
          <h1 className="text-xl font-semibold text-gray-900">{campaign.name}</h1>
          <div className="flex items-center gap-3 mt-1">
            <StatusBadge status={campaign.status} />
            {campaign.client_name && (
              <span className="text-xs text-gray-500">{campaign.client_name}</span>
            )}
            {campaign.goal && (
              <span className="text-xs text-gray-500">{campaign.goal}</span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <Link
            to={`/campaigns/${id}/review`}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-sm border border-gray-300 text-gray-700 rounded hover:bg-gray-50"
          >
            <ClipboardList className="w-4 h-4" />
            Review
          </Link>

          {campaign.status === 'active' ? (
            <button
              onClick={() => pauseMutation.mutate()}
              disabled={pauseMutation.isPending}
              className="inline-flex items-center gap-1.5 px-3 py-2 text-sm border border-gray-300 text-gray-700 rounded hover:bg-gray-50 disabled:opacity-50"
            >
              <Pause className="w-4 h-4" />
              Pause
            </button>
          ) : campaign.status === 'paused' ? (
            <button
              onClick={() => resumeMutation.mutate()}
              disabled={resumeMutation.isPending}
              className="inline-flex items-center gap-1.5 px-3 py-2 text-sm bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
            >
              <Play className="w-4 h-4" />
              Resume
            </button>
          ) : null}
        </div>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl p-5">
        <h2 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-4">Pipeline</h2>
        <PipelineStatus pipelineData={campaign.pipeline} campaignStatus={campaign.status} />
      </div>

      <div className="flex border-b border-gray-200 gap-1">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              tab === t.key
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'calendar' && (
        <div className="bg-white border border-gray-200 rounded-xl p-4" style={{ height: 600 }}>
          <CalendarView
            events={calendarItems}
            onSelectEvent={(item) => {
              const asset = assets.find((a) => a.id === item.asset_id) || item.asset;
              if (asset) setSelectedAsset(asset);
            }}
          />
        </div>
      )}

      {tab === 'assets' && (
        <div>
          {assets.length === 0 ? (
            <div className="text-center py-12 text-gray-400 text-sm border border-dashed border-gray-200 rounded-xl">
              No assets generated yet
            </div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
              {assets.map((asset) => (
                <AssetCard
                  key={asset.id}
                  asset={asset}
                  onClick={setSelectedAsset}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {tab === 'analytics' && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <StatCard label="Total Reach" value={analytics.total_reach?.toLocaleString()} />
            <StatCard label="Impressions" value={analytics.total_impressions?.toLocaleString()} />
            <StatCard label="Engagements" value={analytics.total_engagements?.toLocaleString()} />
            <StatCard label="Engagement Rate" value={analytics.avg_engagement_rate ? `${(analytics.avg_engagement_rate * 100).toFixed(2)}%` : '—'} />
          </div>

          {analyticsData?.daily && analyticsData.daily.length > 0 && (
            <div className="bg-white border border-gray-200 rounded-xl p-5">
              <h3 className="text-sm font-medium text-gray-700 mb-4">Performance Over Time</h3>
              <AnalyticsChart
                type="line"
                data={analyticsData.daily}
                series={[
                  { key: 'reach', label: 'Reach', color: '#3b5bdb' },
                  { key: 'engagements', label: 'Engagements', color: '#10b981' },
                ]}
                height={200}
              />
            </div>
          )}
        </div>
      )}

      {selectedAsset && (
        <AssetPreview asset={selectedAsset} onClose={() => setSelectedAsset(null)} />
      )}
    </div>
  );
}
