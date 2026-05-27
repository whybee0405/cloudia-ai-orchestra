import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Save, Loader, Check } from 'lucide-react';
import { api } from '../api/client';
import BrandGuidelinesEditor from '../components/BrandGuidelinesEditor';

export default function BrandGuidelines() {
  const { clientId } = useParams();
  const queryClient = useQueryClient();
  const [guidelines, setGuidelines] = useState(null);
  const [saved, setSaved] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ['brand-guidelines', clientId],
    queryFn: () =>
      api.get(`/clients/${clientId}/brand-guidelines`).then((r) => r.data),
    staleTime: 60000,
    onSuccess: (d) => {
      if (!guidelines) setGuidelines(d?.guidelines || d || {});
    },
  });

  const initialData = guidelines || data?.guidelines || data || {};

  const saveMutation = useMutation({
    mutationFn: (data) =>
      api.put(`/clients/${clientId}/brand-guidelines`, data).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['brand-guidelines', clientId] });
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    },
  });

  if (isLoading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-6 bg-gray-200 rounded w-1/3" />
        <div className="h-64 bg-gray-200 rounded" />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Brand Guidelines</h1>
          <p className="text-sm text-gray-500 mt-0.5">Client ID: {clientId}</p>
        </div>
        <button
          onClick={() => guidelines && saveMutation.mutate(guidelines)}
          disabled={saveMutation.isPending || !guidelines}
          className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {saveMutation.isPending ? (
            <Loader className="w-4 h-4 animate-spin" />
          ) : saved ? (
            <Check className="w-4 h-4" />
          ) : (
            <Save className="w-4 h-4" />
          )}
          {saveMutation.isPending ? 'Saving...' : saved ? 'Saved!' : 'Save Guidelines'}
        </button>
      </div>

      {saveMutation.isError && (
        <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded">
          {saveMutation.error?.response?.data?.detail || 'Failed to save guidelines'}
        </p>
      )}

      <div className="bg-white border border-gray-200 rounded-xl p-6">
        <BrandGuidelinesEditor
          initialData={initialData}
          onChange={setGuidelines}
        />
      </div>
    </div>
  );
}
