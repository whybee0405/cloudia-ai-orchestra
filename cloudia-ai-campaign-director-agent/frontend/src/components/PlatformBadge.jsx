const PLATFORM_STYLES = {
  instagram: { bg: 'bg-pink-100', text: 'text-pink-700', label: 'Instagram' },
  facebook: { bg: 'bg-blue-100', text: 'text-blue-700', label: 'Facebook' },
  twitter: { bg: 'bg-sky-100', text: 'text-sky-700', label: 'Twitter/X' },
  x: { bg: 'bg-sky-100', text: 'text-sky-700', label: 'X' },
  linkedin: { bg: 'bg-blue-200', text: 'text-blue-800', label: 'LinkedIn' },
  tiktok: { bg: 'bg-slate-100', text: 'text-slate-700', label: 'TikTok' },
  youtube: { bg: 'bg-red-100', text: 'text-red-700', label: 'YouTube' },
  pinterest: { bg: 'bg-rose-100', text: 'text-rose-700', label: 'Pinterest' },
};

export default function PlatformBadge({ platform, className = '' }) {
  const style = PLATFORM_STYLES[platform?.toLowerCase()] || {
    bg: 'bg-gray-100',
    text: 'text-gray-600',
    label: platform,
  };
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${style.bg} ${style.text} ${className}`}
    >
      {style.label}
    </span>
  );
}
