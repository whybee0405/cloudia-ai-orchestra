import { X, Download, ExternalLink } from 'lucide-react';
import { getAssetUrl } from '../api/assets';
import StatusBadge from './StatusBadge';
import PlatformBadge from './PlatformBadge';

export default function AssetPreview({ asset, onClose, actions }) {
  if (!asset) return null;

  const isImage = asset.type === 'image' || asset.content_type?.startsWith('image/');
  const isVideo = asset.type === 'video' || asset.content_type?.startsWith('video/');
  const fileUrl = asset.id ? getAssetUrl(asset.id) : null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-3xl mx-4 overflow-hidden flex flex-col max-h-[90vh]">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <div className="flex items-center gap-3">
            <h2 className="text-base font-semibold text-gray-900 truncate">
              {asset.title || `Asset #${asset.id}`}
            </h2>
            <StatusBadge status={asset.status} />
          </div>
          <button onClick={onClose} className="p-1 rounded hover:bg-gray-100">
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        <div className="flex-1 overflow-auto">
          <div className="bg-gray-50 flex items-center justify-center min-h-48 p-4">
            {isImage && fileUrl ? (
              <img
                src={fileUrl}
                alt={asset.title}
                className="max-w-full max-h-96 object-contain rounded"
              />
            ) : isVideo && fileUrl ? (
              <video
                src={fileUrl}
                controls
                className="max-w-full max-h-96 rounded"
              />
            ) : (
              <div className="text-gray-400 text-sm text-center py-8">
                No preview available for this asset type: {asset.type}
              </div>
            )}
          </div>

          <div className="p-5 space-y-4">
            {asset.caption && (
              <div>
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Caption</p>
                <p className="text-sm text-gray-800 whitespace-pre-wrap">{asset.caption}</p>
              </div>
            )}

            {(asset.platforms?.length > 0 || asset.platform) && (
              <div>
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Platforms</p>
                <div className="flex flex-wrap gap-1.5">
                  {asset.platforms?.map((p) => <PlatformBadge key={p} platform={p} />)}
                  {asset.platform && !asset.platforms && <PlatformBadge platform={asset.platform} />}
                </div>
              </div>
            )}

            {asset.hashtags && asset.hashtags.length > 0 && (
              <div>
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Hashtags</p>
                <p className="text-sm text-gray-600">{asset.hashtags.map((h) => `#${h}`).join(' ')}</p>
              </div>
            )}

            {asset.scheduled_at && (
              <div>
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Scheduled</p>
                <p className="text-sm text-gray-800">{new Date(asset.scheduled_at).toLocaleString()}</p>
              </div>
            )}
          </div>
        </div>

        {(actions || fileUrl) && (
          <div className="flex items-center gap-2 px-5 py-4 border-t border-gray-100 bg-gray-50">
            {fileUrl && (
              <a
                href={fileUrl}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-700 border border-gray-300 rounded hover:bg-gray-100"
              >
                <ExternalLink className="w-4 h-4" />
                Open
              </a>
            )}
            {actions}
          </div>
        )}
      </div>
    </div>
  );
}
