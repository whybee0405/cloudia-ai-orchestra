const BASE = '/api/ads'

async function req<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`)
  return res.json()
}

// ── Types ──────────────────────────────────────────────────────────────────

export interface AdsAccount {
  id: number
  client_name: string
  customer_id: string
  mcc_id: string
  status: string
  industry: string | null
  business_type: string | null
  budget_sensitivity: string | null
  monthly_ad_spend: number | null
  primary_kpi: string | null
  primary_kpi_target: number | null
  secondary_kpi: string | null
  secondary_kpi_target: number | null
  baseline_ctr: number | null
  baseline_cvr: number | null
  baseline_cpc: number | null
  baseline_cpa: number | null
  baseline_roas: number | null
  brand_dna_client_id: string | null
}

export interface AdsAccountCreate {
  client_name: string
  customer_id: string
  mcc_id: string
  industry?: string
  business_type?: string
  budget_sensitivity?: string
  monthly_ad_spend?: number
  primary_kpi?: string
  primary_kpi_target?: number
  brand_dna_client_id: string
}

export interface QueueItem {
  id: number
  account_id: number
  agent_name: string
  action_type: string
  action_payload: Record<string, unknown> | null
  reasoning: string | null
  status: string
  created_at: string
  reviewed_at: string | null
  reviewed_by: string | null
}

export interface AuditEntry {
  id: number
  account_id: number
  campaign_id: string | null
  anomaly_type: string | null
  severity: string | null
  diagnosis: string | null
  recommended_action: string | null
  run_time: string
  acknowledged: boolean
}

// ── Accounts ───────────────────────────────────────────────────────────────

export const getAccountByBrandDna = (brandDnaId: string) =>
  req<AdsAccount>(`/accounts/by-brand-dna/${brandDnaId}`)

export const createAdsAccount = (payload: AdsAccountCreate) =>
  req<AdsAccount>('/accounts', { method: 'POST', body: JSON.stringify(payload) })

export const listAdsAccounts = () => req<AdsAccount[]>('/accounts')

// ── Approval queue ─────────────────────────────────────────────────────────

export const listQueue = (accountId?: number) => {
  const qs = accountId != null ? `?account_id=${accountId}` : ''
  return req<QueueItem[]>(`/queue${qs}`)
}

export const approveQueueItem = (id: number, reviewedBy: string) =>
  req<QueueItem>(`/queue/${id}/approve`, {
    method: 'POST',
    body: JSON.stringify({ reviewed_by: reviewedBy }),
  })

export const rejectQueueItem = (id: number, reviewedBy: string) =>
  req<QueueItem>(`/queue/${id}/reject`, {
    method: 'POST',
    body: JSON.stringify({ reviewed_by: reviewedBy }),
  })

export const executeQueueItem = (id: number) =>
  req<QueueItem>(`/queue/${id}/execute`, { method: 'POST' })

// ── Audit log ──────────────────────────────────────────────────────────────

export const listAuditLog = (accountId?: number, severity?: string) => {
  const params = new URLSearchParams()
  if (accountId != null) params.set('account_id', String(accountId))
  if (severity) params.set('severity', severity)
  const qs = params.toString() ? `?${params.toString()}` : ''
  return req<AuditEntry[]>(`/audit${qs}`)
}
