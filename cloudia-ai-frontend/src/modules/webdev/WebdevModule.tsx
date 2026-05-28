import { useState } from 'react'
import { useParams, useNavigate, Routes, Route } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Code2, Globe, ArrowLeft } from 'lucide-react'
import { getClientByBrandDna, createClient } from '@/api/webdev'
import { useClient } from '@/shared/hooks/useClient'
import { Card, CardBody } from '@/shared/components/Card'
import { Button } from '@/shared/components/Button'
import { PageLoader } from '@/shared/components/LoadingSpinner'
import { ProjectList } from './ProjectList'
import { ProjectDetail } from './ProjectDetail'
import { NewProjectForm } from './NewProjectForm'

function NotConnected({
  brandDnaClientId,
  clientName,
  clientIndustry,
}: {
  brandDnaClientId: string
  clientName: string
  clientIndustry?: string
}) {
  const { clientId } = useParams<{ clientId: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [error, setError] = useState('')

  const { mutate, isPending } = useMutation({
    mutationFn: () =>
      createClient({
        name: clientName,
        industry: clientIndustry,
        brand_dna_client_id: brandDnaClientId,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['webdev-client', brandDnaClientId] }),
    onError: (err: Error) => setError(err.message),
  })

  return (
    <div className="p-8">
      <button
        onClick={() => navigate(`/clients/${clientId}`)}
        className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 mb-6"
      >
        <ArrowLeft className="w-4 h-4" /> Back to Hub
      </button>
      <div className="max-w-md">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-purple-100 flex items-center justify-center">
            <Code2 className="w-5 h-5 text-purple-600" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-900">WebDev Agent</h1>
            <p className="text-sm text-slate-500">AI-powered website building for <strong>{clientName}</strong></p>
          </div>
        </div>

        <Card>
          <CardBody className="space-y-4 text-center py-8">
            <Globe className="w-10 h-10 text-slate-300 mx-auto" />
            <div>
              <p className="text-sm font-medium text-slate-700">No WebDev workspace yet</p>
              <p className="text-xs text-slate-500 mt-1">
                Create a workspace to start building WordPress and Shopify sites with AI agents.
              </p>
            </div>
            {error && <p className="text-sm text-red-600">{error}</p>}
            <Button onClick={() => mutate()} loading={isPending}>
              Create Workspace
            </Button>
          </CardBody>
        </Card>
      </div>
    </div>
  )
}

function WebdevWorkspace({ webdevClientId }: { webdevClientId: number }) {
  return (
    <Routes>
      <Route index element={<ProjectList webdevClientId={webdevClientId} />} />
      <Route path="new" element={<NewProjectForm webdevClientId={webdevClientId} />} />
      <Route path=":projectId" element={<ProjectDetail />} />
    </Routes>
  )
}

export function WebdevModule() {
  const { clientId } = useParams<{ clientId: string }>()
  const id = clientId!

  const { data: brandDnaClient, isLoading: clientLoading } = useClient(id)

  const { data: webdevClient, isLoading: webdevLoading, error: webdevError } = useQuery({
    queryKey: ['webdev-client', id],
    queryFn: () => getClientByBrandDna(id),
    retry: false,
    enabled: !!id,
  })

  if (clientLoading || webdevLoading) return <PageLoader />

  const is404 = webdevError instanceof Error && webdevError.message.startsWith('404')

  if (is404 || !webdevClient) {
    return (
      <NotConnected
        brandDnaClientId={id}
        clientName={brandDnaClient?.name ?? 'This client'}
        clientIndustry={brandDnaClient?.industry ?? undefined}
      />
    )
  }

  return <WebdevWorkspace webdevClientId={webdevClient.id} />
}
