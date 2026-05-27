import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Check, X } from 'lucide-react';
import { getCalendar, updateCalendarItem } from '../api/calendar';
import { approveGate, rejectGate } from '../api/approvals';
import CalendarView from '../components/CalendarView';
import AssetPreview from '../components/AssetPreview';
import StatusBadge from '../components/StatusBadge';

export default function ContentCalendar() {
  const queryClient = useQueryClient();
  const [calDate, setCalDate] = useState(new Date());
  const [selectedItem, setSelectedItem] = useState(null);

  const { data, isLoading } = useQuery({
    queryKey: ['calendar', {}],
    queryFn: () => getCalendar(),
    staleTime: 15000,
  });

  const items = data?.items || data || [];

  const reschedule = useMutation({
    mutationFn: ({ id, scheduled_at }) => updateCalendarItem(id, { scheduled_at }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['calendar'] }),
  });

  const approveMutation = useMutation({
    mutationFn: ({ gateId }) => approveGate(gateId, ''),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['calendar'] });
      setSelectedItem(null);
    },
  });

  const rejectMutation = useMutation({
    mutationFn: ({ gateId }) => rejectGate(gateId, ''),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['calendar'] });
      setSelectedItem(null);
    },
  });

  const handleDrop = (item, newDate) => {
    reschedule.mutate({ id: item.id, scheduled_at: newDate.toISOString() });
  };

  const handleSelect = (item) => {
    setSelectedItem(item);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Content Calendar</h1>
          <p className="text-sm text-gray-500 mt-0.5">{items.length} scheduled items</p>
        </div>
      </div>

      {isLoading ? (
        <div className="bg-white border border-gray-200 rounded-xl h-96 animate-pulse" />
      ) : (
        <div className="bg-white border border-gray-200 rounded-xl p-4" style={{ height: 680 }}>
          <CalendarView
            events={items}
            onSelectEvent={handleSelect}
            onEventDrop={handleDrop}
            onNavigate={setCalDate}
            date={calDate}
          />
        </div>
      )}

      {selectedItem && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
          onClick={(e) => e.target === e.currentTarget && setSelectedItem(null)}
        >
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden">
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
              <div>
                <h2 className="text-base font-semibold text-gray-900">
                  {selectedItem.title || selectedItem.asset?.title || `Post #${selectedItem.id}`}
                </h2>
                {selectedItem.scheduled_at && (
                  <p className="text-xs text-gray-400 mt-0.5">
                    {new Date(selectedItem.scheduled_at).toLocaleString()}
                  </p>
                )}
              </div>
              <StatusBadge status={selectedItem.status || selectedItem.asset?.status} />
            </div>

            <div className="p-5">
              {selectedItem.asset && (
                <div>
                  {(selectedItem.asset.type === 'image') && (
                    <img
                      src={`${import.meta.env.VITE_API_URL || 'http://localhost:8001'}/api/assets/${selectedItem.asset.id}/file`}
                      alt={selectedItem.asset.title}
                      className="w-full max-h-64 object-contain rounded bg-gray-50 mb-4"
                      onError={(e) => (e.target.style.display = 'none')}
                    />
                  )}
                  {selectedItem.asset.caption && (
                    <p className="text-sm text-gray-700 mb-4">{selectedItem.asset.caption}</p>
                  )}
                </div>
              )}

              <div className="flex gap-3">
                {selectedItem.gate_id && (
                  <>
                    <button
                      onClick={() => approveMutation.mutate({ gateId: selectedItem.gate_id })}
                      disabled={approveMutation.isPending}
                      className="flex-1 inline-flex items-center justify-center gap-1.5 px-4 py-2 text-sm font-medium bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
                    >
                      <Check className="w-4 h-4" />
                      Approve
                    </button>
                    <button
                      onClick={() => rejectMutation.mutate({ gateId: selectedItem.gate_id })}
                      disabled={rejectMutation.isPending}
                      className="flex-1 inline-flex items-center justify-center gap-1.5 px-4 py-2 text-sm font-medium bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
                    >
                      <X className="w-4 h-4" />
                      Reject
                    </button>
                  </>
                )}
                <button
                  onClick={() => setSelectedItem(null)}
                  className="px-4 py-2 text-sm border border-gray-300 text-gray-700 rounded hover:bg-gray-50"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
