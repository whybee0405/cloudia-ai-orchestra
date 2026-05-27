import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { PauseCircle, XCircle, Clock, Loader } from 'lucide-react';
import { getScheduled, cancelPost } from '../api/publishing';
import { getCampaigns, pauseCampaign } from '../api/campaigns';
import StatusBadge from '../components/StatusBadge';
import PlatformBadge from '../components/PlatformBadge';

const STATUS_COLORS = {
  scheduled: 'border-l-yellow-400',
  published: 'border-l-purple-400',
  failed: 'border-l-red-400',
  cancelled: 'border-l-gray-300',
  publishing: 'border-l-blue-400',
};

export default function Scheduler() {
  const queryClient = useQueryClient();
  const [selectedCampaign, setSelectedCampaign] = useState('all');
  const [notification, setNotification] = useState(null);

  const { data: scheduledData, isLoading } = useQuery({
    queryKey: ['scheduled', selectedCampaign],
    queryFn: () =>
      getScheduled(selectedCampaign !== 'all' ? { campaign_id: selectedCampaign } : {}),
    staleTime: 10000,
    refetchInterval: 30000,
  });

  const { data: campaignsData } = useQuery({
    queryKey: ['campaigns'],
    queryFn: getCampaigns,
    staleTime: 30000,
  });

  const posts = scheduledData?.posts || scheduledData || [];
  const campaigns = campaignsData?.campaigns || campaignsData || [];
  const activeCampaigns = campaigns.filter((c) => c.status === 'active');

  const cancelMutation = useMutation({
    mutationFn: cancelPost,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scheduled'] });
      setNotification({ type: 'success', msg: 'Post cancelled' });
      setTimeout(() => setNotification(null), 2500);
    },
    onError: () => {
      setNotification({ type: 'error', msg: 'Failed to cancel post' });
      setTimeout(() => setNotification(null), 3000);
    },
  });

  const pauseAllMutation = useMutation({
    mutationFn: async () => {
      const toPause = activeCampaigns.map((c) => pauseCampaign(c.id));
      await Promise.all(toPause);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
      queryClient.invalidateQueries({ queryKey: ['scheduled'] });
      setNotification({ type: 'success', msg: `${activeCampaigns.length} campaign(s) paused` });
      setTimeout(() => setNotification(null), 3000);
    },
  });

  const groupedByDate = posts.reduce((acc, post) => {
    const date = post.scheduled_at
      ? new Date(post.scheduled_at).toLocaleDateString('en-US', {
          weekday: 'short',
          month: 'short',
          day: 'numeric',
        })
      : 'Unscheduled';
    if (!acc[date]) acc[date] = [];
    acc[date].push(post);
    return acc;
  }, {});

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Scheduler</h1>
          <p className="text-sm text-gray-500 mt-0.5">{posts.length} scheduled posts</p>
        </div>
        {activeCampaigns.length > 0 && (
          <button
            onClick={() => pauseAllMutation.mutate()}
            disabled={pauseAllMutation.isPending}
            className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium border border-orange-300 text-orange-700 bg-orange-50 rounded-lg hover:bg-orange-100 disabled:opacity-50"
          >
            {pauseAllMutation.isPending ? (
              <Loader className="w-4 h-4 animate-spin" />
            ) : (
              <PauseCircle className="w-4 h-4" />
            )}
            Pause All Campaigns ({activeCampaigns.length})
          </button>
        )}
      </div>

      {notification && (
        <div
          className={`px-4 py-2.5 rounded text-sm font-medium ${
            notification.type === 'success'
              ? 'bg-green-50 text-green-700 border border-green-200'
              : 'bg-red-50 text-red-700 border border-red-200'
          }`}
        >
          {notification.msg}
        </div>
      )}

      <div className="flex items-center gap-2">
        <label className="text-sm text-gray-600">Campaign:</label>
        <select
          value={selectedCampaign}
          onChange={(e) => setSelectedCampaign(e.target.value)}
          className="text-sm border border-gray-200 rounded px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="all">All Campaigns</option>
          {campaigns.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-white border border-gray-200 rounded-lg h-16 animate-pulse" />
          ))}
        </div>
      ) : posts.length === 0 ? (
        <div className="text-center py-16 border border-dashed border-gray-200 rounded-xl text-gray-400 text-sm">
          No scheduled posts
        </div>
      ) : (
        <div className="space-y-6">
          {Object.entries(groupedByDate).map(([date, datePosts]) => (
            <div key={date}>
              <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2 flex items-center gap-2">
                <Clock className="w-3.5 h-3.5" />
                {date}
                <span className="text-gray-400 normal-case font-normal">({datePosts.length})</span>
              </h2>
              <div className="space-y-2">
                {datePosts.map((post) => {
                  const borderColor = STATUS_COLORS[post.status] || 'border-l-gray-300';
                  return (
                    <div
                      key={post.id}
                      className={`bg-white border border-gray-200 border-l-4 ${borderColor} rounded-lg px-4 py-3 flex items-center gap-4`}
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-sm font-medium text-gray-800 truncate">
                            {post.asset?.title || post.title || `Post #${post.id}`}
                          </span>
                          <StatusBadge status={post.status} />
                          {post.platform && <PlatformBadge platform={post.platform} />}
                          {post.platforms?.map((p) => <PlatformBadge key={p} platform={p} />)}
                        </div>
                        {post.scheduled_at && (
                          <p className="text-xs text-gray-400 mt-0.5">
                            {new Date(post.scheduled_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </p>
                        )}
                        {post.campaign_name && (
                          <p className="text-xs text-gray-400">{post.campaign_name}</p>
                        )}
                      </div>

                      {post.status === 'scheduled' && (
                        <button
                          onClick={() => cancelMutation.mutate(post.id)}
                          disabled={cancelMutation.isPending}
                          className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs text-red-600 border border-red-200 rounded hover:bg-red-50 disabled:opacity-50 shrink-0"
                          title="Cancel post"
                        >
                          <XCircle className="w-3.5 h-3.5" />
                          Cancel
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
