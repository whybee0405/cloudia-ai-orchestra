import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft } from 'lucide-react'
import { createCampaign, type CampaignCreate } from '@/api/campaigns'
import { Card, CardBody, CardHeader } from '@/shared/components/Card'
import { Button } from '@/shared/components/Button'
import { Input } from '@/shared/components/Input'

const PLATFORMS = ['Instagram', 'Facebook', 'Twitter', 'LinkedIn', 'TikTok', 'YouTube']

interface FormState {
  name: string
  goal: string
  platforms: string[]
  duration_days: string
  posts_per_week: string
  target_audience: string
  objective: string
  content_themes: string
  tone_notes: string
  operator_notes: string
}

const EMPTY: FormState = {
  name: '',
  goal: '',
  platforms: [],
  duration_days: '',
  posts_per_week: '',
  target_audience: '',
  objective: '',
  content_themes: '',
  tone_notes: '',
  operator_notes: '',
}

export function NewCampaignForm({ directorClientId }: { directorClientId: number }) {
  const { clientId } = useParams<{ clientId: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [form, setForm] = useState<FormState>(EMPTY)
  const [error, setError] = useState('')

  const set = (key: keyof FormState) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm(f => ({ ...f, [key]: e.target.value }))

  const togglePlatform = (p: string) =>
    setForm(f => ({
      ...f,
      platforms: f.platforms.includes(p) ? f.platforms.filter(x => x !== p) : [...f.platforms, p],
    }))

  const { mutate, isPending } = useMutation({
    mutationFn: (payload: CampaignCreate) => createCampaign(payload),
    onSuccess: campaign => {
      qc.invalidateQueries({ queryKey: ['campaigns', directorClientId] })
      navigate(`/clients/${clientId}/campaigns/${campaign.id}`)
    },
    onError: (err: Error) => setError(err.message),
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    if (!form.name.trim()) { setError('Campaign name is required.'); return }
    if (form.platforms.length === 0) { setError('Select at least one platform.'); return }

    const brief: Record<string, string> = {}
    if (form.objective.trim()) brief.objective = form.objective.trim()
    if (form.content_themes.trim()) brief.content_themes = form.content_themes.trim()
    if (form.tone_notes.trim()) brief.tone_notes = form.tone_notes.trim()

    mutate({
      client_id: directorClientId,
      name: form.name.trim(),
      goal: form.goal.trim() || undefined,
      brief,
      platforms: form.platforms,
      duration_days: form.duration_days ? parseInt(form.duration_days) : undefined,
      posts_per_week: form.posts_per_week ? parseInt(form.posts_per_week) : undefined,
      target_audience: form.target_audience.trim() || undefined,
      operator_notes: form.operator_notes.trim() || undefined,
    })
  }

  return (
    <div className="p-8 max-w-2xl">
      <button
        onClick={() => navigate(`/clients/${clientId}/campaigns`)}
        className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 mb-6"
      >
        <ArrowLeft className="w-4 h-4" /> Back to Campaigns
      </button>
      <h1 className="text-2xl font-bold text-slate-900 mb-6">New Campaign</h1>

      <form onSubmit={handleSubmit} className="space-y-5">
        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold text-slate-700">Campaign Info</h2>
          </CardHeader>
          <CardBody className="space-y-4">
            <Input label="Campaign name *" value={form.name} onChange={set('name')} placeholder="e.g. Summer Promo 2026" />
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Campaign goal</label>
              <textarea
                className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-500 resize-none"
                rows={2}
                value={form.goal}
                onChange={set('goal')}
                placeholder="e.g. Increase brand awareness during the summer season"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Input label="Duration (days)" type="number" min={1} value={form.duration_days} onChange={set('duration_days')} placeholder="30" />
              <Input label="Posts per week" type="number" min={1} value={form.posts_per_week} onChange={set('posts_per_week')} placeholder="3" />
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold text-slate-700">Platforms</h2>
          </CardHeader>
          <CardBody>
            <div className="flex flex-wrap gap-2">
              {PLATFORMS.map(p => (
                <button
                  key={p}
                  type="button"
                  onClick={() => togglePlatform(p)}
                  className={`text-sm px-3 py-1.5 rounded-lg border font-medium transition-colors ${
                    form.platforms.includes(p)
                      ? 'bg-purple-600 text-white border-purple-600'
                      : 'bg-white text-slate-600 border-slate-200 hover:border-purple-300'
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold text-slate-700">Brief</h2>
          </CardHeader>
          <CardBody className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Target audience</label>
              <textarea
                className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-500 resize-none"
                rows={2}
                value={form.target_audience}
                onChange={set('target_audience')}
                placeholder="e.g. South African women 25–45 who are health-conscious"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Campaign objective</label>
              <textarea
                className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-500 resize-none"
                rows={2}
                value={form.objective}
                onChange={set('objective')}
                placeholder="What should the campaign achieve?"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Content themes</label>
              <textarea
                className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-500 resize-none"
                rows={2}
                value={form.content_themes}
                onChange={set('content_themes')}
                placeholder="e.g. seasonal promotions, product spotlights, customer stories"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Tone notes</label>
              <textarea
                className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-500 resize-none"
                rows={2}
                value={form.tone_notes}
                onChange={set('tone_notes')}
                placeholder="Any specific tone or style instructions for this campaign"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Operator notes</label>
              <textarea
                className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-500 resize-none"
                rows={2}
                value={form.operator_notes}
                onChange={set('operator_notes')}
                placeholder="Internal notes for the operations team"
              />
            </div>
          </CardBody>
        </Card>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <div className="flex items-center gap-3">
          <Button type="submit" loading={isPending}>
            Create Campaign
          </Button>
          <Button
            type="button"
            variant="secondary"
            onClick={() => navigate(`/clients/${clientId}/campaigns`)}
          >
            Cancel
          </Button>
        </div>
      </form>
    </div>
  )
}
