import { useRef, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getBrandDNA, saveBrandDNA, listPersonas, uploadLogo,
} from '@/api/brand-dna'
import { useClient } from '@/shared/hooks/useClient'
import { TagInput, Input, Textarea } from '@/shared/components/Input'
import { Button } from '@/shared/components/Button'
import { Badge } from '@/shared/components/Badge'
import { PageLoader } from '@/shared/components/LoadingSpinner'
import { CompletenessRing } from '@/shared/components/CompletenessRing'
import { getBrandDNAScore } from '@/lib/brand-dna-score'
import { cn } from '@/lib/utils'
import { CheckCircle, ChevronDown, Pencil, ArrowLeft, Sparkles } from 'lucide-react'
import type { BrandDNAUpdate } from '@/shared/types'
import { PersonaArchetypeCards } from './wizard/PersonaArchetypeCards'
import { BrandPreviewPanel } from '@/shared/components/BrandPreviewPanel'

function AiBadge({ confirmed }: { confirmed: boolean }) {
  if (confirmed) {
    return (
      <span className="inline-flex items-center gap-0.5 text-[10px] font-semibold bg-emerald-100 text-emerald-700 px-1.5 py-0.5 rounded-full">
        <CheckCircle className="w-2.5 h-2.5" /> Confirmed
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-0.5 text-[10px] font-semibold bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded-full">
      <Sparkles className="w-2.5 h-2.5" /> AI generated
    </span>
  )
}

// ── Constants (same as wizard steps) ─────────────────────────────────────────

const TONES = [
  { value: 'formal', label: 'Formal' },
  { value: 'casual', label: 'Casual' },
  { value: 'playful', label: 'Playful' },
  { value: 'authoritative', label: 'Authoritative' },
  { value: 'warm', label: 'Warm' },
]

const VISUAL_STYLES = [
  { value: 'minimalist', label: 'Minimalist', emoji: '⬜' },
  { value: 'bold', label: 'Bold', emoji: '🔥' },
  { value: 'editorial', label: 'Editorial', emoji: '📰' },
  { value: 'dark-tech', label: 'Dark Tech', emoji: '🌑' },
  { value: 'luxury', label: 'Luxury', emoji: '✨' },
  { value: 'warm', label: 'Warm', emoji: '🌿' },
  { value: 'playful', label: 'Playful', emoji: '🎨' },
  { value: 'corporate', label: 'Corporate', emoji: '🏢' },
]

const COMMON_FONTS = [
  'Inter', 'Montserrat', 'Poppins', 'Playfair Display', 'Lora',
  'Raleway', 'Source Sans Pro', 'DM Sans', 'Nunito', 'Roboto',
]

const ACCEPTED = 'image/png,image/jpeg,image/svg+xml,image/webp'

type SectionKey = 'voice' | 'visual' | 'messaging' | 'personas'

// ── Draft state type ──────────────────────────────────────────────────────────

interface Draft {
  tagline: string
  tone: string
  language_style: string
  personality_traits: string[]
  visual_style: string
  primary_color: string
  accent_color: string
  heading_font: string
  body_font: string
  logo_url: string
  usps: string[]
  pain_points_addressed: string[]
  key_messages: string[]
  competitors: string[]
  differentiators: string[]
}

// ── Section wrapper ───────────────────────────────────────────────────────────

function Section({
  title, isOpen, isConfirmed, onToggle, onConfirm, isSaving, summary, children, showAiBadge,
}: {
  title: string
  isOpen: boolean
  isConfirmed: boolean
  onToggle: () => void
  onConfirm: () => void
  isSaving: boolean
  summary: React.ReactNode
  children: React.ReactNode
  showAiBadge?: boolean
}) {
  return (
    <div className={cn(
      'rounded-2xl border transition-all',
      isConfirmed ? 'border-emerald-200 bg-white' : 'border-slate-200 bg-white',
      isOpen && 'ring-2 ring-brand-100 border-brand-200',
    )}>
      <button
        type="button"
        onClick={onToggle}
        className="w-full flex items-center gap-3 px-5 py-4 text-left"
      >
        <div className={cn(
          'w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 transition-colors',
          isConfirmed ? 'bg-emerald-500' : isOpen ? 'bg-brand-500' : 'bg-slate-200',
        )}>
          {isConfirmed
            ? <CheckCircle className="w-3.5 h-3.5 text-white" />
            : <Pencil className="w-3 h-3 text-white" />}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <p className="text-sm font-semibold text-slate-800">{title}</p>
            {showAiBadge && <AiBadge confirmed={isConfirmed} />}
          </div>
          {!isOpen && <div className="mt-1">{summary}</div>}
        </div>
        <ChevronDown className={cn('w-4 h-4 text-slate-400 flex-shrink-0 transition-transform', isOpen && 'rotate-180')} />
      </button>

      {isOpen && (
        <div className="px-5 pb-5 space-y-4 border-t border-slate-100 pt-4">
          {children}
          <div className="flex items-center justify-between pt-2">
            <button
              onClick={onToggle}
              className="text-xs text-slate-400 hover:text-slate-600 transition-colors"
            >
              Collapse
            </button>
            <Button size="sm" onClick={onConfirm} loading={isSaving}>
              <CheckCircle className="w-3.5 h-3.5" />
              Looks good ✓
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export function BrandDNAReviewPage() {
  const { clientId } = useParams<{ clientId: string }>()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const isAiSource = searchParams.get('source') === 'ai'
  const qc = useQueryClient()

  const { data: client } = useClient(clientId!)
  const { data: brandDna, isLoading } = useQuery({
    queryKey: ['brand-dna', clientId],
    queryFn: () => getBrandDNA(clientId!),
    retry: false,
  })
  const { data: personas } = useQuery({
    queryKey: ['personas', clientId],
    queryFn: () => listPersonas(clientId!),
  })

  const [draft, setDraft] = useState<Draft | null>(null)
  const [open, setOpen] = useState<Set<SectionKey>>(new Set<SectionKey>(['voice']))
  const [confirmed, setConfirmed] = useState<Set<SectionKey>>(new Set())
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState('')
  const [logoPreview, setLogoPreview] = useState('')
  const fileRef = useRef<HTMLInputElement>(null)

  // Initialise draft from loaded brand DNA (once)
  const draftInitialised = useRef(false)
  if (brandDna && !draftInitialised.current) {
    draftInitialised.current = true
    setDraft({
      tagline: brandDna.tagline ?? '',
      tone: brandDna.tone ?? '',
      language_style: brandDna.language_style ?? '',
      personality_traits: brandDna.personality_traits ?? [],
      visual_style: brandDna.visual_style ?? '',
      primary_color: brandDna.primary_color ?? '#6366f1',
      accent_color: brandDna.accent_color ?? '',
      heading_font: brandDna.heading_font ?? '',
      body_font: brandDna.body_font ?? '',
      logo_url: brandDna.logo_url ?? '',
      usps: brandDna.usps ?? [],
      pain_points_addressed: brandDna.pain_points_addressed ?? [],
      key_messages: brandDna.key_messages ?? [],
      competitors: brandDna.competitors ?? [],
      differentiators: brandDna.differentiators ?? [],
    })
    if (brandDna.logo_url) setLogoPreview(brandDna.logo_url)
  }

  const patch = (p: Partial<Draft>) => setDraft(d => d ? { ...d, ...p } : d)

  const saveMut = useMutation({
    mutationFn: (payload: BrandDNAUpdate) => saveBrandDNA(clientId!, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['brand-dna', clientId] }),
  })

  const buildPayload = (): BrandDNAUpdate => ({
    tagline: draft?.tagline || undefined,
    tone: draft?.tone || undefined,
    language_style: draft?.language_style || undefined,
    personality_traits: draft?.personality_traits?.length ? draft.personality_traits : undefined,
    visual_style: draft?.visual_style || undefined,
    primary_color: draft?.primary_color || undefined,
    accent_color: draft?.accent_color || undefined,
    heading_font: draft?.heading_font || undefined,
    body_font: draft?.body_font || undefined,
    logo_url: draft?.logo_url || undefined,
    usps: draft?.usps?.length ? draft.usps : undefined,
    pain_points_addressed: draft?.pain_points_addressed?.length ? draft.pain_points_addressed : undefined,
    key_messages: draft?.key_messages?.length ? draft.key_messages : undefined,
    competitors: draft?.competitors?.length ? draft.competitors : undefined,
    differentiators: draft?.differentiators?.length ? draft.differentiators : undefined,
  })

  const toggleSection = (key: SectionKey) => {
    setOpen(prev => {
      const s = new Set(prev)
      s.has(key) ? s.delete(key) : s.add(key)
      return s
    })
  }

  const confirmSection = async (key: SectionKey) => {
    await saveMut.mutateAsync(buildPayload())
    setConfirmed(prev => new Set([...prev, key]))
    setOpen(prev => { const s = new Set(prev); s.delete(key); return s })
  }

  const handleLogoFile = async (file: File) => {
    setUploadError('')
    if (file.size > 5 * 1024 * 1024) { setUploadError('File must be under 5 MB'); return }
    setLogoPreview(URL.createObjectURL(file))
    setUploading(true)
    try {
      const { logo_url } = await uploadLogo(clientId!, file)
      patch({ logo_url })
      setLogoPreview(logo_url)
    } catch (e: unknown) {
      setUploadError(e instanceof Error ? e.message : 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  const handleFinish = async () => {
    await saveMut.mutateAsync(buildPayload())
    qc.invalidateQueries({ queryKey: ['clients'] })
    qc.invalidateQueries({ queryKey: ['brand-dna', clientId] })
    navigate(`/clients/${clientId}/brand-dna`)
  }

  const { score } = getBrandDNAScore(client, brandDna, personas?.length ?? 0)

  if (isLoading || !draft) return <PageLoader />

  // ── Section summaries (collapsed state) ─────────────────────────────────

  const voiceSummary = (
    <div className="flex flex-wrap items-center gap-1.5">
      {draft.tone && <span className="text-xs bg-brand-50 text-brand-700 px-2 py-0.5 rounded-full capitalize">{draft.tone}</span>}
      {draft.tagline && <span className="text-xs text-slate-500 italic truncate max-w-xs">"{draft.tagline}"</span>}
    </div>
  )

  const visualSummary = (
    <div className="flex items-center gap-2">
      {draft.primary_color && (
        <span className="w-4 h-4 rounded-full border border-slate-200 flex-shrink-0" style={{ backgroundColor: draft.primary_color }} />
      )}
      {draft.visual_style && <span className="text-xs text-slate-500 capitalize">{draft.visual_style}</span>}
      {draft.heading_font && <span className="text-xs text-slate-400">{draft.heading_font}</span>}
      {logoPreview && <img src={logoPreview} alt="logo" className="h-5 object-contain rounded" />}
    </div>
  )

  const messagingSummary = (
    <div className="flex flex-wrap gap-1">
      {draft.usps.slice(0, 3).map(u => (
        <span key={u} className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded-md">{u}</span>
      ))}
      {draft.usps.length > 3 && <span className="text-xs text-slate-400">+{draft.usps.length - 3} more</span>}
      {draft.usps.length === 0 && <span className="text-xs text-slate-400">No USPs yet</span>}
    </div>
  )

  const personasSummary = (
    <div className="flex flex-wrap gap-1">
      {personas?.length
        ? personas.map(p => <Badge key={p.id}>{p.persona_name}</Badge>)
        : <span className="text-xs text-slate-400">No personas yet</span>}
    </div>
  )

  return (
    <div className="min-h-screen bg-slate-50 p-6 md:p-10">
      <div className="max-w-2xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <button
              onClick={() => navigate(`/clients/${clientId}`)}
              className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-slate-700 mb-2 transition-colors"
            >
              <ArrowLeft className="w-4 h-4" /> Back to Hub
            </button>
            <h1 className="text-2xl font-bold text-slate-900">
              Review Brand DNA
              {client?.name && <span className="text-slate-400 font-normal"> — {client.name}</span>}
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              Confirm each section below. Click any section to edit inline.
            </p>
          </div>
          <CompletenessRing score={score} size={52} strokeWidth={5} />
        </div>

        {/* Live preview panel */}
        {draft && (
          <BrandPreviewPanel snapshot={{
            tagline: draft.tagline,
            tone: draft.tone,
            language_style: draft.language_style,
            personality_traits: draft.personality_traits,
            visual_style: draft.visual_style,
            primary_color: draft.primary_color,
            accent_color: draft.accent_color,
            heading_font: draft.heading_font,
            usps: draft.usps,
            key_messages: draft.key_messages,
          }} />
        )}

        {/* Sections */}
        <Section
          title="Brand Voice"
          isOpen={open.has('voice')}
          isConfirmed={confirmed.has('voice')}
          onToggle={() => toggleSection('voice')}
          onConfirm={() => confirmSection('voice')}
          isSaving={saveMut.isPending}
          summary={voiceSummary}
          showAiBadge={isAiSource}
        >
          <Input
            label="Tagline *"
            value={draft.tagline}
            onChange={e => patch({ tagline: e.target.value })}
            placeholder="e.g. Where every meal tells a story"
          />
          <div className="space-y-1.5">
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium text-slate-700">Tone *</label>
              <span className="text-xs font-medium text-brand-600 bg-brand-50 px-1.5 py-0.5 rounded">Required</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {TONES.map(t => (
                <button
                  key={t.value}
                  type="button"
                  onClick={() => patch({ tone: t.value })}
                  className={cn(
                    'border rounded-lg px-3 py-1.5 text-xs font-medium transition-all',
                    draft.tone === t.value
                      ? 'border-brand-500 bg-brand-50 text-brand-700 ring-2 ring-brand-500/20'
                      : 'border-slate-200 text-slate-600 hover:border-slate-300 bg-white'
                  )}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>
          <Textarea
            label="Language Style"
            value={draft.language_style}
            onChange={e => patch({ language_style: e.target.value })}
            rows={3}
            placeholder="Describe how the brand writes — vocabulary, sentence structure, local nuances…"
          />
          <TagInput
            label="Personality Traits"
            tags={draft.personality_traits}
            onChange={v => patch({ personality_traits: v })}
            placeholder="e.g. Innovative — press Enter"
          />
        </Section>

        <Section
          title="Visual Identity"
          isOpen={open.has('visual')}
          isConfirmed={confirmed.has('visual')}
          onToggle={() => toggleSection('visual')}
          onConfirm={() => confirmSection('visual')}
          isSaving={saveMut.isPending}
          summary={visualSummary}
          showAiBadge={isAiSource}
        >
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-slate-700">Visual Style</label>
            <div className="grid grid-cols-4 gap-2">
              {VISUAL_STYLES.map(vs => (
                <button
                  key={vs.value}
                  type="button"
                  onClick={() => patch({ visual_style: vs.value })}
                  className={cn(
                    'border rounded-xl py-2.5 px-2 text-center transition-all',
                    draft.visual_style === vs.value
                      ? 'border-brand-500 bg-brand-50 ring-2 ring-brand-500/20'
                      : 'border-slate-200 hover:border-slate-300 bg-white'
                  )}
                >
                  <div className="text-base mb-0.5">{vs.emoji}</div>
                  <p className={cn('text-xs font-medium', draft.visual_style === vs.value ? 'text-brand-700' : 'text-slate-700')}>
                    {vs.label}
                  </p>
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-xs font-medium text-slate-700">Primary Colour *</label>
              <div className="flex items-center gap-2 border border-slate-200 rounded-lg px-2 py-1.5">
                <input type="color" value={draft.primary_color}
                  onChange={e => patch({ primary_color: e.target.value })}
                  className="w-8 h-8 rounded cursor-pointer border-0 bg-transparent" />
                <input type="text" value={draft.primary_color}
                  onChange={e => patch({ primary_color: e.target.value })}
                  className="flex-1 text-xs font-mono outline-none bg-transparent uppercase" maxLength={7} />
              </div>
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium text-slate-700">Accent Colour</label>
              <div className="flex items-center gap-2 border border-slate-200 rounded-lg px-2 py-1.5">
                <input type="color" value={draft.accent_color || '#000000'}
                  onChange={e => patch({ accent_color: e.target.value })}
                  className="w-8 h-8 rounded cursor-pointer border-0 bg-transparent" />
                <input type="text" value={draft.accent_color}
                  onChange={e => patch({ accent_color: e.target.value })}
                  className="flex-1 text-xs font-mono outline-none bg-transparent uppercase" maxLength={7} placeholder="#000000" />
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-700">Heading Font</label>
              <select value={draft.heading_font} onChange={e => patch({ heading_font: e.target.value })}
                className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500">
                <option value="">Select…</option>
                {COMMON_FONTS.map(f => <option key={f}>{f}</option>)}
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-700">Body Font</label>
              <select value={draft.body_font} onChange={e => patch({ body_font: e.target.value })}
                className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500">
                <option value="">Select…</option>
                {COMMON_FONTS.map(f => <option key={f}>{f}</option>)}
              </select>
            </div>
          </div>

          {/* Logo upload */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium text-slate-700">Logo</label>
              <span className="text-xs font-medium text-brand-600 bg-brand-50 px-1.5 py-0.5 rounded">Required</span>
            </div>
            <div
              onDrop={e => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) handleLogoFile(f) }}
              onDragOver={e => e.preventDefault()}
              onClick={() => fileRef.current?.click()}
              className={cn(
                'flex flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed cursor-pointer transition-colors',
                'border-slate-200 bg-white hover:border-brand-400 hover:bg-brand-50/30',
                (uploading) && 'opacity-60 pointer-events-none',
                logoPreview ? 'py-3' : 'py-6',
              )}
            >
              {logoPreview
                ? <img src={logoPreview} alt="Logo" className="max-h-16 max-w-40 object-contain rounded" />
                : <p className="text-xs text-slate-400">Drop logo here or click to browse — PNG, SVG, WebP · max 5 MB</p>}
              {uploading && <p className="text-xs text-brand-600 animate-pulse">Uploading…</p>}
            </div>
            {uploadError && <p className="text-xs text-red-500">{uploadError}</p>}
            <input ref={fileRef} type="file" accept={ACCEPTED} className="hidden"
              onChange={e => { const f = e.target.files?.[0]; if (f) handleLogoFile(f) }} />
          </div>
        </Section>

        <Section
          title="Key Messages"
          isOpen={open.has('messaging')}
          isConfirmed={confirmed.has('messaging')}
          onToggle={() => toggleSection('messaging')}
          onConfirm={() => confirmSection('messaging')}
          isSaving={saveMut.isPending}
          summary={messagingSummary}
          showAiBadge={isAiSource}
        >
          <TagInput
            label="Unique Selling Propositions (USPs) *"
            tags={draft.usps}
            onChange={v => patch({ usps: v })}
            placeholder="e.g. Fastest delivery in Joburg — press Enter"
            hint="What makes this business genuinely different"
          />
          <TagInput
            label="Pain Points Addressed"
            tags={draft.pain_points_addressed}
            onChange={v => patch({ pain_points_addressed: v })}
            placeholder="e.g. No more waiting 2 hours for a quote — press Enter"
          />
          <TagInput
            label="Key Messages"
            tags={draft.key_messages}
            onChange={v => patch({ key_messages: v })}
            placeholder="e.g. Quality you can taste in every bite — press Enter"
          />
          <TagInput
            label="Competitors"
            tags={draft.competitors}
            onChange={v => patch({ competitors: v })}
            placeholder="e.g. Takealot — press Enter"
          />
          <TagInput
            label="Differentiators"
            tags={draft.differentiators}
            onChange={v => patch({ differentiators: v })}
            placeholder="e.g. Family-owned, locally sourced — press Enter"
          />
        </Section>

        <Section
          title="ICP Personas"
          isOpen={open.has('personas')}
          isConfirmed={confirmed.has('personas')}
          onToggle={() => toggleSection('personas')}
          onConfirm={() => confirmSection('personas')}
          isSaving={saveMut.isPending}
          summary={personasSummary}
        >
          {/* Added personas */}
          {personas && personas.length > 0 && (
            <div className="space-y-2 mb-2">
              {personas.map(p => (
                <div key={p.id} className="flex items-start gap-3 border border-emerald-200 bg-emerald-50/30 rounded-xl px-4 py-3">
                  <CheckCircle className="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-semibold text-slate-800">{p.persona_name}</p>
                    {p.goals?.length ? (
                      <p className="text-xs text-slate-500 mt-0.5">{p.goals.slice(0, 2).join(' · ')}</p>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* AI archetype suggestions */}
          <PersonaArchetypeCards clientId={clientId!} />

          <button
            onClick={() => navigate(`/clients/${clientId}/brand-dna/wizard`)}
            className="text-xs text-brand-600 hover:text-brand-800 font-medium transition-colors mt-2"
          >
            Manage personas in full editor →
          </button>
        </Section>

        {/* Complete button */}
        <div className="flex items-center justify-between pt-2 pb-8">
          <p className="text-xs text-slate-400">
            {confirmed.size} of 4 sections confirmed
          </p>
          <Button onClick={handleFinish} loading={saveMut.isPending}>
            <CheckCircle className="w-4 h-4" />
            Save & Complete
          </Button>
        </div>
      </div>
    </div>
  )
}
