import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { CheckSquare, ChevronLeft, Loader } from 'lucide-react';
import { getApprovals, approveGate, rejectGate } from '../api/approvals';
import ApprovalCard from '../components/ApprovalCard';

export default function ContentReview() {
  const { id: campaignId } = useParams();
  const queryClient = useQueryClient();
  const [bulkLoading, setBulkLoading] = useState(false);
  const [notification, setNotification] = useState(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ['approvals', campaignId],
    queryFn: () => getApprovals(campaignId ? { campaign_id: campaignId } : {}),
    staleTime: 10000,
  });

  const gates = (data?.gates || data || []).filter(
    (g) => !campaignId || String(g.campaign_id) === String(campaignId)
  );
  const pendingGates = gates.filter((g) => g.status === 'pending');

  const approveMutation = useMutation({
    mutationFn: ({ gateId, notes }) => approveGate(gateId, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['approvals'] });
      setNotification({ type: 'success', msg: 'Approved' });
      setTimeout(() => setNotification(null), 2000);
    },
    onError: () => {
      setNotification({ type: 'error', msg: 'Approval failed' });
      setTimeout(() => setNotification(null), 3000);
    },
  });

  const rejectMutation = useMutation({
    mutationFn: ({ gateId, notes }) => rejectGate(gateId, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['approvals'] });
      setNotification({ type: 'success', msg: 'Rejected' });
      setTimeout(() => setNotification(null), 2000);
    },
  });

  const handleBulkApprove = async () => {
    setBulkLoading(true);
    for (const g of pendingGates) {
      await approveGate(g.id, 'Bulk approved');
    }
    queryClient.invalidateQueries({ queryKey: ['approvals'] });
    setBulkLoading(false);
    setNotification({ type: 'success', msg: `${pendingGates.length} items approved` });
    setTimeout(() => setNotification(null), 2500);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {campaignId && (
            <Link
              to={`/campaigns/${campaignId}`}
              className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-800"
            >
              <ChevronLeft className="w-4 h-4" />
              Back
            </Link>
          )}
          <div>
            <h1 className="text-xl font-semibold text-gray-900">Content Review</h1>
            <p className="text-sm text-gray-500 mt-0.5">
              {pendingGates.length} pending, {gates.length} total
            </p>
          </div>
        </div>

        {pendingGates.length > 1 && (
          <button
            onClick={handleBulkApprove}
            disabled={bulkLoading}
            className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
          >
            {bulkLoading ? <Loader className="w-4 h-4 animate-spin" /> : <CheckSquare className="w-4 h-4" />}
            Approve All ({pendingGates.length})
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

      {isLoading ? (
        <div className="space-y-4">
          {[1, 2].map((i) => (
            <div key={i} className="bg-white border border-gray-200 rounded-xl h-48 animate-pulse" />
          ))}
        </div>
      ) : error ? (
        <div className="text-center py-12 text-red-600 text-sm">Failed to load review items</div>
      ) : pendingGates.length === 0 ? (
        <div className="text-center py-16 border border-dashed border-gray-200 rounded-xl">
          <CheckSquare className="w-8 h-8 text-green-400 mx-auto mb-2" />
          <p className="text-gray-500 text-sm">No pending reviews</p>
        </div>
      ) : (
        <div className="space-y-4">
          {pendingGates.map((gate) => (
            <ApprovalCard
              key={gate.id}
              gate={gate}
              asset={gate.asset}
              isLoading={approveMutation.isPending || rejectMutation.isPending}
              onApprove={(gateId, notes) => approveMutation.mutate({ gateId, notes })}
              onReject={(gateId, notes) => rejectMutation.mutate({ gateId, notes })}
            />
          ))}
        </div>
      )}

      {gates.filter((g) => g.status !== 'pending').length > 0 && (
        <div>
          <h2 className="text-sm font-medium text-gray-600 mb-3">Reviewed</h2>
          <div className="space-y-3">
            {gates
              .filter((g) => g.status !== 'pending')
              .map((gate) => (
                <div
                  key={gate.id}
                  className="bg-white border border-gray-100 rounded-lg px-4 py-3 flex items-center gap-3"
                >
                  <span className="text-sm text-gray-700 flex-1">
                    {gate.asset?.title || `Gate #${gate.id}`}
                  </span>
                  <span
                    className={`text-xs font-medium px-2 py-0.5 rounded-full capitalize ${
                      gate.status === 'approved'
                        ? 'bg-green-100 text-green-700'
                        : 'bg-red-100 text-red-700'
                    }`}
                  >
                    {gate.status}
                  </span>
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}
