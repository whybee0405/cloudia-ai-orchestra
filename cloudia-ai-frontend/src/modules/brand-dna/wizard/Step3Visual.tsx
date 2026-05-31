import { useRef, useState } from 'react'
import { Card, CardBody, CardHeader } from '@/shared/components/Card'
import { Button } from '@/shared/components/Button'
import { cn } from '@/lib/utils'
import { uploadLogo } from '@/api/brand-dna'
import type { WizardData } from './BrandDNAWizard'

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

interface Props {
  clientId: string
  data: WizardData
  onChange: (patch: Partial<WizardData>) => void
  onNext: () => void
  onBack: () => void
  isSaving: boolean
}

export function Step3Visual({ clientId, data, onChange, onNext, onBack, isSaving }: Props) {
  const fileRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState('')
  const [preview, setPreview] = useState<string>(data.logo_url || '')

  const handleFile = async (file: File) => {
    setUploadError('')
    if (file.size > 5 * 1024 * 1024) {
      setUploadError('File must be under 5 MB')
      return
    }
    setPreview(URL.createObjectURL(file))
    setUploading(true)
    try {
      const { logo_url } = await uploadLogo(clientId, file)
      onChange({ logo_url })
      setPreview(logo_url)
    } catch (e: unknown) {
      setUploadError(e instanceof Error ? e.message : 'Upload failed')
      setPreview(data.logo_url || '')
    } finally {
      setUploading(false)
    }
  }

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault()
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  return (
    <Card>
      <CardHeader>
        <h2 className="text-sm font-semibold text-slate-700">Step 3 — Visual Identity</h2>
        <p className="text-xs text-slate-500 mt-0.5">Colours, fonts, and visual style that shape creative output.</p>
      </CardHeader>
      <CardBody className="space-y-5">
        {/* Visual style */}
        <div className="space-y-1">
          <label className="block text-sm font-medium text-slate-700">Visual Style</label>
          <div className="grid grid-cols-4 gap-2">
            {VISUAL_STYLES.map(vs => (
              <button
                key={vs.value}
                type="button"
                onClick={() => onChange({ visual_style: vs.value })}
                className={cn(
                  'border rounded-xl py-3 px-2 text-center transition-all',
                  data.visual_style === vs.value
                    ? 'border-brand-500 bg-brand-50 ring-2 ring-brand-500/20'
                    : 'border-slate-200 hover:border-slate-300 bg-white'
                )}
              >
                <div className="text-lg mb-1">{vs.emoji}</div>
                <p className={cn('text-xs font-medium', data.visual_style === vs.value ? 'text-brand-700' : 'text-slate-700')}>{vs.label}</p>
              </button>
            ))}
          </div>
        </div>

        {/* Colours */}
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <label className="block text-sm font-medium text-slate-700">Brand Colours</label>
            <span className="text-xs font-medium text-brand-600 bg-brand-50 px-1.5 py-0.5 rounded">Primary required</span>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div className="space-y-1">
              <label className="text-xs text-slate-500">Primary</label>
              <div className="flex items-center gap-2 border border-slate-200 rounded-lg px-2 py-1.5">
                <input
                  type="color"
                  value={data.primary_color}
                  onChange={e => onChange({ primary_color: e.target.value })}
                  className="w-8 h-8 rounded cursor-pointer border-0 bg-transparent"
                />
                <input
                  type="text"
                  value={data.primary_color}
                  onChange={e => onChange({ primary_color: e.target.value })}
                  className="flex-1 text-xs font-mono text-slate-700 outline-none bg-transparent uppercase"
                  maxLength={7}
                />
              </div>
            </div>
            <div className="space-y-1">
              <label className="text-xs text-slate-500">Accent</label>
              <div className="flex items-center gap-2 border border-slate-200 rounded-lg px-2 py-1.5">
                <input
                  type="color"
                  value={data.accent_color || '#000000'}
                  onChange={e => onChange({ accent_color: e.target.value })}
                  className="w-8 h-8 rounded cursor-pointer border-0 bg-transparent"
                />
                <input
                  type="text"
                  value={data.accent_color}
                  onChange={e => onChange({ accent_color: e.target.value })}
                  className="flex-1 text-xs font-mono text-slate-700 outline-none bg-transparent uppercase"
                  maxLength={7}
                  placeholder="#000000"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Fonts */}
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <label className="block text-sm font-medium text-slate-700">Heading Font</label>
            <select
              value={data.heading_font}
              onChange={e => onChange({ heading_font: e.target.value })}
              className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              <option value="">Select or type…</option>
              {COMMON_FONTS.map(f => <option key={f} value={f}>{f}</option>)}
            </select>
          </div>
          <div className="space-y-1">
            <label className="block text-sm font-medium text-slate-700">Body Font</label>
            <select
              value={data.body_font}
              onChange={e => onChange({ body_font: e.target.value })}
              className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              <option value="">Select or type…</option>
              {COMMON_FONTS.map(f => <option key={f} value={f}>{f}</option>)}
            </select>
          </div>
        </div>

        {/* Logo upload */}
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <label className="block text-sm font-medium text-slate-700">Logo</label>
            <span className="text-xs font-medium text-brand-600 bg-brand-50 px-1.5 py-0.5 rounded">Required</span>
          </div>
          <div
            onDrop={onDrop}
            onDragOver={e => e.preventDefault()}
            onClick={() => fileRef.current?.click()}
            className={cn(
              'relative flex flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed cursor-pointer transition-colors',
              'border-slate-200 bg-white hover:border-brand-400 hover:bg-brand-50/30',
              uploading && 'opacity-60 pointer-events-none',
              preview ? 'py-3' : 'py-8',
            )}
          >
            {preview ? (
              <div className="flex flex-col items-center gap-2">
                <img
                  src={preview}
                  alt="Logo preview"
                  className="max-h-20 max-w-48 object-contain rounded"
                />
                <p className="text-xs text-slate-400">Click or drag to replace</p>
              </div>
            ) : (
              <>
                <span className="text-2xl text-slate-300">🖼️</span>
                <p className="text-sm text-slate-500 font-medium">Drop your logo here, or click to browse</p>
                <p className="text-xs text-slate-400">PNG, JPG, SVG, WebP — max 5 MB</p>
              </>
            )}
            {uploading && (
              <div className="absolute inset-0 flex items-center justify-center bg-white/70 rounded-xl">
                <span className="text-xs text-brand-600 font-medium animate-pulse">Uploading…</span>
              </div>
            )}
          </div>
          {uploadError && <p className="text-xs text-red-500">{uploadError}</p>}
          <input
            ref={fileRef}
            type="file"
            accept={ACCEPTED}
            className="hidden"
            onChange={e => { const f = e.target.files?.[0]; if (f) handleFile(f) }}
          />
        </div>

        <div className="flex justify-between pt-2">
          <Button variant="secondary" onClick={onBack}>← Back</Button>
          <Button onClick={onNext} loading={isSaving}>Save & Continue →</Button>
        </div>
      </CardBody>
    </Card>
  )
}
