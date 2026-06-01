import { useNavigate, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useClient, useBrandDNA, usePersonas } from '@/shared/hooks/useClient'
import { getSuggestions } from '@/api/brand-dna'
import { Card, CardBody, CardHeader } from '@/shared/components/Card'
import { Button } from '@/shared/components/Button'
import { BrandDNABadge } from '@/shared/components/BrandDNABadge'
import { SuggestionCard } from '@/shared/components/SuggestionCard'
import { PageLoader } from '@/shared/components/LoadingSpinner'
import { Badge } from '@/shared/components/Badge'
import { ArrowLeft, ArrowUpRight, Megaphone, BarChart2, Globe, Dna, RefreshCw, Sparkles, FileBarChart } from 'lucide-react'
import { CompletenessRing } from '@/shared/components/CompletenessRing'
import { getBrandDNAScore } from '@/lib/brand-dna-score'

export function ClientHub() {
  const { clientId } = useParams<{ clientId: string }>()
  const navigate = useNavigate()
  const id = clientId!

  const { data: client, isLoading } = useClient(id)
  const { data: brandDna } = useBrandDNA(id)
  const { data: personas } = usePersonas(id)
  const { data: suggestionsData, isLoading: suggestionsLoading, refetch: refetchSuggestions } = useQuery({
    queryKey: ['suggestions', id],
    queryFn: () => getSuggestions(id),
    enabled: !!id,
    staleTime: 60_000,
  })

  if (isLoading) return <PageLoader />
  if (!client) return <div className="p-8 text-sm text-red-600">Client not found</div>

  const { score: dnaScore, details: dnaDetails } = getBrandDNAScore(client, brandDna, personas?.length ?? 0)
  const missingRequired = dnaDetails.filter(d => d.required && !d.done)

  const services = [
    {
      key: 'campaigns',
      label: 'Social Campaigns',
      icon: Megaphone,
      color: 'bg-purple-50 text-purple-600',
      path: `/clients/${id}/campaigns`,
    },
    {
      key: 'ads',
      label: 'Google Ads',
      icon: BarChart2,
      color: 'bg-blue-50 text-blue-600',
      path: `/clients/${id}/ads`,
    },
    {
      key: 'webdev',
      label: 'Websites',
      icon: Globe,
      color: 'bg-emerald-50 text-emerald-600',
      path: `/clients/${id}/webdev`,
    },
    {
      key: 'reports',
      label: 'Reports',
      icon: FileBarChart,
      color: 'bg-slate-100 text-slate-600',
      path: `/clients/${id}/reports`,
    },
  ]

  return (
    <div className="p-4 md:p-8">
      {/* Back nav */}
      <button
        onClick={() => navigate('/clients')}
        className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 mb-5 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        All Clients
      </button>

      {/* Client header */}
      <div className="flex flex-wrap items-start justify-between gap-3 mb-6">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-10 h-10 md:w-12 md:h-12 rounded-xl bg-brand-100 flex items-center justify-center flex-shrink-0">
            <span className="text-brand-700 font-bold text-base md:text-lg">{client.name.charAt(0)}</span>
          </div>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-xl md:text-2xl font-bold text-slate-900 truncate">{client.name}</h1>
              {!client.is_active && <Badge variant="warning">Inactive</Badge>}
            </div>
            <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 mt-1 text-xs md:text-sm text-slate-500">
              {client.industry && <span className="capitalize">{client.industry.replace(/_/g, ' ')}</span>}
              {client.location && <span>· {client.location}</span>}
              {client.website_url && (
                <a
                  href={client.website_url}
                  target="_blank"
                  rel="noreferrer"
                  className="hover:text-brand-600 flex items-center gap-0.5 truncate max-w-[200px]"
                  onClick={e => e.stopPropagation()}
                >
                  · {client.website_url.replace(/^https?:\/\//, '')}
                  <ArrowUpRight className="w-3 h-3 flex-shrink-0" />
                </a>
              )}
            </div>
          </div>
        </div>
        <Button variant="secondary" size="sm" onClick={() => navigate(`/clients/${id}/brand-dna`)}>
          Edit Client
        </Button>
      </div>

      {/* Main grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Left column: Brand DNA + services */}
        <div className="lg:col-span-2 space-y-5">
          {/* Brand DNA card */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Dna className="w-4 h-4 text-slate-400" />
                  <h2 className="text-sm font-semibold text-slate-700">Brand DNA</h2>
                </div>
                <div className="flex items-center gap-2">
                  {brandDna && <CompletenessRing score={dnaScore} size={36} strokeWidth={3} />}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => navigate(client.has_brand_dna ? `/clients/${id}/brand-dna` : `/clients/${id}/brand-dna/setup`)}
                  >
                    {client.has_brand_dna ? 'Edit' : 'Set Up'}
                    <ArrowUpRight className="w-3.5 h-3.5" />
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardBody>
              {brandDna ? (
                <div className="space-y-3">
                  <BrandDNABadge brandDna={brandDna} personaCount={personas?.length ?? 0} />
                  {brandDna.tagline && (
                    <p className="text-sm text-slate-600 italic">"{brandDna.tagline}"</p>
                  )}
                  {brandDna.usps && brandDna.usps.length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-slate-500 mb-1.5">USPs</p>
                      <div className="flex flex-wrap gap-1.5">
                        {brandDna.usps.slice(0, 4).map(usp => (
                          <span key={usp} className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded-md">{usp}</span>
                        ))}
                        {brandDna.usps.length > 4 && (
                          <span className="text-xs text-slate-400">+{brandDna.usps.length - 4} more</span>
                        )}
                      </div>
                    </div>
                  )}
                  {/* Enhance nudge — shown when score < 70% */}
                  {dnaScore < 70 && missingRequired.length > 0 && (
                    <div className="mt-1 rounded-xl bg-amber-50 border border-amber-200 px-3 py-2.5">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <p className="text-xs font-semibold text-amber-800 mb-1">Complete your Brand DNA</p>
                          <p className="text-xs text-amber-700">
                            Still needed: {missingRequired.map(d => d.label).join(', ')}
                          </p>
                        </div>
                        <button
                          onClick={() => navigate(`/clients/${id}/brand-dna/wizard`)}
                          className="flex-shrink-0 flex items-center gap-1 text-xs font-semibold text-amber-700 hover:text-amber-900 transition-colors"
                        >
                          <Sparkles className="w-3 h-3" /> Enhance
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-4">
                  <p className="text-sm text-slate-500 mb-3">Brand DNA not set up yet.</p>
                  <Button size="sm" onClick={() => navigate(`/clients/${id}/brand-dna/setup`)}>
                    <Sparkles className="w-3.5 h-3.5" /> Set Up Brand DNA
                  </Button>
                </div>
              )}
            </CardBody>
          </Card>

          {/* Services */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {services.map(({ key, label, icon: Icon, color, path }) => (
              <Card
                key={key}
                className="hover:border-brand-200 hover:shadow-md transition-all cursor-pointer"
                onClick={() => navigate(path)}
              >
                <CardBody className="py-5">
                  <div className={`w-9 h-9 rounded-xl ${color} flex items-center justify-center mb-3`}>
                    <Icon className="w-4.5 h-4.5" />
                  </div>
                  <p className="text-sm font-semibold text-slate-800">{label}</p>
                  <p className="text-xs text-slate-400 mt-0.5">Open →</p>
                </CardBody>
              </Card>
            ))}
          </div>
        </div>

        {/* Right column: Director Suggestions */}
        <div>
          <Card className="h-full">
            <CardHeader>
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-semibold text-slate-700">Suggestions</h2>
                <button
                  onClick={() => refetchSuggestions()}
                  className="text-slate-400 hover:text-slate-600 transition-colors"
                  title="Refresh suggestions"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${suggestionsLoading ? 'animate-spin' : ''}`} />
                </button>
              </div>
            </CardHeader>
            <CardBody className="space-y-3">
              {suggestionsLoading && (
                <div className="py-4 text-center">
                  <p className="text-xs text-slate-400">Analysing client state…</p>
                </div>
              )}
              {suggestionsData?.suggestions.length === 0 && (
                <p className="text-xs text-slate-400 py-4 text-center">No suggestions right now — all good!</p>
              )}
              {suggestionsData?.suggestions.map(s => (
                <SuggestionCard key={s.id} suggestion={s} />
              ))}
            </CardBody>
          </Card>
        </div>
      </div>
    </div>
  )
}
