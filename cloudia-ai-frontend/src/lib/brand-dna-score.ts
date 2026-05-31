import type { BrandDNA, Client } from '@/shared/types'

export interface ScoreDetail {
  label: string
  done: boolean
  required: boolean
}

export function getBrandDNAScore(
  client: Client | undefined,
  brandDna: BrandDNA | undefined,
  personaCount: number,
): { score: number; details: ScoreDetail[] } {
  const details: ScoreDetail[] = [
    // Core — 70 pts
    { label: 'Industry set', done: !!client?.industry, required: true },
    { label: 'Brand tone', done: !!brandDna?.tone, required: true },
    { label: 'Tagline', done: !!brandDna?.tagline, required: true },
    { label: 'Primary colour', done: !!brandDna?.primary_color, required: true },
    { label: 'At least 2 USPs', done: (brandDna?.usps?.length ?? 0) >= 2, required: true },
    { label: 'At least 1 persona', done: personaCount >= 1, required: true },
    { label: 'Logo uploaded', done: !!brandDna?.logo_url, required: true },
    // Enhancement — 30 pts
    { label: 'Language style', done: !!brandDna?.language_style, required: false },
    { label: 'Personality traits', done: (brandDna?.personality_traits?.length ?? 0) >= 2, required: false },
    { label: 'Visual style', done: !!brandDna?.visual_style, required: false },
    { label: 'Key messages', done: (brandDna?.key_messages?.length ?? 0) >= 1, required: false },
    { label: 'Differentiators', done: (brandDna?.differentiators?.length ?? 0) >= 1, required: false },
    { label: 'Website URL', done: !!client?.website_url, required: false },
  ]

  const requiredTotal = details.filter(d => d.required).length  // 7
  const optionalTotal = details.filter(d => !d.required).length // 6

  const requiredDone = details.filter(d => d.required && d.done).length
  const optionalDone = details.filter(d => !d.required && d.done).length

  // Required fields account for 70%, optional for 30%
  const score = Math.round(
    (requiredDone / requiredTotal) * 70 +
    (optionalDone / optionalTotal) * 30
  )

  return { score, details }
}

export function scoreColor(score: number): string {
  if (score >= 70) return '#22c55e'  // green-500
  if (score >= 40) return '#f59e0b'  // amber-500
  return '#ef4444'                    // red-500
}
