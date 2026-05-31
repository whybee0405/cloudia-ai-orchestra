import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useClient } from '@/shared/hooks/useClient'
import { generateBrandDNA, scrapeWebsite } from '@/api/brand-dna'
import type { ScrapeSignals } from '@/api/brand-dna'
import { Button } from '@/shared/components/Button'
import { ArrowLeft, Sparkles, ArrowRight, Globe } from 'lucide-react'
import { cn } from '@/lib/utils'

const LOADING_MESSAGES = [
  'Reading your brief…',
  'Crafting your brand voice…',
  'Defining your visual identity…',
  'Writing your key messages…',
  'Mapping your ideal customers…',
  'Polishing the final touches…',
]

function LoadingOverlay({ messages }: { messages: string[] }) {
  const [msgIdx, setMsgIdx] = useState(0)

  useEffect(() => {
    const t = setInterval(() => setMsgIdx(i => (i + 1) % messages.length), 1600)
    return () => clearInterval(t)
  }, [messages.length])

  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-white/95 backdrop-blur-sm">
      <div className="flex flex-col items-center gap-6 max-w-sm text-center">
        <div className="relative w-16 h-16">
          <div className="absolute inset-0 rounded-full border-4 border-brand-100" />
          <div className="absolute inset-0 rounded-full border-4 border-transparent border-t-brand-600 animate-spin" />
          <div className="absolute inset-0 flex items-center justify-center">
            <Sparkles className="w-6 h-6 text-brand-500" />
          </div>
        </div>
        <div className="space-y-1.5">
          <p className="text-base font-semibold text-slate-800 transition-all duration-300">
            {messages[msgIdx]}
          </p>
          <p className="text-xs text-slate-400">This takes about 10 seconds</p>
        </div>
        <div className="flex gap-1.5">
          {messages.map((_, i) => (
            <span
              key={i}
              className={cn(
                'w-1.5 h-1.5 rounded-full transition-all duration-300',
                i === msgIdx ? 'bg-brand-500 w-4' : 'bg-slate-200'
              )}
            />
          ))}
        </div>
      </div>
    </div>
  )
}

function SignalsPanel({ signals, onUse }: { signals: ScrapeSignals; onUse: (prompt: string) => void }) {
  return (
    <div className="rounded-xl border border-emerald-200 bg-emerald-50/60 p-4 space-y-3">
      <div className="flex items-center gap-2">
        <Globe className="w-4 h-4 text-emerald-600" />
        <p className="text-sm font-semibold text-emerald-800">Found on your website</p>
      </div>
      <p className="text-sm text-slate-700 leading-relaxed">{signals.description}</p>
      {signals.key_phrases.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {signals.key_phrases.map(p => (
            <span key={p} className="text-xs bg-white border border-emerald-200 text-emerald-700 px-2 py-0.5 rounded-full">{p}</span>
          ))}
        </div>
      )}
      {signals.tone_signals.length > 0 && (
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs text-slate-500">Tone signals:</span>
          {signals.tone_signals.map(t => (
            <span key={t} className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full capitalize">{t}</span>
          ))}
        </div>
      )}
      <button
        onClick={() => onUse(signals.suggested_prompt)}
        className="text-xs font-semibold text-emerald-700 hover:text-emerald-900 transition-colors flex items-center gap-1"
      >
        Use this as my description →
      </button>
    </div>
  )
}

