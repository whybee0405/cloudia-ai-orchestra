import { Image, Video, FileText, Music } from 'lucide-react';
import StatusBadge from './StatusBadge';
import PlatformBadge from './PlatformBadge';
import { getAssetUrl } from '../api/assets';

function TypeIcon({ type }) {
  if (type === 'video') return <Video className="w-4 h-4" />;
  if (type === 'text' || type === 'caption') return <FileText className="w-4 h-4" />;
  if (type === 'audio') return <Music className="w-4 h-4" />;
  return <Image className="w-4 h-4" />;
}

export default function AssetCard({ asset, onClick }) {
  const isImage = asset.type === 'image' || asset.content_type?.startsWith('image/');
  const isVideo = asset.type === 'video' || asset.content_type?.startsWith('video/');
  const fileUrl = asset.id ? getAssetUrl(asset.id) : null;

  return (
    <div
      className="bg-white border border-gray-200 rounded-lg overflow-hidden cursor-pointer hover:border-blue-400 hover:shadow-md transition-all"
      onClick={() => onClick && onClick(asset)}
    >
      <div className="aspect-video bg-gray-100 flex items-center justify-center relative">
        {isImage && fileUrl ? (
          <img
            src={fileUrl}
            alt={asset.title || 'Asset'}
            className="w-full h-full object-cover"
            onError={(e) => {
              e.target.style.display = 'none';
            }}
          />
        ) : isVideo && fileUrl ? (
          <video
            src={fileUrl}
            className="w-full h-full object-cover"
            muted
            playsInline
          />
        ) : (
          <div className="flex flex-col items-center gap-1 text-gray-400">
            <TypeIcon type={asset.type} />
            <span className="text-xs capitalize">{asset.type || 'asset'}</span>
          </div>
        )}
        <div className="absolute top-1 right-1">
          <StatusBadge status={asset.status} />
        </div>
      </div>
      <div className="p-3">
        <p className="text-sm font-medium text-gray-900 truncate">{asset.title || `Asset #${asset.id}`}</p>
        <div className="flex flex-wrap gap-1 mt-1.5">
          {asset.platforms?.map((p) => (
            <PlatformBadge key={p} platform={p} />
          ))}
          {asset.platform && !asset.platforms && <PlatformBadge platform={asset.platform} />}
        </div>
        {asset.created_at && (
          <p className="text-xs text-gray-400 mt-1.5">
            {new Date(asset.created_at).toLocaleDateString()}
          </p>
        )}
      </div>
    </div>
  );
}
