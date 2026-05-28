const BASE = '/api/ads'

async function req<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!res.ok) throw new Error(`Ads API error: ${res.statusText}`)
  return res.json()
}

export interface AdsSummary {
  client_id: string
  active_count: number
  completed_count: number
  last_activity?: string
  status_summary: string
}

export const getAdsSummary = (clientId: string) => req<AdsSummary>(`/clients/${clientId}/summary`)
