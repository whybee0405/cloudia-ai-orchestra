const BASE = '/api/webdev'

async function req<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`)
  return res.json()
}

// ── Types ──────────────────────────────────────────────────────────────────

export interface WebdevClient {
  id: number
  name: string
  industry: string | null
  business_type: string | null
  target_audience: string | null
  usp: string | null
  tone_of_voice: string | null
  brand_colours: Record<string, string> | null
  brand_fonts: Record<string, string> | null
  logo_url: string | null
  contact_email: string | null
  contact_phone: string | null
  website_url: string | null
  social_links: Record<string, string> | null
  notes: string | null
  brand_dna_client_id: string | null
  created_at: string
}

export interface WebdevClientCreate {
  name: string
  industry?: string
  business_type?: string
  brand_dna_client_id: string
}

export interface AgentTask {
  id: number
  agent_name: string
  pipeline_order: number
  status: string
  tokens_used: number | null
  cost_usd: number | null
  started_at: string | null
  completed_at: string | null
  error: string | null
  retry_count: number
}

export interface ApprovalGate {
  id: number
  gate_name: string
  pipeline_order: number
  status: string
  notes: string | null
  created_at: string
  reviewed_at: string | null
  reviewed_by: string | null
}

export interface Project {
  id: number
  client_id: number
  platform: string | null
  status: string
  brief: Record<string, unknown> | null
  pipeline_plan: Record<string, unknown> | null
  site_url: string | null
  estimated_pages: number | null
  actual_pages: number | null
  created_at: string
  completed_at: string | null
  operator_notes: string | null
  tasks: AgentTask[]
  gates: ApprovalGate[]
}

export interface ProjectCreate {
  client_id: number
  platform?: 'wordpress' | 'shopify'
  brief: Record<string, unknown>
}

export interface ContentPiece {
  id: number
  page_slug: string
  content_type: string
  title: string | null
  h1: string | null
  body_content: string | null
  cta_text: string | null
  meta_title: string | null
  meta_description: string | null
  status: string
  revision_notes: string | null
}

export interface ContentUpdate {
  title?: string
  h1?: string
  body_content?: string
  cta_text?: string
  meta_title?: string
  meta_description?: string
  revision_notes?: string
}

export interface Credential {
  id: number
  client_id: number
  platform: string
  site_url: string
  shop_name: string | null
  is_active: boolean
  last_verified_at: string | null
}

export interface CredentialCreate {
  client_id: number
  platform: 'wordpress' | 'shopify'
  site_url: string
  api_url?: string
  access_token?: string
  app_password?: string
  shop_name?: string
  api_version?: string
}

export interface SystemStatus {
  db_connected: boolean
  redis_connected: boolean
  celery_worker_active: boolean
}

// ── Clients ────────────────────────────────────────────────────────────────

export const getClientByBrandDna = (brandDnaId: string) =>
  req<WebdevClient>(`/projects/clients/by-brand-dna/${brandDnaId}`)

export const createClient = (payload: WebdevClientCreate) =>
  req<WebdevClient>('/projects/clients/', { method: 'POST', body: JSON.stringify(payload) })

export const listClients = () => req<WebdevClient[]>('/projects/clients/')

// ── Projects ───────────────────────────────────────────────────────────────

export const listProjects = (clientId?: number) => {
  const qs = clientId != null ? `?client_id=${clientId}` : ''
  return req<Project[]>(`/projects/${qs}`)
}

export const getProject = (id: number) => req<Project>(`/projects/${id}`)

export const createProject = (payload: ProjectCreate) =>
  req<Project>('/projects/', { method: 'POST', body: JSON.stringify(payload) })

export const cancelProject = (id: number) =>
  req<{ detail: string }>(`/projects/${id}`, { method: 'DELETE' })

export const retryTask = (projectId: number, taskId: number) =>
  req<{ detail: string }>(`/projects/${projectId}/retry/${taskId}`, { method: 'POST' })

// ── Approval gates ─────────────────────────────────────────────────────────

export const listGates = (projectId?: number, status?: string) => {
  const params = new URLSearchParams()
  if (projectId != null) params.set('project_id', String(projectId))
  if (status) params.set('status', status)
  const qs = params.toString() ? `?${params.toString()}` : ''
  return req<ApprovalGate[]>(`/approvals/${qs}`)
}

export const approveGate = (gateId: number, reviewedBy = 'operator', notes?: string) =>
  req<ApprovalGate>(`/approvals/${gateId}/approve`, {
    method: 'POST',
    body: JSON.stringify({ reviewed_by: reviewedBy, notes }),
  })

export const rejectGate = (gateId: number, notes: string, reviewedBy = 'operator') =>
  req<ApprovalGate>(`/approvals/${gateId}/reject`, {
    method: 'POST',
    body: JSON.stringify({ reviewed_by: reviewedBy, notes }),
  })

export const requestRevision = (gateId: number, notes: string, reviewedBy = 'operator') =>
  req<ApprovalGate>(`/approvals/${gateId}/request-revision`, {
    method: 'POST',
    body: JSON.stringify({ reviewed_by: reviewedBy, notes }),
  })

// ── Content ────────────────────────────────────────────────────────────────

export const getProjectContent = (projectId: number) =>
  req<ContentPiece[]>(`/content/project/${projectId}`)

export const updateContent = (contentId: number, payload: ContentUpdate) =>
  req<ContentPiece>(`/content/${contentId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })

export const approveContent = (contentId: number) =>
  req<ContentPiece>(`/content/${contentId}/approve`, { method: 'POST' })

export const approveAllContent = (projectId: number) =>
  req<{ approved: number }>(`/content/project/${projectId}/approve-all`, { method: 'POST' })

export const regenerateContent = (contentId: number) =>
  req<ContentPiece>(`/content/${contentId}/regenerate`, { method: 'POST' })

// ── Credentials & system status ────────────────────────────────────────────

export const getSystemStatus = () => req<SystemStatus>('/settings/')

export const listCredentials = () => req<Credential[]>('/settings/credentials/')

export const createCredential = (payload: CredentialCreate) =>
  req<Credential>('/settings/credentials/', {
    method: 'POST',
    body: JSON.stringify(payload),
  })

export const testCredential = (id: number) =>
  req<{ ok: boolean; detail: string }>(`/settings/credentials/${id}/test`)

export const deleteCredential = (id: number) =>
  req<void>(`/settings/credentials/${id}`, { method: 'DELETE' })
