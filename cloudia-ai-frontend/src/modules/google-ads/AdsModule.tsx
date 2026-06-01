import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, BarChart2, Link2, LayoutDashboard, CheckSquare, AlertCircle } from 'lucide-react'
import {
  getAccountByBrandDna,
  createAdsAccount,
  type AdsAccount,
  type AdsAccountCreate,
} from '@/api/google-ads'
import { useClient } from '@/shared/hooks/useClient'
import { Card, CardBody, CardHeader } from '@/shared/components/Card'
import { Button } from '@/shared/components/Button'
import { Input } from '@/shared/components/Input'
import { PageLoader } from '@/shared/components/LoadingSpinner'
import { AccountOverview } from './AccountOverview'
import { ApprovalQueue } from './ApprovalQueue'
import { AuditLog } from './AuditLog'

type Tab = 'overview' | 'queue' | 'audit'

const TABS: { key: Tab; label: string; icon: typeof LayoutDashboard }[] = [
  { key: 'overview', label: 'Overview', icon: LayoutDashboard },
  { key: 'queue', label: 'Approval Queue', icon: CheckSquare },
  { key: 'audit', label: 'Audit Log', icon: AlertCircle },
]

const SENSITIVITIES = ['conservative', 'moderate', 'aggressive']
const KPIS = ['roas', 'cpa', 'ctr', 'cvr', 'clicks', 'impressions']

interface ConnectFormState {
  customer_id: string
  mcc_id: string
  budget_sensitivity: string
  monthly_ad_spend: string
  primary_kpi: string
  primary_kpi_target: string
}

function ConnectAccount({
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
  const [form, setForm] = useState<ConnectFormState>({
    customer_id: '',
    mcc_id: '',
    budget_sensitivity: 'moderate',
    monthly_ad_spend: '',
    primary_kpi: 'roas',
    primary_kpi_target: '',
  })
  const [error, setError] = useState('')

  const set = (k: keyof ConnectFormState) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
      setForm(f => ({ ...f, [k]: e.target.value }))

  const { mutate, isPending } = useMutation({
    mutationFn: (payload: AdsAccountCreate) => createAdsAccount(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ads-account', brandDnaClientId] }),
    onError: (err: Error) => setError(err.message),
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    if (!form.customer_id.trim()) { setError('Customer ID is required.'); return }
    if (!form.mcc_id.trim()) { setError('MCC ID is required.'); return }
    mutate({
      client_name: clientName,
      customer_id: form.customer_id.trim(),
      mcc_id: form.mcc_id.trim(),
      industry: clientIndustry,
      budget_sensitivity: form.budget_sensitivity,
      monthly_ad_spend: form.monthly_ad_spend ? parseFloat(form.monthly_ad_spend) : undefined,
      primary_kpi: form.primary_kpi || undefined,
      primary_kpi_target: form.primary_kpi_target ? parseFloat(form.primary_kpi_target) : undefined,
      brand_dna_client_id: brandDnaClientId,
    })
  }

  return (
    <div className="p-4 md:p-8">
      <button
        onClick={() => navigate(`/clients/${clientId}`)}
        className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 mb-6"
      >
        <ArrowLeft className="w-4 h-4" /> Back to Hub
      </button>
      <div className="max-w-lg">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-blue-100 flex items-center justify-center">
            <BarChart2 className="w-5 h-5 text-blue-600" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-900">Connect Google Ads</h1>
            <p className="text-sm text-slate-500">Link a Google Ads account for <strong>{clientName}</strong></p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <Card>
            <CardHeader><h2 className="text-sm font-semibold text-slate-700">Google Ads IDs</h2></CardHeader>
            <CardBody className="space-y-4">
              <Input
                label="Customer ID *"
                placeholder="123-456-7890"
                value={form.customer_id}
                onChange={set('customer_id')}
                hint="Found in the top-right of your Google Ads dashboard"
              />
              <Input
                label="MCC Manager ID *"
                placeholder="987-654-3210"
                value={form.mcc_id}
                onChange={set('mcc_id')}
                hint="Your agency's manager account ID"
              />
            </CardBody>
          </Card>

          <Card>
            <CardHeader><h2 className="text-sm font-semibold text-slate-700">Budget & KPIs</h2></CardHeader>
            <CardBody className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Budget sensitivity</label>
                <select
                  className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-500 capitalize"
                  value={form.budget_sensitivity}
                  onChange={set('budget_sensitivity')}
                >
                  {SENSITIVITIES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <Input
                label="Monthly ad spend (ZAR)"
                type="number"
                min={0}
                placeholder="15000"
                value={form.monthly_ad_spend}
                onChange={set('monthly_ad_spend')}
              />
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">Primary KPI</label>
                  <select
                    className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-500"
                    value={form.primary_kpi}
                    onChange={set('primary_kpi')}
                  >
                    {KPIS.map(k => <option key={k} value={k}>{k.toUpperCase()}</option>)}
                  </select>
                </div>
                <Input
                  label="Target value"
                  type="number"
                  min={0}
                  step="0.01"
                  placeholder="4.5"
                  value={form.primary_kpi_target}
                  onChange={set('primary_kpi_target')}
                />
              </div>
            </CardBody>
          </Card>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <div className="flex items-center gap-3">
            <Button type="submit" loading={isPending}>
              <Link2 className="w-4 h-4" />
              Connect Account
            </Button>
            <Button type="button" variant="secondary" onClick={() => navigate(`/clients/${clientId}`)}>
              Cancel
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}

function AdsAccountView({ account }: { account: AdsAccount }) {
  const { clientId } = useParams<{ clientId: string }>()
  const navigate = useNavigate()
  const [tab, setTab] = useState<Tab>('overview')

  return (
    <div className="p-4 md:p-8">
      <button
        onClick={() => navigate(`/clients/${clientId}`)}
        className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 mb-6"
      >
        <ArrowLeft className="w-4 h-4" /> Back to Hub
      </button>

      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-blue-100 flex items-center justify-center">
            <BarChart2 className="w-5 h-5 text-blue-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-900">{account.client_name}</h1>
            <p className="text-sm text-slate-500">Customer ID: {account.customer_id}</p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 border-b border-slate-200 mb-6">
        {TABS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
              tab === key
                ? 'border-blue-600 text-blue-700'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            <Icon className="w-3.5 h-3.5" />
            {label}
          </button>
        ))}
      </div>

      {tab === 'overview' && <AccountOverview account={account} />}
      {tab === 'queue' && <ApprovalQueue accountId={account.id} />}
      {tab === 'audit' && <AuditLog accountId={account.id} />}
    </div>
  )
}

export function AdsModule() {
  const { clientId } = useParams<{ clientId: string }>()
  const id = clientId!

  const { data: brandDnaClient, isLoading: clientLoading } = useClient(id)

  const { data: adsAccount, isLoading: accountLoading, error: accountError } = useQuery({
    queryKey: ['ads-account', id],
    queryFn: () => getAccountByBrandDna(id),
    retry: false,
    enabled: !!id,
  })

  if (clientLoading || accountLoading) return <PageLoader />

  const is404 = accountError instanceof Error && accountError.message.startsWith('404')

  if (is404 || !adsAccount) {
    return (
      <ConnectAccount
        brandDnaClientId={id}
        clientName={brandDnaClient?.name ?? 'This client'}
        clientIndustry={brandDnaClient?.industry ?? undefined}
      />
    )
  }

  return <AdsAccountView account={adsAccount} />
}
