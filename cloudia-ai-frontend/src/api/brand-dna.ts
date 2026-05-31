import type {
  Client, ClientCreate, ClientUpdate,
  BrandDNA, BrandDNAUpdate,
  ICPPersona, PersonaCreate, PersonaUpdate,
  PersonaTemplatesResponse, EnrichmentResponse, SuggestionsResponse,
} from '@/shared/types'

const BASE = '/api/brand'

async function req<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? 'Request failed')
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

// Clients
export const listClients = () => req<Client[]>('/clients')
export const getClient = (id: string) => req<Client>(`/clients/${id}`)
export const createClient = (body: ClientCreate) => req<Client>('/clients', { method: 'POST', body: JSON.stringify(body) })
export const updateClient = (id: string, body: ClientUpdate) => req<Client>(`/clients/${id}`, { method: 'PATCH', body: JSON.stringify(body) })

// Brand DNA
export const getBrandDNA = (clientId: string) => req<BrandDNA>(`/clients/${clientId}/brand-dna`)
export const saveBrandDNA = (clientId: string, body: BrandDNAUpdate) => req<BrandDNA>(`/clients/${clientId}/brand-dna`, { method: 'PUT', body: JSON.stringify(body) })
export const enrichBrandDNA = (clientId: string) => req<EnrichmentResponse>(`/clients/${clientId}/brand-dna/enrich`, { method: 'POST' })

// Personas
export const listPersonas = (clientId: string) => req<ICPPersona[]>(`/clients/${clientId}/personas`)
export const createPersona = (clientId: string, body: PersonaCreate) => req<ICPPersona>(`/clients/${clientId}/personas`, { method: 'POST', body: JSON.stringify(body) })
export const updatePersona = (clientId: string, personaId: number, body: PersonaUpdate) => req<ICPPersona>(`/clients/${clientId}/personas/${personaId}`, { method: 'PATCH', body: JSON.stringify(body) })
export const deletePersona = (clientId: string, personaId: number) => req<void>(`/clients/${clientId}/personas/${personaId}`, { method: 'DELETE' })
export const getPersonaTemplates = (industry?: string) => req<PersonaTemplatesResponse>(`/clients/x/personas/templates${industry ? `?industry=${industry}` : ''}`)

// Persona suggestions
export interface PersonaArchetype {
  persona_name: string
  age_min?: number
  age_max?: number
  gender_skew?: string
  income_bracket?: string
  location_type?: string
  interests?: string[]
  values?: string[]
  pain_points?: string[]
  goals?: string[]
  preferred_channels?: string[]
  seo_keywords?: string[]
  vocabulary?: string[]
}
export const suggestPersonas = (clientId: string) =>
  req<{ archetypes: PersonaArchetype[] }>(`/clients/${clientId}/personas/suggest`, { method: 'POST' })

// Suggestions
export const getSuggestions = (clientId: string) => req<SuggestionsResponse>(`/clients/${clientId}/suggestions`)

// Website scraping
export interface ScrapeSignals {
  description: string
  tagline_hint: string
  tone_signals: string[]
  key_phrases: string[]
  suggested_prompt: string
}
export const scrapeWebsite = (clientId: string) =>
  req<ScrapeSignals>(`/clients/${clientId}/scrape`, { method: 'POST' })

// AI generation
export const generateBrandDNA = (clientId: string, prompt: string) =>
  req<BrandDNA>(`/clients/${clientId}/brand-dna/generate`, { method: 'POST', body: JSON.stringify({ prompt }) })

// Logo upload (multipart — bypass the JSON helper)
export async function uploadLogo(clientId: string, file: File): Promise<{ logo_url: string }> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE}/clients/${clientId}/logo`, { method: 'POST', body: form })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? 'Upload failed')
  }
  return res.json()
}
