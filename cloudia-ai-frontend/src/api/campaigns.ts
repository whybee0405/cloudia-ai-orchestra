const BASE = '/api/campaigns'

async function req<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`)
  return res.json()
}

// ── Types ──────────────────────────────────────────────────────────────────

export interface DirectorClient {
  id: number
  name: string
  industry: string | null
  business_type: string | null
  brand_dna_client_id: string | null
  is_active: boolean
  created_at: string | null
}

export interface CampaignListItem {
  id: number
  client_id: number
  name: string
  goal: string | null
  status: string | null
  platforms: string[]
  start_date: string | null
  end_date: string | null
  created_at: string | null
}

export interface CalendarItem {
  id: number
  campaign_id: number
  platform: string
  content_type: string
  scheduled_for: string
  status: string | null
  topic: string | null
}

export interface AssetListItem {
  id: number
  campaign_id: number
  asset_type: string
  content_type: string | null
  title: string | null
  status: string | null
  created_at: string | null
}

export interface ApprovalGate {
  id: number
  campaign_id: number
  gate_name: string | null
  pipeline_order: number | null
  status: string | null
  notes: string | null
  created_at: string | null
  reviewed_at: string | null
  reviewed_by: string | null
}

export interface Campaign extends CampaignListItem {
  brief: Record<string, unknown>
  duration_days: number | null
  posts_per_week: number | null
  target_audience: string | null
  campaign_hashtags: unknown
  content_mix: unknown
  operator_notes: string | null
  completed_at: string | null
  calendar_items: CalendarItem[]
  content_assets: AssetListItem[]
  approval_gates: ApprovalGate[]
}

export interface CampaignCreate {
  client_id: number
  name: string
  goal?: string
  brief: Record<string, unknown>
  platforms: string[]
  duration_days?: number
  posts_per_week?: number
  target_audience?: string
  operator_notes?: string
}

// ── Director client (links Brand DNA UUID ↔ Campaign Director int ID) ──────

export const getDirectorClientByBrandDna = (brandDnaId: string) =>
  req<DirectorClient>(`/clients/by-brand-dna/${brandDnaId}`)

export const createDirectorClient = (payload: {
  name: string
  industry?: string
  brand_dna_client_id: string
}) => req<DirectorClient>('/clients', { method: 'POST', body: JSON.stringify(payload) })

// ── Campaigns ───────────────────────────────────────────────────────────────

export const listCampaigns = (clientId: number) =>
  req<CampaignListItem[]>(`?client_id=${clientId}`)

export const getCampaign = (id: number) => req<Campaign>(`/${id}`)

export const createCampaign = (payload: CampaignCreate) =>
  req<Campaign>('', { method: 'POST', body: JSON.stringify(payload) })

export const pauseCampaign = (id: number) =>
  req<Campaign>(`/${id}/pause`, { method: 'POST' })

export const resumeCampaign = (id: number) =>
  req<Campaign>(`/${id}/resume`, { method: 'POST' })

// ── Approval gates ──────────────────────────────────────────────────────────

export const approveGate = (
  gateId: number,
  payload: { notes?: string; reviewed_by?: string },
) => req<ApprovalGate>(`/approvals/${gateId}/approve`, { method: 'POST', body: JSON.stringify(payload) })

export const rejectGate = (
  gateId: number,
  payload: { notes?: string; reviewed_by?: string },
) => req<ApprovalGate>(`/approvals/${gateId}/reject`, { method: 'POST', body: JSON.stringify(payload) })
