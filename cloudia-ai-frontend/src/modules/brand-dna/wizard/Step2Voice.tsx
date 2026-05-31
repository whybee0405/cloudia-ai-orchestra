import { Card, CardBody, CardHeader } from '@/shared/components/Card'
import { Input, TagInput, Textarea } from '@/shared/components/Input'
import { Button } from '@/shared/components/Button'
import { cn } from '@/lib/utils'
import type { WizardData } from './BrandDNAWizard'

const TONES = [
  { value: 'formal', label: 'Formal', desc: 'Professional and authoritative' },
  { value: 'casual', label: 'Casual', desc: 'Friendly and approachable' },
  { value: 'playful', label: 'Playful', desc: 'Fun, energetic, creative' },
  { value: 'authoritative', label: 'Authoritative', desc: 'Expert, confident, assertive' },
  { value: 'warm', label: 'Warm', desc: 'Empathetic, caring, personal' },
]

interface Props {
  data: WizardData
  onChange: (patch: Partial<WizardData>) => void
  onNext: () => void
  onBack: () => void
  isSaving: boolean
}

export function Step2Voice({ data, onChange, onNext, onBack, isSaving }: Props) {
  return (
    <Card>
      <CardHeader>
        <h2 className="text-sm font-semibold text-slate-700">Step 2 — Brand Voice</h2>
        <p className="text-xs text-slate-500 mt-0.5">Define how the brand speaks and feels.</p>
      </CardHeader>
      <CardBody className="space-y-5">
        <Input
          label="Tagline *"
          value={data.tagline}
          onChange={e => onChange({ tagline: e.target.value })}
          placeholder="e.g. Where every meal tells a story"
        />

        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <label className="block text-sm font-medium text-slate-700">Tone of Voice</label>
            <span className="text-xs font-medium text-brand-600 bg-brand-50 px-1.5 py-0.5 rounded">Required</span>
          </div>
          <div className="grid grid-cols-5 gap-2">
            {TONES.map(t => (
              <button
                key={t.value}
                type="button"
                onClick={() => onChange({ tone: t.value })}
                className={cn(
                  'border rounded-xl p-3 text-left transition-all',
                  data.tone === t.value
                    ? 'border-brand-500 bg-brand-50 ring-2 ring-brand-500/20'
                    : 'border-slate-200 hover:border-slate-300 bg-white'
                )}
              >
                <p className={cn('text-xs font-semibold', data.tone === t.value ? 'text-brand-700' : 'text-slate-700')}>{t.label}</p>
                <p className="text-xs text-slate-400 mt-0.5 leading-relaxed">{t.desc}</p>
              </button>
            ))}
          </div>
        </div>

        <Textarea
          label="Language Style"
          value={data.language_style}
          onChange={e => onChange({ language_style: e.target.value })}
          rows={3}
          placeholder="e.g. Conversational South African English, uses local expressions, avoids jargon, short punchy sentences…"
          hint="Describe how the brand writes — vocabulary, sentence structure, local nuances"
        />

        <TagInput
          label="Personality Traits"
          tags={data.personality_traits}
          onChange={traits => onChange({ personality_traits: traits })}
          placeholder="e.g. Innovative, Trustworthy, Bold — press Enter to add"
          hint="Add 3–6 adjectives that describe the brand's personality"
        />

        <div className="flex justify-between pt-2">
          <Button variant="secondary" onClick={onBack}>← Back</Button>
          <Button onClick={onNext} loading={isSaving}>Save & Continue →</Button>
        </div>
      </CardBody>
    </Card>
  )
}
