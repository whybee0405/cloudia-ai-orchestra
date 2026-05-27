import { useQuery, useQueryClient } from '@tanstack/react-query';
import { CheckCircle, AlertCircle, Clock } from 'lucide-react';
import { api } from '../api/client';
import OAuthConnectButton from '../components/OAuthConnectButton';

const PLATFORMS = [
  { id: 'instagram', label: 'Instagram', emoji: '📸' },
  { id: 'facebook', label: 'Facebook', emoji: '👤' },
  { id: 'twitter', label: 'Twitter/X', emoji: '🐦' },
  { id: 'linkedin', label: 'LinkedIn', emoji: '💼' },
  { id: 'tiktok', label: 'TikTok', emoji: '🎵' },
  { id: 'youtube', label: 'YouTube', emoji: '▶' },
  { id: 'pinterest', label: 'Pinterest', emoji: '📌' },
];

function PlatformRow({ platform, connection, clientId, onConnected }) {
  const isConnected = !!connection;
  const expiry = connection?.expires_at ? new Date(connection.expires_at) : null;
  const isExpired = expiry && expiry < new Date();
  const expiresInDays = expiry
    ? Math.ceil((expiry - new Date()) / (1000 * 60 * 60 * 24))
    : null;

  return (
    <div className="flex items-center justify-between py-3 px-4 border-b border-gray-100 last:border-0">
      <div className="flex items-center gap-3">
        <span className="text-xl">{platform.emoji}</span>
        <div>
          <p className="text-sm font-medium text-gray-800">{platform.label}</p>
          {isConnected && connection.account_name && (
            <p className="text-xs text-gray-500">@{connection.account_name}</p>
          )}
        </div>
      </div>

      <div className="flex items-center gap-3">
        {isConnected ? (
          <>
            <div className="flex items-center gap-1.5">
              {isExpired ? (
                <>
                  <AlertCircle className="w-4 h-4 text-red-500" />
                  <span className="text-xs text-red-600">Token expired</span>
                </>
              ) : expiresInDays != null && expiresInDays <= 7 ? (
                <>
                  <Clock className="w-4 h-4 text-yellow-500" />
                  <span className="text-xs text-yellow-600">Expires in {expiresInDays}d</span>
                </>
              ) : (
                <>
                  <CheckCircle className="w-4 h-4 text-green-500" />
                  <span className="text-xs text-green-600">Connected</span>
                </>
              )}
            </div>
            {(isExpired || (expiresInDays != null && expiresInDays <= 7)) && (
              <OAuthConnectButton
                platform={platform.id}
                clientId={clientId}
                onConnected={onConnected}
              />
            )}
          </>
        ) : (
          <OAuthConnectButton
            platform={platform.id}
            clientId={clientId}
            onConnected={onConnected}
          />
        )}
      </div>
    </div>
  );
}

function ClientSection({ client }) {
  const queryClient = useQueryClient();

  const { data } = useQuery({
    queryKey: ['platform-accounts', client.id],
    queryFn: () =>
      api.get(`/clients/${client.id}/accounts`).then((r) => r.data),
    staleTime: 30000,
  });

  const connections = data?.accounts || data || [];

  const getConnection = (platformId) =>
    connections.find((c) => c.platform === platformId);

  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-100 bg-gray-50">
        <h2 className="text-sm font-semibold text-gray-800">{client.name}</h2>
        <p className="text-xs text-gray-500 mt-0.5">
          {connections.filter((c) => c.connected).length} / {PLATFORMS.length} platforms connected
        </p>
      </div>
      <div>
        {PLATFORMS.map((platform) => (
          <PlatformRow
            key={platform.id}
            platform={platform}
            connection={getConnection(platform.id)}
            clientId={client.id}
            onConnected={() => queryClient.invalidateQueries({ queryKey: ['platform-accounts', client.id] })}
          />
        ))}
      </div>
    </div>
  );
}

export default function PlatformAccounts() {
  const { data, isLoading } = useQuery({
    queryKey: ['clients'],
    queryFn: () => api.get('/clients').then((r) => r.data),
    staleTime: 60000,
  });

  const clients = data?.clients || data || [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-gray-900">Platform Accounts</h1>
        <p className="text-sm text-gray-500 mt-0.5">OAuth connections per client</p>
      </div>

      {isLoading ? (
        <div className="space-y-4">
          {[1, 2].map((i) => (
            <div key={i} className="bg-white border border-gray-200 rounded-xl h-48 animate-pulse" />
          ))}
        </div>
      ) : clients.length === 0 ? (
        <div className="text-center py-16 border border-dashed border-gray-200 rounded-xl text-gray-400 text-sm">
          No clients yet. Create a campaign to add a client.
        </div>
      ) : (
        <div className="space-y-5">
          {clients.map((client) => (
            <ClientSection key={client.id} client={client} />
          ))}
        </div>
      )}
    </div>
  );
}
