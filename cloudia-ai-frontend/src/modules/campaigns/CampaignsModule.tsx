import { useParams, useNavigate, Routes, Route } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Megaphone, Link2 } from 'lucide-react'
import { getDirectorClientByBrandDna, createDirectorClient } from '@/api/campaigns'
import { useClient } from '@/shared/hooks/useClient'
import { Card, CardBody } from '@/shared/components/Card'
import { Button } from '@/shared/components/Button'
import { PageLoader } from '@/shared/components/LoadingSpinner'
import { CampaignList } from './CampaignList'
import { CampaignDetail } from './CampaignDetail'
import { NewCampaignForm } from './NewCampaignForm'

function NotConnected({ brandDnaClientId, clientName, clientIndustry }: {
  brandDnaClientId: string
  clientName: string
  clientIndustry?: string
}) {
  const qc = useQueryClient()
  const navigate = useNavigate()
  const { clientId } = useParams<{ clientId: string }>()

  const { mutate: connect, isPending, error } = useMutation({
    mutationFn: () =>
      createDirectorClient({
        name: clientName,
        industry: clientIndustry ?? undefined,
        brand_dna_client_id: brandDnaClientId,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['director-client', brandDnaClientId] })
    },
  })

  return (
    <div className="p-8">
      <button
        onClick={() => navigate(`/clients/${clientId}`)}
        className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 mb-6"
      >
        <ArrowLeft className="w-4 h-4" /> Back to Hub
      </button>
      <Card className="max-w-md">
        <CardBody className="py-12 text-center">
          <div className="w-12 h-12 rounded-xl bg-purple-100 flex items-center justify-center mx-auto mb-4">
            <Megaphone className="w-6 h-6 text-purple-600" />
          </div>
          <h2 className="text-base font-semibold text-slate-800 mb-2">Social Campaigns</h2>
          <p className="text-sm text-slate-500 mb-6">
            Connect <strong>{clientName}</strong> to the Campaign Director to start managing social media campaigns.
          </p>
          {error && (
            <p className="text-sm text-red-600 mb-4">{(error as Error).message}</p>
          )}
          <Button onClick={() => connect()} loading={isPending}>
            <Link2 className="w-4 h-4" />
            Connect to Campaign Director
          </Button>
        </CardBody>
      </Card>
    </div>
  )
}

function CampaignsRoutes({ directorClientId }: { directorClientId: number }) {
  return (
    <Routes>
      <Route index element={<CampaignList directorClientId={directorClientId} />} />
      <Route path="new" element={<NewCampaignForm directorClientId={directorClientId} />} />
      <Route path=":campaignId" element={<CampaignDetailRoute />} />
    </Routes>
  )
}

function CampaignDetailRoute() {
  const { campaignId } = useParams<{ campaignId: string }>()
  return <CampaignDetail campaignId={parseInt(campaignId!)} />
}

export function CampaignsModule() {
  const { clientId } = useParams<{ clientId: string }>()
  const id = clientId!

  const { data: brandDnaClient, isLoading: clientLoading } = useClient(id)

  const { data: directorClient, isLoading: directorLoading, error: directorError } = useQuery({
    queryKey: ['director-client', id],
    queryFn: () => getDirectorClientByBrandDna(id),
    retry: false,
    enabled: !!id,
  })

  if (clientLoading || directorLoading) return <PageLoader />

  const is404 = directorError instanceof Error && directorError.message.startsWith('404')

  if (is404 || !directorClient) {
    return (
      <NotConnected
        brandDnaClientId={id}
        clientName={brandDnaClient?.name ?? 'This client'}
        clientIndustry={brandDnaClient?.industry ?? undefined}
      />
    )
  }

  return <CampaignsRoutes directorClientId={directorClient.id} />
}
