import { useState } from 'react';
import { Search, Filter } from 'lucide-react';
import { useAssets } from '../hooks/useAssets';
import AssetCard from '../components/AssetCard';
import AssetPreview from '../components/AssetPreview';

const STATUS_OPTIONS = ['all', 'draft', 'approved', 'published', 'rejected', 'pending_review'];
const TYPE_OPTIONS = ['all', 'image', 'video', 'text', 'carousel', 'reel', 'story'];
const PLATFORM_OPTIONS = ['all', 'instagram', 'facebook', 'twitter', 'linkedin', 'tiktok', 'youtube'];

export default function AssetLibrary() {
  const [filters, setFilters] = useState({ status: 'all', type: 'all', platform: 'all', search: '' });
  const [selectedAsset, setSelectedAsset] = useState(null);
  const [showFilters, setShowFilters] = useState(false);

  const queryFilters = {};
  if (filters.status !== 'all') queryFilters.status = filters.status;
  if (filters.type !== 'all') queryFilters.type = filters.type;
  if (filters.platform !== 'all') queryFilters.platform = filters.platform;

  const { data, isLoading } = useAssets(queryFilters);
  const assets = data?.assets || data || [];

  const filtered = assets.filter((a) => {
    if (!filters.search) return true;
    const q = filters.search.toLowerCase();
    return (
      a.title?.toLowerCase().includes(q) ||
      a.caption?.toLowerCase().includes(q) ||
      a.id?.toString().includes(q)
    );
  });

  const setFilter = (key, val) => setFilters((f) => ({ ...f, [key]: val }));

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Asset Library</h1>
          <p className="text-sm text-gray-500 mt-0.5">{filtered.length} assets</p>
        </div>
        <button
          onClick={() => setShowFilters(!showFilters)}
          className={`inline-flex items-center gap-1.5 px-3 py-2 text-sm border rounded hover:bg-gray-50 ${showFilters ? 'border-blue-400 text-blue-600' : 'border-gray-300 text-gray-700'}`}
        >
          <Filter className="w-4 h-4" />
          Filters
        </button>
      </div>

      <div className="flex items-center gap-2">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            value={filters.search}
            onChange={(e) => setFilter('search', e.target.value)}
            placeholder="Search assets..."
            className="w-full pl-9 pr-4 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
      </div>

      {showFilters && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Status</label>
            <select
              value={filters.status}
              onChange={(e) => setFilter('status', e.target.value)}
              className="w-full text-sm border border-gray-200 rounded px-3 py-2 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              {STATUS_OPTIONS.map((s) => (
                <option key={s} value={s}>{s === 'all' ? 'All Statuses' : s.replace(/_/g, ' ')}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Type</label>
            <select
              value={filters.type}
              onChange={(e) => setFilter('type', e.target.value)}
              className="w-full text-sm border border-gray-200 rounded px-3 py-2 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              {TYPE_OPTIONS.map((t) => (
                <option key={t} value={t}>{t === 'all' ? 'All Types' : t}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Platform</label>
            <select
              value={filters.platform}
              onChange={(e) => setFilter('platform', e.target.value)}
              className="w-full text-sm border border-gray-200 rounded px-3 py-2 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              {PLATFORM_OPTIONS.map((p) => (
                <option key={p} value={p}>{p === 'all' ? 'All Platforms' : p}</option>
              ))}
            </select>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="bg-white border border-gray-200 rounded-lg overflow-hidden animate-pulse">
              <div className="aspect-video bg-gray-200" />
              <div className="p-3 space-y-2">
                <div className="h-3 bg-gray-200 rounded w-2/3" />
                <div className="h-2 bg-gray-200 rounded w-1/3" />
              </div>
            </div>
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 border border-dashed border-gray-200 rounded-xl text-gray-400 text-sm">
          No assets found
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          {filtered.map((asset) => (
            <AssetCard key={asset.id} asset={asset} onClick={setSelectedAsset} />
          ))}
        </div>
      )}

      {selectedAsset && (
        <AssetPreview asset={selectedAsset} onClose={() => setSelectedAsset(null)} />
      )}
    </div>
  );
}
