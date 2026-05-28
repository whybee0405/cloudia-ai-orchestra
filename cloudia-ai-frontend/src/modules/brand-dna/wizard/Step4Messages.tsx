import { Card, CardBody, CardHeader } from '@/shared/components/Card'
import { TagInput } from '@/shared/components/Input'
import { Button } from '@/shared/components/Button'
import type { WizardData } from './BrandDNAWizard'

interface Props {
  data: WizardData
  onChange: (patch: Partial<WizardData>) => void
  onNext: () => void
  onBack: () => void
  isSaving: boolean
}

export function Step4Messages({ data, onChange, onNext, onBack, isSaving }: Props) {
  return (
    <Card>
      <CardHeader>
        <h2 className="text-sm font-semibold text-slate-700">Step 4 — Key Messages</h2>
        <p className="text-xs text-slate-500 mt-0.5">What the brand stands for and why customers choose it.</p>
      </CardHeader>
      <CardBody className="space-y-5">
        <TagInput
          label="Unique Selling Propositions (USPs)"
          tags={data.usps}
          onChange={v => onChange({ usps: v })}
          placeholder="e.g. Fastest delivery in Joburg — press Enter"
          hint="What makes this business genuinely different from competitors"
        />
        <TagInput
          label="Pain Points Addressed"
          tags={data.pain_points_addressed}
          onChange={v => onChange({ pain_points_addressed: v })}
          placeholder="e.g. No more waiting 2 hours for a quote — press Enter"
          hint="Customer problems this business solves"
        />
        <TagInput
          label="Key Messages"
          tags={data.key_messages}
          onChange={v => onChange({ key_messages: v })}
          placeholder="e.g. Quality you can taste in every bite — press Enter"
          hint="Core claims or promises the brand makes"
        />
        <TagInput
          label="Competitors"
          tags={data.competitors}
          onChange={v => onChange({ competitors: v })}
          placeholder="e.g. Takealot, Mr Delivery — press Enter"
          hint="Main competitors in the market"
        />
        <TagInput
          label="Differentiators"
          tags={data.differentiators}
          onChange={v => onChange({ differentiators: v })}
          placeholder="e.g. Family-owned, locally sourced ingredients — press Enter"
          hint="What genuinely sets this business apart from competitors"
        />
        <div className="flex justify-between pt-2">
          <Button variant="secondary" onClick={onBack}>← Back</Button>
          <Button onClick={onNext} loading={isSaving}>Save & Continue →</Button>
        </div>
      </CardBody>
    </Card>
  )
}
