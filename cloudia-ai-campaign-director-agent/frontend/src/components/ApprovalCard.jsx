import { useState } from 'react';
import { Check, X, RotateCcw } from 'lucide-react';
import { getAssetUrl } from '../api/assets';
import StatusBadge from './StatusBadge';
import PlatformBadge from './PlatformBadge';

export default function ApprovalCard({ gate, asset, onApprove, onReject, isLoading }) {
  const [caption, setCaption] = useState(asset?.caption || '');
  const [notes, setNotes] = useState('');

  const isImage = asset?.type === 'image' || asset?.content_type?.startsWith('image/');
  const isVideo = asset?.type === 'video' || asset?.content_type?.startsWith('video/');
  const fileUrl = asset?.id ? getAssetUrl(asset.id) : null;

  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 bg-gray-50">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-800">
            {asset?.title || `Gate #${gate?.id}`}
          </span>
          <StatusBadge status={gate?.status || asset?.status} />
        </div>
        <div className="flex gap-1">
          {asset?.platforms?.map((p) => <PlatformBadge key={p} platform={p} />)}
          {asset?.platform && !asset?.platforms && <PlatformBadge platform={asset.platform} />}
        </div>
      </div>

      <div className="flex flex-col md:flex-row">
        <div className="md:w-1/2 bg-gray-100 flex items-center justify-center min-h-40">
          {isImage && fileUrl ? (
            <img src={fileUrl} alt={asset.title} className="max-w-full max-h-64 object-contain" />
          ) : isVideo && fileUrl ? (
            <video src={fileUrl} controls className="max-w-full max-h-64" />
          ) : (
            <div className="text-gray-400 text-sm p-8 text-center">
              {asset?.type || 'Asset'} — no preview
            </div>
          )}
        </div>

        <div className="md:w-1/2 p-4 flex flex-col gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">
              Caption
            </label>
            <textarea
              value={caption}
              onChange={(e) => setCaption(e.target.value)}
              rows={4}
              className="w-full text-sm text-gray-800 border border-gray-200 rounded px-3 py-2 resize-none focus:outline-none focus:ring-1 focus:ring-blue-500"
              placeholder="Edit caption..."
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">
              Review Notes
            </label>
            <input
              type="text"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full text-sm border border-gray-200 rounded px-3 py-2 focus:outline-none focus:ring-1 focus:ring-blue-500"
              placeholder="Optional notes..."
            />
          </div>

          <div className="flex gap-2 pt-1">
            <button
              onClick={() => onApprove && onApprove(gate?.id, notes)}
              disabled={isLoading}
              className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 text-sm font-medium bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
            >
              <Check className="w-4 h-4" />
              Approve
            </button>
            <button
              onClick={() => onReject && onReject(gate?.id, notes)}
              disabled={isLoading}
              className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 text-sm font-medium bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
            >
              <X className="w-4 h-4" />
              Reject
            </button>
            <button
              onClick={() => onReject && onReject(gate?.id, 'Request revision: ' + notes)}
              disabled={isLoading}
              className="inline-flex items-center justify-center gap-1 px-3 py-2 text-sm font-medium border border-gray-300 text-gray-700 rounded hover:bg-gray-50 disabled:opacity-50"
              title="Request revision"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
