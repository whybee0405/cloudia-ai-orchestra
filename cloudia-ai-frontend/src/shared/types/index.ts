export interface Client {
  id: string
  name: string
  website_url?: string
  industry?: string
  sub_industry?: string
  location?: string
  timezone: string
  founded_year?: number
  is_active: boolean
  created_at: string
  updated_at: string
  has_brand_dna: boolean
  persona_count: number
}

export interface ClientCreate {
  name: string
  website_url?: string
  industry?: string
  sub_industry?: string
  location?: string
  timezone?: string
  founded_year?: number
}

export interface ClientUpdate extends Partial<ClientCreate> {
  is_active?: boolean
}

export interface BrandDNA {
  id: number
  client_id: string
  tagline?: string
  tone?: string
  language_style?: string
  personality_traits?: string[]
  primary_color?: string
  secondary_colors?: string[]
  accent_color?: string
  heading_font?: string
  body_font?: string
  logo_url?: string
  visual_style?: string
  usps?: string[]
  pain_points_addressed?: string[]
  key_messages?: string[]
  competitors?: string[]
  differentiators?: string[]
  enriched_at?: string
  created_at: string
  updated_at: string
}

export type BrandDNAUpdate = Partial<Omit<BrandDNA, 'id' | 'client_id' | 'created_at' | 'updated_at' | 'enriched_at'>>

export interface ICPPersona {
  id: number
  client_id: string
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
  order: number
  created_at: string
  updated_at: string
}

export type PersonaCreate = Omit<ICPPersona, 'id' | 'client_id' | 'created_at' | 'updated_at'>
export type PersonaUpdate = Partial<PersonaCreate>

export interface PersonaTemplate {
  persona_name: string
  age_min: number
  age_max: number
  gender_skew: string
  income_bracket: string
  location_type: string
  interests: string[]
  values: string[]
  pain_points: string[]
  goals: string[]
  preferred_channels: string[]
  seo_keywords: string[]
  vocabulary: string[]
  order: number
}

export interface PersonaTemplatesResponse {
  industries: { key: string; label: string; template_count: number }[]
  templates: Record<string, PersonaTemplate[]>
}

export interface EnrichmentSuggestion {
  field: string
  current_value: unknown
  suggested_value: unknown
  reasoning: string
}

export interface EnrichmentResponse {
  suggestions: EnrichmentSuggestion[]
  summary: string
}

export interface Suggestion {
  id: string
  priority: number
  service: string
  title: string
  description: string
  action_label: string
  action_url: string
}

export interface SuggestionsResponse {
  client_id: string
  suggestions: Suggestion[]
}
