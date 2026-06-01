import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getBrandDNA, listPersonas } from '@/api/brand-dna'
import { useClient } from '@/shared/hooks/useClient'
import { Card, CardBody, CardHeader } from '@/shared/components/Card'
import { Button } from '@/shared/components/Button'
import { Badge } from '@/shared/components/Badge'
import { PageLoader } from '@/shared/components/LoadingSpinner'
import { ArrowLeft, Edit3, Users, Palette, MessageSquare, Target } from 'lucide-react'

export function BrandDNAView() {
  const { clientId } = useParams<{ clientId: string }>()
  const navigate = useNavigate()
  const id = clientId!

  const { data: client, isLoading: clientLoading } = useClient(id)
  const { data: brandDna, isLoading: dnaLoading } = useQuery({ queryKey: ['brand-dna', id], queryFn: () => getBrandDNA(id), retry: false })
  const { data: personas } = useQuery({ queryKey: ['personas', id], queryFn: () => listPersonas(id) })

  if (clientLoading || dnaLoading) return <PageLoader />

  if (!brandDna) {
    return (
      <div className="p-8">
        <button onClick={() => navigate(`/clients/${id}`)} className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 mb-6">
          <ArrowLeft className="w-4 h-4" /> Back to Hub
        </button>
        <div className="text-center py-20">
          <p className="text-sm text-slate-500 mb-4">Brand DNA hasn't been set up yet.</p>
          <Button onClick={() => navigate(`/clients/${id}/brand-dna/setup`)}>Set Up Brand DNA</Button>
        </div>
      </div>
    )
  }

  return (
    <div className="p-4 md:p-8 max-w-3xl">
      <button onClick={() => navigate(`/clients/${id}`)} className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 mb-6">
        <ArrowLeft className="w-4 h-4" /> Back to Hub
      </button>

      <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
        <div>
          <h1 className="text-xl md:text-2xl font-bold text-slate-900">Brand DNA</h1>
          <p className="text-sm text-slate-500">{client?.name}</p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" size="sm" onClick={() => navigate(`/clients/${id}/brand-dna/review`)}>
            <Edit3 className="w-3.5 h-3.5" /> Edit Inline
          </Button>
          <Button variant="ghost" size="sm" onClick={() => navigate(`/clients/${id}/brand-dna/wizard`)}>
            Full Wizard
          </Button>
        </div>
      </div>

      <div className="space-y-5">
        {/* Voice */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <MessageSquare className="w-4 h-4 text-slate-400" />
              <h2 className="text-sm font-semibold text-slate-700">Brand Voice</h2>
            </div>
          </CardHeader>
          <CardBody className="space-y-3">
            {brandDna.tagline && <p className="text-sm text-slate-700 italic">"{brandDna.tagline}"</p>}
            <div className="flex flex-wrap gap-2">
              {brandDna.tone && <Badge variant="info" className="capitalize">{brandDna.tone}</Badge>}
              {brandDna.visual_style && <Badge variant="purple" className="capitalize">{brandDna.visual_style}</Badge>}
            </div>
            {brandDna.language_style && <p className="text-sm text-slate-600">{brandDna.language_style}</p>}
            {brandDna.personality_traits?.length && (
              <div className="flex flex-wrap gap-1.5">
                {brandDna.personality_traits.map(t => <Badge key={t}>{t}</Badge>)}
              </div>
            )}
          </CardBody>
        </Card>

        {/* Visual */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Palette className="w-4 h-4 text-slate-400" />
              <h2 className="text-sm font-semibold text-slate-700">Visual Identity</h2>
            </div>
          </CardHeader>
          <CardBody>
            <div className="flex flex-wrap gap-4">
              {brandDna.primary_color && (
                <div className="flex items-center gap-2">
                  <span className="w-8 h-8 rounded-lg border border-slate-200 shadow-sm" style={{ backgroundColor: brandDna.primary_color }} />
                  <div>
                    <p className="text-xs text-slate-500">Primary</p>
                    <p className="text-xs font-mono font-medium text-slate-700">{brandDna.primary_color.toUpperCase()}</p>
                  </div>
                </div>
              )}
              {brandDna.accent_color && (
                <div className="flex items-center gap-2">
                  <span className="w-8 h-8 rounded-lg border border-slate-200 shadow-sm" style={{ backgroundColor: brandDna.accent_color }} />
                  <div>
                    <p className="text-xs text-slate-500">Accent</p>
                    <p className="text-xs font-mono font-medium text-slate-700">{brandDna.accent_color.toUpperCase()}</p>
                  </div>
                </div>
              )}
              {(brandDna.heading_font || brandDna.body_font) && (
                <div>
                  <p className="text-xs text-slate-500 mb-1">Fonts</p>
                  <p className="text-xs text-slate-700">{brandDna.heading_font} / {brandDna.body_font}</p>
                </div>
              )}
            </div>
          </CardBody>
        </Card>

        {/* Messaging */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Target className="w-4 h-4 text-slate-400" />
              <h2 className="text-sm font-semibold text-slate-700">Key Messages</h2>
            </div>
          </CardHeader>
          <CardBody className="space-y-3">
            {[
              { label: 'USPs', items: brandDna.usps },
              { label: 'Key Messages', items: brandDna.key_messages },
              { label: 'Differentiators', items: brandDna.differentiators },
              { label: 'Pain Points Addressed', items: brandDna.pain_points_addressed },
            ].filter(s => s.items?.length).map(({ label, items }) => (
              <div key={label}>
                <p className="text-xs font-medium text-slate-500 mb-1.5">{label}</p>
                <div className="flex flex-wrap gap-1.5">
                  {items!.map(item => <Badge key={item}>{item}</Badge>)}
                </div>
              </div>
            ))}
          </CardBody>
        </Card>

        {/* Personas */}
        {personas?.length ? (
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Users className="w-4 h-4 text-slate-400" />
                <h2 className="text-sm font-semibold text-slate-700">ICP Personas ({personas.length})</h2>
              </div>
            </CardHeader>
            <CardBody className="space-y-3">
              {personas.map(p => (
                <div key={p.id} className="border border-slate-200 rounded-xl p-3">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-sm font-semibold text-slate-800">{p.persona_name}</p>
                    <p className="text-xs text-slate-400">
                      {p.age_min && p.age_max ? `${p.age_min}–${p.age_max}` : ''} · {p.income_bracket}
                    </p>
                  </div>
                  {p.seo_keywords?.length ? (
                    <div className="flex flex-wrap gap-1">
                      {p.seo_keywords.map(k => <Badge key={k} variant="info" className="text-xs">{k}</Badge>)}
                    </div>
                  ) : null}
                </div>
              ))}
            </CardBody>
          </Card>
        ) : null}
      </div>
    </div>
  )
}
