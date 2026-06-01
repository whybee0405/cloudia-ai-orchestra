import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { listClients } from '@/api/brand-dna'
import { Card } from '@/shared/components/Card'
import { Button } from '@/shared/components/Button'
import { Badge } from '@/shared/components/Badge'
import { BrandDNABadge } from '@/shared/components/BrandDNABadge'
import { PageLoader } from '@/shared/components/LoadingSpinner'
import { Plus, Building2, ArrowRight } from 'lucide-react'

export function ClientList() {
  const navigate = useNavigate()
  const { data: clients, isLoading, error } = useQuery({
    queryKey: ['clients'],
    queryFn: listClients,
  })

  return (
    <div className="p-4 md:p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl md:text-2xl font-bold text-slate-900">Clients</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            {clients?.length ?? 0} client{clients?.length !== 1 ? 's' : ''}
          </p>
        </div>
        <Button onClick={() => navigate('/clients/new')}>
          <Plus className="w-4 h-4" />
          New Client
        </Button>
      </div>

      {isLoading && <PageLoader />}

      {error && (
        <Card className="p-6 border-red-200 bg-red-50">
          <p className="text-sm text-red-700">Failed to load clients. Is the Brand DNA service running?</p>
        </Card>
      )}

      {clients?.length === 0 && (
        <div className="text-center py-20">
          <div className="w-12 h-12 rounded-xl bg-slate-100 flex items-center justify-center mx-auto mb-4">
            <Building2 className="w-6 h-6 text-slate-400" />
          </div>
          <h2 className="text-sm font-semibold text-slate-700 mb-1">No clients yet</h2>
          <p className="text-sm text-slate-500 mb-4">Add your first client to get started</p>
          <Button onClick={() => navigate('/clients/new')}>
            <Plus className="w-4 h-4" />
            Add Client
          </Button>
        </div>
      )}

      <div className="grid gap-3">
        {clients?.map(client => (
          <Card
            key={client.id}
            className="hover:border-brand-200 hover:shadow-md transition-all cursor-pointer"
            onClick={() => navigate(`/clients/${client.id}`)}
          >
            <div className="flex items-center gap-4 px-5 py-4">
              {/* Avatar */}
              <div className="w-10 h-10 rounded-xl bg-brand-100 flex items-center justify-center flex-shrink-0">
                <span className="text-brand-700 font-bold text-sm">
                  {client.name.charAt(0).toUpperCase()}
                </span>
              </div>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <h2 className="font-semibold text-slate-900 text-sm truncate">{client.name}</h2>
                  {!client.is_active && <Badge variant="warning">Inactive</Badge>}
                </div>
                <div className="flex items-center gap-3 text-xs text-slate-500">
                  {client.industry && <span className="capitalize">{client.industry.replace(/_/g, ' ')}</span>}
                  {client.location && <span>· {client.location}</span>}
                  {client.website_url && (
                    <span className="hidden sm:inline truncate max-w-[180px]">· {client.website_url.replace(/^https?:\/\//, '')}</span>
                  )}
                </div>
              </div>

              {/* Brand DNA status */}
              <div className="flex-shrink-0">
                <BrandDNABadge brandDna={client.has_brand_dna ? ({} as never) : null} personaCount={client.persona_count} compact />
              </div>

              <ArrowRight className="w-4 h-4 text-slate-300 flex-shrink-0" />
            </div>
          </Card>
        ))}
      </div>
    </div>
  )
}
