import { useState } from 'react';
import { ExternalLink, Loader } from 'lucide-react';
import { api } from '../api/client';

export default function OAuthConnectButton({ platform, clientId, onConnected }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleConnect = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get(`/oauth/${platform}/auth-url`, {
        params: { client_id: clientId },
      });
      const url = res.data?.url || res.data?.auth_url;
      if (url) {
        window.open(url, '_blank', 'noopener,noreferrer');
        onConnected && onConnected(platform);
      } else {
        setError('No OAuth URL returned');
      }
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to get OAuth URL');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <button
        onClick={handleConnect}
        disabled={loading}
        className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
      >
        {loading ? (
          <Loader className="w-4 h-4 animate-spin" />
        ) : (
          <ExternalLink className="w-4 h-4" />
        )}
        {loading ? 'Loading...' : 'Connect'}
      </button>
      {error && <p className="text-xs text-red-600 mt-1">{error}</p>}
    </div>
  );
}
