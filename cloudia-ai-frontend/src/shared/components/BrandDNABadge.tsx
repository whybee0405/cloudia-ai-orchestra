import type { BrandDNA } from '@/shared/types'
import { Palette, MessageSquare, Users } from 'lucide-react'

interface BrandDNABadgeProps {
  brandDna?: BrandDNA | null
  personaCount?: number
  compact?: boolean
}

export function BrandDNABadge({ brandDna, personaCount = 0, compact = false }: BrandDNABadgeProps) {
  if (!brandDna) {
    return (
      <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-amber-50 border border-amber-200 text-xs text-amber-700 font-medium">
        <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
        Brand DNA incomplete
      </div>
    )
  }

  if (compact) {
    return (
      <div className="inline-flex items-center gap-2">
        {brandDna.primary_color && (
          <span
            className="w-4 h-4 rounded-full border border-slate-200 flex-shrink-0"
            style={{ backgroundColor: brandDna.primary_color }}
          />
        )}
        {brandDna.tone && (
          <span className="text-xs text-slate-600 capitalize">{brandDna.tone}</span>
        )}
        {brandDna.visual_style && (
          <span className="text-xs text-slate-400">· {brandDna.visual_style}</span>
        )}
      </div>
    )
  }

  return (
    <div className="flex flex-wrap items-center gap-3 text-sm text-slate-600">
      {brandDna.tone && (
        <div className="flex items-center gap-1.5">
          <MessageSquare className="w-3.5 h-3.5 text-slate-400" />
          <span className="capitalize">{brandDna.tone} voice</span>
        </div>
      )}
      {brandDna.visual_style && (
        <div className="flex items-center gap-1.5">
          <Palette className="w-3.5 h-3.5 text-slate-400" />
          <span className="capitalize">{brandDna.visual_style}</span>
          {brandDna.primary_color && (
            <span
              className="w-3.5 h-3.5 rounded-full border border-slate-200"
              style={{ backgroundColor: brandDna.primary_color }}
            />
          )}
        </div>
      )}
      {personaCount > 0 && (
        <div className="flex items-center gap-1.5">
          <Users className="w-3.5 h-3.5 text-slate-400" />
          <span>{personaCount} persona{personaCount !== 1 ? 's' : ''}</span>
        </div>
      )}
    </div>
  )
}
