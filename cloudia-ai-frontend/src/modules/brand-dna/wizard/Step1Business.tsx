import { useState } from 'react'
import { Card, CardBody, CardHeader } from '@/shared/components/Card'
import { Input, Textarea } from '@/shared/components/Input'
import { Button } from '@/shared/components/Button'
import { cn } from '@/lib/utils'
import type { WizardData } from './BrandDNAWizard'

const INDUSTRIES = [
  { value: 'restaurant', label: 'Restaurant / Food Service' },
  { value: 'retail', label: 'Retail' },
  { value: 'professional_services', label: 'Professional Services' },
  { value: 'health_wellness', label: 'Health & Wellness' },
  { value: 'real_estate', label: 'Real Estate' },
  { value: 'education', label: 'Education' },
  { value: 'ecommerce', label: 'E-Commerce' },
  { value: 'hospitality_tourism', label: 'Hospitality & Tourism' },
  { value: 'automotive', label: 'Automotive' },
  { value: 'beauty_personal_care', label: 'Beauty & Personal Care' },
  { value: 'other', label: 'Other' },
]

interface Props {
  data: WizardData
  onChange: (patch: Partial<WizardData>) => void
  onNext: () => void
  isSaving: boolean
  onGenerate: (prompt: string) => Promise<unknown>
  isGenerating: boolean
}

export function Step1Business({ data, onChange, onNext, isSaving, onGenerate, isGenerating }: Props) {
  const [aiOpen, setAiOpen] = useState(false)
  const [prompt, setPrompt] = useState('')
  const [generated, setGenerated] = useState(false)

  const handleGenerate = async () => {
    if (!prompt.trim()) return
    await onGenerate(prompt)
    setGenerated(true)
  }

  return (
    <Card>
      <CardHeader>
        <h2 className="text-sm font-semibold text-slate-700">Step 1 — Business Basics</h2>
        <p className="text-xs text-slate-500 mt-0.5">Tell us about the business.</p>
      </CardHeader>
      <CardBody className="space-y-4">
        <Input
          label="Business Name"
          value={data.name}
          onChange={e => onChange({ name: e.target.value })}
          placeholder="e.g. Acme Digital"
        />
        <Input
          label="Website URL"
          value={data.website_url}
          onChange={e => onChange({ website_url: e.target.value })}
          placeholder="https://example.co.za"
          type="url"
          hint="Used by the AI enrichment agent to extract brand signals"
        />
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <label className="block text-sm font-medium text-slate-700">Industry</label>
            <select
              value={data.industry}
              onChange={e => onChange({ industry: e.target.value })}
              className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
            >
              <option value="">Select industry</option>
              {INDUSTRIES.map(i => <option key={i.value} value={i.value}>{i.label}</option>)}
            </select>
          </div>
          <Input
            label="Sub-Industry"
            value={data.sub_industry}
            onChange={e => onChange({ sub_industry: e.target.value })}
            placeholder="e.g. Fine Dining"
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Input
            label="Location"
            value={data.location}
            onChange={e => onChange({ location: e.target.value })}
            placeholder="e.g. Cape Town"
          />
          <Input
            label="Founded Year"
            value={data.founded_year}
            onChange={e => onChange({ founded_year: e.target.value })}
            type="number"
            min="1900"
            max={new Date().getFullYear()}
            placeholder="e.g. 2018"
          />
        </div>

        {/* AI generate panel */}
        <div className="rounded-xl border border-brand-200 bg-brand-50/40 overflow-hidden">
          <button
            type="button"
            onClick={() => setAiOpen(o => !o)}
            className="w-full flex items-center justify-between px-4 py-3 text-left"
          >
            <div className="flex items-center gap-2">
              <span className="text-base">✨</span>
              <span className="text-sm font-medium text-brand-800">Generate Brand DNA with AI</span>
              <span className="text-xs text-brand-500">optional</span>
            </div>
            <span className={cn('text-brand-500 transition-transform', aiOpen && 'rotate-180')}>▾</span>
          </button>

          {aiOpen && (
            <div className="px-4 pb-4 space-y-3 border-t border-brand-100">
              <p className="text-xs text-slate-500 pt-3">
                Describe your business in plain language — what you do, who you serve, and what makes you different.
                We'll use this to pre-fill your voice, messaging, and visual style across the remaining steps.
              </p>
              <Textarea
                label=""
                value={prompt}
                onChange={e => setPrompt(e.target.value)}
                rows={4}
                placeholder="e.g. We're a Cape Town-based craft coffee roastery specialising in single-origin African beans. Our customers are specialty coffee enthusiasts aged 25–45 who care about ethical sourcing and exceptional taste. We're premium but approachable…"
              />
              <div className="flex items-center justify-between">
                {generated && (
                  <p className="text-xs text-green-600 font-medium">Fields updated — review them in the next steps</p>
                )}
                <div className="ml-auto">
                  <Button
                    onClick={handleGenerate}
                    loading={isGenerating}
                    disabled={!prompt.trim()}
                    variant="secondary"
                  >
                    ✨ Generate
                  </Button>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="flex justify-end pt-2">
          <Button onClick={onNext} loading={isSaving}>Save & Continue →</Button>
        </div>
      </CardBody>
    </Card>
  )
}
