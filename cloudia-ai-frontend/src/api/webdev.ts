const BASE = '/api/webdev'

async function req<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!res.ok) throw new Error(`WebDev API error: ${res.statusText}`)
  return res.json()
}

export interface WebdevSummary {
  client_id: string
  active_count: number
  completed_count: number
  last_activity?: string
  status_summary: string
}

export const getWebdevSummary = (clientId: string) => req<WebdevSummary>(`/clients/${clientId}/summary`)
