import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { saveBrandDNA, updateClient } from '@/api/brand-dna'
import type { BrandDNAUpdate, PersonaCreate } from '@/shared/types'
import { Step1Business } from './Step1Business'
import { Step2Voice } from './Step2Voice'
import { Step3Visual } from './Step3Visual'
import { Step4Messages } from './Step4Messages'
import { Step5Personas } from './Step5Personas'
import { Step6Review } from './Step6Review'
import { cn } from '@/lib/utils'

export interface WizardData {
  // Step 1 — Client info
  name: string
  website_url: string
  industry: string
  sub_industry: string
  location: string
  founded_year: string
  // Step 2 — Voice
  tagline: string
  tone: string
  language_style: string
  personality_traits: string[]
  // Step 3 — Visual
  primary_color: string
  secondary_colors: string[]
  accent_color: string
  heading_font: string
  body_font: string
  visual_style: string
  logo_url: string
  // Step 4 — Messaging
  usps: string[]
  pain_points_addressed: string[]
  key_messages: string[]
  competitors: string[]
  differentiators: string[]
  // Step 5 — Personas (managed separately via API)
  personas: PersonaCreate[]
}

const STEPS = [
  { number: 1, label: 'Business' },
  { number: 2, label: 'Voice' },
  { number: 3, label: 'Visual' },
  { number: 4, label: 'Messages' },
  { number: 5, label: 'Personas' },
  { number: 6, label: 'Review' },
]

const DEFAULT: WizardData = {
  name: '', website_url: '', industry: '', sub_industry: '', location: '', founded_year: '',
  tagline: '', tone: '', language_style: '', personality_traits: [],
  primary_color: '#6366f1', secondary_colors: [], accent_color: '', heading_font: '', body_font: '', visual_style: '', logo_url: '',
  usps: [], pain_points_addressed: [], key_messages: [], competitors: [], differentiators: [],
  personas: [],
}

export function BrandDNAWizard() {
  const { clientId } = useParams<{ clientId: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [step, setStep] = useState(1)
  const [data, setData] = useState<WizardData>(DEFAULT)

  const update = (patch: Partial<WizardData>) => setData(d => ({ ...d, ...patch }))

  const saveDNA = useMutation({
    mutationFn: (body: BrandDNAUpdate) => saveBrandDNA(clientId!, body),
  })

  const saveClientInfo = useMutation({
    mutationFn: () => updateClient(clientId!, {
      name: data.name || undefined,
      website_url: data.website_url || undefined,
      industry: data.industry || undefined,
      sub_industry: data.sub_industry || undefined,
      location: data.location || undefined,
      founded_year: data.founded_year ? parseInt(data.founded_year) : undefined,
    }),
  })

  const next = async () => {
    if (step === 1) await saveClientInfo.mutateAsync()
    if (step >= 2 && step <= 4) {
      await saveDNA.mutateAsync(buildDNAPayload())
    }
    if (step < 6) setStep(s => s + 1)
  }

  const finish = () => {
    queryClient.invalidateQueries({ queryKey: ['clients'] })
    queryClient.invalidateQueries({ queryKey: ['brand-dna', clientId] })
    queryClient.invalidateQueries({ queryKey: ['personas', clientId] })
    navigate(`/clients/${clientId}`)
  }

  const buildDNAPayload = (): BrandDNAUpdate => ({
    tagline: data.tagline || undefined,
    tone: data.tone || undefined,
    language_style: data.language_style || undefined,
    personality_traits: data.personality_traits.length ? data.personality_traits : undefined,
    primary_color: data.primary_color || undefined,
    secondary_colors: data.secondary_colors.length ? data.secondary_colors : undefined,
    accent_color: data.accent_color || undefined,
    heading_font: data.heading_font || undefined,
    body_font: data.body_font || undefined,
    visual_style: data.visual_style || undefined,
    logo_url: data.logo_url || undefined,
    usps: data.usps.length ? data.usps : undefined,
    pain_points_addressed: data.pain_points_addressed.length ? data.pain_points_addressed : undefined,
    key_messages: data.key_messages.length ? data.key_messages : undefined,
    competitors: data.competitors.length ? data.competitors : undefined,
    differentiators: data.differentiators.length ? data.differentiators : undefined,
  })

  const isSaving = saveDNA.isPending || saveClientInfo.isPending

  return (
    <div className="min-h-screen bg-slate-50 p-8">
      <div className="max-w-2xl mx-auto">
        {/* Progress */}
        <div className="mb-8">
          <h1 className="text-xl font-bold text-slate-900 mb-4">Brand DNA Setup</h1>
          <div className="flex items-center gap-0">
            {STEPS.map(({ number, label }, idx) => (
              <div key={number} className="flex items-center flex-1">
                <div className="flex flex-col items-center gap-1">
                  <div className={cn(
                    'w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold transition-colors',
                    step > number ? 'bg-brand-600 text-white' :
                    step === number ? 'bg-brand-600 text-white ring-4 ring-brand-100' :
                    'bg-slate-200 text-slate-500'
                  )}>
                    {step > number ? '✓' : number}
                  </div>
                  <span className={cn('text-xs whitespace-nowrap', step === number ? 'text-brand-600 font-medium' : 'text-slate-400')}>
                    {label}
                  </span>
                </div>
                {idx < STEPS.length - 1 && (
                  <div className={cn('flex-1 h-0.5 mx-1 mb-4 transition-colors', step > number ? 'bg-brand-600' : 'bg-slate-200')} />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Step content */}
        {step === 1 && <Step1Business data={data} onChange={update} onNext={next} isSaving={isSaving} />}
        {step === 2 && <Step2Voice data={data} onChange={update} onNext={next} onBack={() => setStep(1)} isSaving={isSaving} />}
        {step === 3 && <Step3Visual data={data} onChange={update} onNext={next} onBack={() => setStep(2)} isSaving={isSaving} />}
        {step === 4 && <Step4Messages data={data} onChange={update} onNext={next} onBack={() => setStep(3)} isSaving={isSaving} />}
        {step === 5 && <Step5Personas clientId={clientId!} data={data} onChange={update} onNext={next} onBack={() => setStep(4)} isSaving={isSaving} />}
        {step === 6 && <Step6Review clientId={clientId!} data={data} onFinish={finish} onBack={() => setStep(5)} />}
      </div>
    </div>
  )
}
