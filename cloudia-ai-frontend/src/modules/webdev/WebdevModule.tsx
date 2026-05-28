import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Globe } from 'lucide-react'
import { Button } from '@/shared/components/Button'
import { Card, CardBody } from '@/shared/components/Card'

export function WebdevModule() {
  const { clientId } = useParams<{ clientId: string }>()
  const navigate = useNavigate()

  return (
    <div className="p-8">
      <button onClick={() => navigate(`/clients/${clientId}`)} className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 mb-6">
        <ArrowLeft className="w-4 h-4" /> Back to Hub
      </button>
      <h1 className="text-2xl font-bold text-slate-900 mb-1">Websites</h1>
      <p className="text-sm text-slate-500 mb-6">WordPress & Shopify builder pipeline</p>
      <Card>
        <CardBody className="py-16 text-center">
          <div className="w-12 h-12 rounded-xl bg-emerald-100 flex items-center justify-center mx-auto mb-4">
            <Globe className="w-6 h-6 text-emerald-600" />
          </div>
          <h2 className="text-sm font-semibold text-slate-700 mb-1">WebDev Module</h2>
          <p className="text-sm text-slate-500 mb-4">Coming in Phase 6 — WebDev service module</p>
          <Button variant="secondary" size="sm" disabled>Coming soon</Button>
        </CardBody>
      </Card>
    </div>
  )
}
