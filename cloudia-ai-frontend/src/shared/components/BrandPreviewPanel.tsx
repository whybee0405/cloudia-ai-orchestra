import { useState, useEffect, useRef } from 'react'
import { cn } from '@/lib/utils'
import { Eye, EyeOff, Copy, CheckCircle } from 'lucide-react'

interface BrandSnapshot {
  tagline?: string
  tone?: string
  language_style?: string
  personality_traits?: string[]
  visual_style?: string
  primary_color?: string
  accent_color?: string
  heading_font?: string
  usps?: string[]
  key_messages?: string[]
}

function toneAdjective(tone: string): string {
  const map: Record<string, string> = {
    formal: 'professional and authoritative',
    casual: 'friendly and conversational',
    playful: 'energetic and fun',
    authoritative: 'confident and expert',
    warm: 'caring and personal',
  }
  return map[tone] ?? tone
}

function buildSocialCaption(s: BrandSnapshot): string {
  if (!s.tagline && !s.usps?.length && !s.tone) return '— Fill in your tagline and tone to see a sample caption'
  const usp = s.usps?.[0] ?? s.key_messages?.[0] ?? ''
  const trait = s.personality_traits?.[0] ?? ''
  const tone = s.tone ? toneAdjective(s.tone) : 'compelling'
  const opener = s.tagline ? `"${s.tagline}" ` : ''
  return `${opener}${usp ? `${usp}. ` : ''}${trait ? `We're ${trait.toLowerCase()} and we bring that to everything we do. ` : ''}Written in a ${tone} voice that resonates with your audience. #BrandDNA`
}

function buildAdHeadline(s: BrandSnapshot): string {
  if (!s.tagline && !s.usps?.length) return '— Add a tagline or USPs to preview your ad headline'
  const usp = s.usps?.[0] ?? ''
  if (s.tagline && usp) return `${s.tagline} | ${usp}`
  return s.tagline ?? usp ?? '—'
}

function buildEmailSubject(s: BrandSnapshot): string {
  if (!s.key_messages?.length && !s.usps?.length && !s.tone) return '— Add key messages to preview your email subject'
  const msg = s.key_messages?.[0] ?? s.usps?.[1] ?? s.usps?.[0] ?? ''
  const tone = s.tone
  if (tone === 'playful') return `✨ ${msg} — You deserve this`
  if (tone === 'formal') return `A message about ${msg}`
  if (tone === 'warm') return `Here's something we think you'll love — ${msg}`
  if (tone === 'authoritative') return `Why ${msg} matters`
  return `Discover: ${msg}`
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  const copy = () => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }
  return (
    <button onClick={copy} className="text-slate-300 hover:text-slate-500 transition-colors flex-shrink-0">
      {copied ? <CheckCircle className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
    </button>
  )
}

function SampleCard({
  label, emoji, content,
}: { label: string; emoji: string; content: string }) {
  const isPlaceholder = content.startsWith('—')
  return (
    <div className="rounded-xl border border-slate-100 bg-slate-50/50 p-3 space-y-2">
      <div className="flex items-center gap-1.5">
        <span className="text-sm">{emoji}</span>
        <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wide">{label}</span>
      </div>
      <div className="flex items-start justify-between gap-2">
        <p className={cn(
          'text-xs leading-relaxed',
          isPlaceholder ? 'text-slate-300 italic' : 'text-slate-700'
        )}>
          {content}
        </p>
        {!isPlaceholder && <CopyButton text={content} />}
      </div>
    </div>
  )
}

interface Props {
  snapshot: BrandSnapshot
}

export function BrandPreviewPanel({ snapshot }: Props) {
  const [open, setOpen] = useState(true)
  const [previews, setPreviews] = useState({
    social: buildSocialCaption(snapshot),
    headline: buildAdHeadline(snapshot),
    email: buildEmailSubject(snapshot),
  })

  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => {
      setPreviews({
        social: buildSocialCaption(snapshot),
        headline: buildAdHeadline(snapshot),
        email: buildEmailSubject(snapshot),
      })
    }, 500)
    return () => { if (timerRef.current) clearTimeout(timerRef.current) }
  }, [
    snapshot.tagline, snapshot.tone, snapshot.personality_traits,
    snapshot.usps, snapshot.key_messages, snapshot.language_style,
  ])

  return (
    <div className="rounded-2xl border border-slate-200 bg-white overflow-hidden shadow-sm">
      {/* Header */}
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-50 transition-colors"
      >
        <div className="flex items-center gap-2">
          {open ? <Eye className="w-3.5 h-3.5 text-brand-500" /> : <EyeOff className="w-3.5 h-3.5 text-slate-400" />}
          <span className="text-xs font-semibold text-slate-700">Live Brand Preview</span>
          <span className="text-[10px] text-slate-400">updates as you type</span>
        </div>
        {/* Colour swatches */}
        <div className="flex items-center gap-1.5">
          {snapshot.primary_color && (
            <span
              className="w-4 h-4 rounded-full border border-slate-200 flex-shrink-0"
              style={{ backgroundColor: snapshot.primary_color }}
              title="Primary"
            />
          )}
          {snapshot.accent_color && (
            <span
              className="w-4 h-4 rounded-full border border-slate-200 flex-shrink-0"
              style={{ backgroundColor: snapshot.accent_color }}
              title="Accent"
            />
          )}
          {snapshot.heading_font && (
            <span className="text-[10px] text-slate-400 ml-1">{snapshot.heading_font}</span>
          )}
        </div>
      </button>

      {open && (
        <div className="px-4 pb-4 space-y-2 border-t border-slate-100">
          <SampleCard label="Social Caption" emoji="📱" content={previews.social} />
          <SampleCard label="Ad Headline" emoji="📣" content={previews.headline} />
          <SampleCard label="Email Subject" emoji="✉️" content={previews.email} />
        </div>
      )}
    </div>
  )
}