export function BrandDNASetup() {
  const { clientId } = useParams<{ clientId: string }>()
  const navigate = useNavigate()
  const { data: client } = useClient(clientId!)
  const [description, setDescription] = useState('')
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState('')
  const [scraping, setScraping] = useState(false)
  const [signals, setSignals] = useState<ScrapeSignals | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const scrapeTriggered = useRef(false)

  // Auto-trigger scrape once client with website_url is loaded
  useEffect(() => {
    if (!client?.website_url || scrapeTriggered.current) return
    scrapeTriggered.current = true
    setScraping(true)
    scrapeWebsite(clientId!)
      .then(setSignals)
      .catch(() => { /* silent — scrape is best-effort */ })
      .finally(() => setScraping(false))
  }, [client, clientId])

  // Focus textarea once scrape finishes
  useEffect(() => {
    if (!scraping) textareaRef.current?.focus()
  }, [scraping])

  const buildPrompt = () => {
    const lines: string[] = []
    if (client?.name) lines.push(`Business Name: ${client.name}`)
    if (client?.industry) lines.push(`Industry: ${client.industry}`)
    if (client?.sub_industry) lines.push(`Sub-industry: ${client.sub_industry}`)
    if (client?.location) lines.push(`Location: ${client.location}`)
    if (client?.website_url) lines.push(`Website: ${client.website_url}`)
    if (lines.length) lines.push('---')
    lines.push(description.trim())
    return lines.join('\n')
  }

  const handleGenerate = async () => {
    if (!description.trim()) return
    setError('')
    setGenerating(true)
    try {
      await generateBrandDNA(clientId!, buildPrompt())
      navigate(`/clients/${clientId}/brand-dna/review?source=ai`)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Generation failed')
      setGenerating(false)
    }
  }

  return (
    <>
      {generating && <LoadingOverlay messages={LOADING_MESSAGES} />}

      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-brand-50/30 flex flex-col">
        {/* Header */}
        <div className="px-8 pt-8">
          <button
            onClick={() => navigate(`/clients/${clientId}`)}
            className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" /> Back to Hub
          </button>
        </div>

        {/* Main */}
        <div className="flex-1 flex items-center justify-center px-6 py-12">
          <div className="w-full max-w-xl space-y-5">
            {/* Title */}
            <div className="text-center space-y-2">
              <div className="inline-flex items-center gap-2 bg-brand-100 text-brand-700 text-xs font-semibold px-3 py-1.5 rounded-full">
                <Sparkles className="w-3.5 h-3.5" />
                AI-Powered Setup
              </div>
              <h1 className="text-3xl font-bold text-slate-900">
                Set up Brand DNA
                {client?.name && <span className="text-brand-600"> for {client.name}</span>}
              </h1>
              <p className="text-slate-500 text-sm">
                Describe the business and we'll generate a complete brand profile in seconds.
              </p>
            </div>

            {/* Context chips */}
            {client && (client.industry || client.location || client.website_url) && (
              <div className="flex flex-wrap gap-2 justify-center">
                {client.industry && (
                  <span className="inline-flex items-center gap-1 text-xs bg-white border border-slate-200 text-slate-600 px-2.5 py-1 rounded-full">
                    🏷 {client.industry.replace(/_/g, ' ')}
                  </span>
                )}
                {client.location && (
                  <span className="inline-flex items-center gap-1 text-xs bg-white border border-slate-200 text-slate-600 px-2.5 py-1 rounded-full">
                    📍 {client.location}
                  </span>
                )}
                {client.website_url && (
                  <span className="inline-flex items-center gap-1 text-xs bg-white border border-slate-200 text-slate-600 px-2.5 py-1 rounded-full">
                    🌐 {client.website_url.replace(/^https?:\/\//, '')}
                  </span>
                )}
              </div>
            )}

            {/* Scraping indicator */}
            {scraping && (
              <div className="flex items-center gap-2.5 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3">
                <div className="w-4 h-4 rounded-full border-2 border-emerald-300 border-t-emerald-600 animate-spin flex-shrink-0" />
                <p className="text-sm text-emerald-700">Scanning your website for brand signals…</p>
              </div>
            )}

            {/* Scraped signals panel */}
            {!scraping && signals && (
              <SignalsPanel signals={signals} onUse={setDescription} />
            )}

            {/* Prompt card */}
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
              <div className="px-5 pt-5 pb-2">
                <label className="block text-sm font-semibold text-slate-800 mb-1">
                  What makes this business different?
                </label>
                <p className="text-xs text-slate-400 mb-3">
                  What do you do, who do you serve, and what sets you apart? The more specific, the better.
                </p>
                <textarea
                  ref={textareaRef}
                  value={description}
                  onChange={e => setDescription(e.target.value)}
                  rows={5}
                  placeholder="e.g. We're a Cape Town craft roastery specialising in single-origin African beans. Our customers are specialty coffee enthusiasts aged 25–45 who care about ethical sourcing and exceptional taste. We're premium but approachable…"
                  className="w-full text-sm text-slate-800 placeholder:text-slate-300 outline-none resize-none"
                  onKeyDown={e => {
                    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleGenerate()
                  }}
                />
              </div>
              <div className="flex items-center justify-between px-5 py-3 bg-slate-50 border-t border-slate-100">
                <span className="text-xs text-slate-400">
                  {description.length > 0 ? `${description.length} chars` : '⌘↵ to generate'}
                </span>
                <Button
                  onClick={handleGenerate}
                  loading={generating}
                  disabled={!description.trim() || scraping}
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  Generate Brand DNA
                </Button>
              </div>
            </div>

            {error && (
              <p className="text-center text-sm text-red-500">{error}</p>
            )}

            {/* Manual fallback */}
            <div className="text-center">
              <button
                onClick={() => navigate(`/clients/${clientId}/brand-dna/wizard`)}
                className="inline-flex items-center gap-1.5 text-sm text-slate-400 hover:text-brand-600 transition-colors"
              >
                Set up step by step instead
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
