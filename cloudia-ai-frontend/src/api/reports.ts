// ── Types ──────────────────────────────────────────────────────────────────

export interface AdsSummary {
  service: 'google-ads'
  connected: boolean
  account_status: string | null
  customer_id: string | null
  pending_queue_items: number
  anomalies_last_7d: number
  critical_anomalies_last_7d: number
  baseline_roas: number | null
  primary_kpi: string | null
  primary_kpi_target: number | null
}

export interface WebdevSummary {
  service: 'webdev'
  connected: boolean
  client_name: string
  total_projects: number
  active_projects: number
  completed_projects: number
  pending_gates: number
  last_project_platform: string | null
  last_project_status: string | null
}

export interface CampaignSummary {
  service: 'campaign-director'
  connected: boolean
  client_name: string
  total_campaigns: number
  active_campaigns: number
  pending_gates: number
  latest_campaign_name: string | null
  latest_campaign_status: string | null
}

export interface CampaignAnalytics {
  total_reach: number
  total_impressions: number
  total_engagement: number
  avg_engagement_rate: number | null
  top_posts: Array<{
    published_post_id: number
    post_url: string | null
    platform: string | null
    impressions: number
    reach: number
    engagement_rate: number | null
  }>
}

// ── Helpers ────────────────────────────────────────────────────────────────

async function get<T>(url: string): Promise<T> {
  const res = await fetch(url, { headers: { 'Content-Type': 'application/json' } })
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`)
  return res.json()
}

// ── Endpoints ──────────────────────────────────────────────────────────────

export const getAdsSummary = (brandDnaClientId: string) =>
  get<AdsSummary>(`/api/ads/accounts/by-brand-dna/${brandDnaClientId}/summary`)

export const getWebdevSummary = (brandDnaClientId: string) =>
  get<WebdevSummary>(`/api/webdev/clients/by-brand-dna/${brandDnaClientId}/summary`)

export const getCampaignSummary = (brandDnaClientId: string) =>
  get<CampaignSummary>(`/api/campaigns/clients/by-brand-dna/${brandDnaClientId}/summary`)

export const getCampaignAnalytics = (
  directorClientId: number,
  params?: { date_from?: string; date_to?: string },
) => {
  const qs = new URLSearchParams({ client_id: String(directorClientId) })
  if (params?.date_from) qs.set('date_from', params.date_from)
  if (params?.date_to) qs.set('date_to', params.date_to)
  return get<CampaignAnalytics>(`/api/analytics?${qs}`)
}

// ── Phase 2: asset report & agent costs ────────────────────────────────────

export interface AssetReport {
  total_assets: number
  by_status: Record<string, number>
  by_type: Record<string, number>
  brand_check_pass_rate: number | null
  cost_usd_total: number
  tokens_total: number
  by_date: Array<{ date: string; count: number; cost_usd: number }>
}

export interface AgentCostReport {
  service: string
  period_cost_usd: number
  period_tokens: number
  by_agent: Array<{ agent_name: string; runs: number; tokens: number; cost_usd: number }>
  by_day: Array<{ date: string; cost_usd: number; tokens: number }>
}

export const getAssetReport = (
  directorClientId: number,
  params?: { date_from?: string; date_to?: string },
) => {
  const qs = new URLSearchParams({ client_id: String(directorClientId) })
  if (params?.date_from) qs.set('date_from', params.date_from)
  if (params?.date_to) qs.set('date_to', params.date_to)
  return get<AssetReport>(`/api/assets/report?${qs}`)
}

export const getCampaignAgentCosts = (
  directorClientId: number,
  params?: { date_from?: string; date_to?: string },
) => {
  const qs = new URLSearchParams({ client_id: String(directorClientId) })
  if (params?.date_from) qs.set('date_from', params.date_from)
  if (params?.date_to) qs.set('date_to', params.date_to)
  return get<AgentCostReport>(`/api/reporting/agent-costs?${qs}`)
}

export const getAdsAgentCosts = (
  adsAccountId: number,
  params?: { date_from?: string; date_to?: string },
) => {
  const qs = new URLSearchParams({ account_id: String(adsAccountId) })
  if (params?.date_from) qs.set('date_from', params.date_from)
  if (params?.date_to) qs.set('date_to', params.date_to)
  return get<AgentCostReport>(`/api/ads/reporting/agent-costs?${qs}`)
}

// ── Phase 3: Brand DNA usage audit ────────────────────────────────────────

export interface BrandDNAUsage {
  client_id: string
  total_accesses: number
  by_service: Record<string, number>
  by_agent: Array<{ agent_name: string; service: string; count: number }>
  by_day: Array<{ date: string; count: number }>
  persona_usage: Array<{ persona_id: number; persona_name: string; access_count: number }>
}

export const getBrandDNAUsage = (
  clientId: string,
  params?: { date_from?: string; date_to?: string },
) => {
  const qs = new URLSearchParams()
  if (params?.date_from) qs.set('date_from', params.date_from)
  if (params?.date_to) qs.set('date_to', params.date_to)
  const query = qs.toString() ? `?${qs}` : ''
  return get<BrandDNAUsage>(`/api/brand/clients/${clientId}/reports/brand-dna-usage${query}`)
}

export const getWebdevAgentCosts = (
  webdevClientId: number,
  params?: { date_from?: string; date_to?: string },
) => {
  const qs = new URLSearchParams({ client_id: String(webdevClientId) })
  if (params?.date_from) qs.set('date_from', params.date_from)
  if (params?.date_to) qs.set('date_to', params.date_to)
  return get<AgentCostReport>(`/api/webdev/reporting/agent-costs?${qs}`)
}
