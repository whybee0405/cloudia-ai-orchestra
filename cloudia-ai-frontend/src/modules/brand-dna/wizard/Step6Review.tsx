import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { getBrandDNA, listPersonas, enrichBrandDNA } from '@/api/brand-dna'
import { Card, CardBody, CardHeader } from '@/shared/components/Card'
import { Button } from '@/shared/components/Button'
import { Badge } from '@/shared/components/Badge'
import { Sparkles, CheckCircle } from 'lucide-react'
import type { WizardData } from './BrandDNAWizard'
import type { EnrichmentSuggestion } from '@/shared/types'

interface Props {
  clientId: string
  data: WizardData
  onFinish: () => void
  onBack: () => void
}

export function Step6Review({ clientId, onFinish, onBack }: Props) {
  const [enrichResult, setEnrichResult] = useState<{ summary: string; suggestions: EnrichmentSuggestion[] } | null>(null)

  const { data: brandDna } = useQuery({ queryKey: ['brand-dna', clientId], queryFn: () => getBrandDNA(clientId), retry: false })
  const { data: personas } = useQuery({ queryKey: ['personas', clientId], queryFn: () => listPersonas(clientId) })

  const enrichMut = useMutation({
    mutationFn: () => enrichBrandDNA(clientId),
    onSuccess: (result) => setEnrichResult(result),
  })

  const sections = [
    { label: 'Tone', value: brandDna?.tone },
    { label: 'Visual Style', value: brandDna?.visual_style },
    { label: 'Primary Colour', value: brandDna?.primary_color },
    { label: 'Tagline', value: brandDna?.tagline },
  ]

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <h2 className="text-sm font-semibold text-slate-700">Step 6 — Review & Enrich</h2>
          <p className="text-xs text-slate-500 mt-0.5">Check your Brand DNA before completing setup.</p>
        </CardHeader>
        <CardBody className="space-y-4">
          {/* Quick summary */}
          <div className="grid grid-cols-2 gap-3">
            {sections.map(({ label, value }) => value && (
              <div key={label} className="bg-slate-50 rounded-lg px-3 py-2.5">
                <p className="text-xs text-slate-500 mb-0.5">{label}</p>
                <div className="flex items-center gap-2">
                  {label === 'Primary Colour' && (
                    <span className="w-4 h-4 rounded-full border border-slate-200 flex-shrink-0" style={{ backgroundColor: value }} />
                  )}
                  <p className="text-sm font-medium text-slate-800 capitalize">{value}</p>
                </div>
              </div>
            ))}
          </div>

          {/* USPs */}
          {brandDna?.usps?.length ? (
            <div>
              <p className="text-xs font-medium text-slate-500 mb-1.5">USPs ({brandDna.usps.length})</p>
              <div className="flex flex-wrap gap-1.5">
                {brandDna.usps.map(u => <Badge key={u}>{u}</Badge>)}
              </div>
            </div>
          ) : null}

          {/* Personas */}
          {personas?.length ? (
            <div>
              <p className="text-xs font-medium text-slate-500 mb-1.5">Personas ({personas.length})</p>
              <div className="space-y-1.5">
                {personas.map(p => (
                  <div key={p.id} className="flex items-center gap-2 bg-slate-50 rounded-lg px-3 py-2">
                    <CheckCircle className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0" />
                    <span className="text-sm text-slate-700">{p.persona_name}</span>
                    {p.seo_keywords?.length && <span className="text-xs text-slate-400">· {p.seo_keywords.length} keywords</span>}
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </CardBody>
      </Card>

      {/* AI Enrichment */}
      <Card>
        <CardBody className="space-y-3">
          <div className="flex items-start gap-3">
            <div className="w-9 h-9 rounded-xl bg-purple-100 flex items-center justify-center flex-shrink-0">
              <Sparkles className="w-4 h-4 text-purple-600" />
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-800">AI Enrichment</p>
              <p className="text-xs text-slate-500">Let Claude analyse your brand and suggest improvements to USPs, key messages, and persona keywords.</p>
            </div>
          </div>
          {!enrichResult && (
            <Button variant="secondary" size="sm" onClick={() => enrichMut.mutate()} loading={enrichMut.isPending}>
              <Sparkles className="w-3.5 h-3.5" />
              Enrich with AI
            </Button>
          )}
          {enrichResult && (
            <div className="space-y-3">
              <div className="bg-purple-50 rounded-lg p-3">
                <p className="text-xs text-purple-800 leading-relaxed">{enrichResult.summary}</p>
              </div>
              {enrichResult.suggestions.slice(0, 4).map((s, i) => (
                <div key={i} className="border border-slate-200 rounded-lg p-3 space-y-1">
                  <p className="text-xs font-semibold text-slate-700 capitalize">{s.field.replace(/_/g, ' ')}</p>
                  <p className="text-xs text-slate-500">{s.reasoning}</p>
                  {s.suggested_value && (
                    <p className="text-xs text-brand-700 bg-brand-50 px-2 py-1 rounded">
                      Suggested: {Array.isArray(s.suggested_value) ? s.suggested_value.join(', ') : String(s.suggested_value)}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardBody>
      </Card>

      <div className="flex justify-between">
        <Button variant="secondary" onClick={onBack}>← Back</Button>
        <Button onClick={onFinish}>
          <CheckCircle className="w-4 h-4" />
          Complete Setup
        </Button>
      </div>
    </div>
  )
}
