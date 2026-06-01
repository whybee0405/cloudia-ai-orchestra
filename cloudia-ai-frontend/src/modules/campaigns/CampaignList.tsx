import { useQuery } from '@tanstack/react-query'
import { useNavigate, useParams } from 'react-router-dom'
import { Plus, Megaphone, Calendar, Clock } from 'lucide-react'
import { listCampaigns, type CampaignListItem } from '@/api/campaigns'
import { Card, CardBody } from '@/shared/components/Card'
import { Button } from '@/shared/components/Button'
import { Badge } from '@/shared/components/Badge'
import { PageLoader } from '@/shared/components/LoadingSpinner'

const STATUS_BADGE: Record<string, 'default' | 'success' | 'warning' | 'danger' | 'info' | 'purple'> = {
  planned: 'default',
  active: 'success',
  running: 'info',
  paused: 'warning',
  halted: 'danger',
  completed: 'success',
}

const PLATFORM_COLORS: Record<string, string> = {
  instagram: 'bg-purple-100 text-purple-700',
  facebook: 'bg-blue-100 text-blue-700',
  twitter: 'bg-slate-100 text-slate-700',
  x: 'bg-slate-100 text-slate-700',
  linkedin: 'bg-sky-100 text-sky-700',
  tiktok: 'bg-pink-100 text-pink-700',
  youtube: 'bg-red-100 text-red-700',
}

function PlatformChip({ platform }: { platform: string }) {
  const lower = platform.toLowerCase()
  return (
    <span className={`text-xs px-2 py-0.5 rounded-md font-medium capitalize ${PLATFORM_COLORS[lower] ?? 'bg-slate-100 text-slate-600'}`}>
      {platform}
    </span>
  )
}

function CampaignCard({ campaign }: { campaign: CampaignListItem }) {
  const { clientId } = useParams<{ clientId: string }>()
  const navigate = useNavigate()
  const status = campaign.status ?? 'planned'

  return (
    <Card
      className="hover:border-purple-200 hover:shadow-md transition-all cursor-pointer"
      onClick={() => navigate(`/clients/${clientId}/campaigns/${campaign.id}`)}
    >
      <CardBody className="space-y-3">
        <div className="flex items-start justify-between gap-2">
          <h3 className="text-sm font-semibold text-slate-800 leading-snug">{campaign.name}</h3>
          <Badge variant={STATUS_BADGE[status] ?? 'default'} className="shrink-0">
            {status}
          </Badge>
        </div>

        {campaign.goal && (
          <p className="text-xs text-slate-500 line-clamp-2">{campaign.goal}</p>
        )}

        {campaign.platforms?.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {campaign.platforms.map(p => <PlatformChip key={p} platform={p} />)}
          </div>
        )}

        <div className="flex items-center gap-3 text-xs text-slate-400">
          {campaign.start_date && (
            <span className="flex items-center gap-1">
              <Calendar className="w-3 h-3" />
              {new Date(campaign.start_date).toLocaleDateString('en-ZA', { day: 'numeric', month: 'short' })}
            </span>
          )}
          {campaign.created_at && (
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {new Date(campaign.created_at).toLocaleDateString('en-ZA', { day: 'numeric', month: 'short', year: 'numeric' })}
            </span>
          )}
        </div>
      </CardBody>
    </Card>
  )
}

export function CampaignList({ directorClientId }: { directorClientId: number }) {
  const { clientId } = useParams<{ clientId: string }>()
  const navigate = useNavigate()

  const { data: campaigns, isLoading, error } = useQuery({
    queryKey: ['campaigns', directorClientId],
    queryFn: () => listCampaigns(directorClientId),
  })

  if (isLoading) return <PageLoader />

  return (
    <div className="p-4 md:p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl md:text-2xl font-bold text-slate-900">Social Campaigns</h1>
          <p className="text-sm text-slate-500 mt-0.5">Multi-agent content pipeline</p>
        </div>
        <Button onClick={() => navigate(`/clients/${clientId}/campaigns/new`)}>
          <Plus className="w-4 h-4" />
          New Campaign
        </Button>
      </div>

      {error && (
        <p className="text-sm text-red-600 mb-4">Failed to load campaigns.</p>
      )}

      {campaigns?.length === 0 && (
        <Card>
          <CardBody className="py-16 text-center">
            <div className="w-12 h-12 rounded-xl bg-purple-100 flex items-center justify-center mx-auto mb-4">
              <Megaphone className="w-6 h-6 text-purple-600" />
            </div>
            <h2 className="text-sm font-semibold text-slate-700 mb-1">No campaigns yet</h2>
            <p className="text-sm text-slate-500 mb-4">Create your first campaign to get started.</p>
            <Button onClick={() => navigate(`/clients/${clientId}/campaigns/new`)}>
              <Plus className="w-4 h-4" />
              New Campaign
            </Button>
          </CardBody>
        </Card>
      )}

      {campaigns && campaigns.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
          {campaigns.map(c => <CampaignCard key={c.id} campaign={c} />)}
        </div>
      )}
    </div>
  )
}
