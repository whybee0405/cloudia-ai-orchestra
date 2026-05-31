import { useNavigate } from 'react-router-dom'
import type { Suggestion } from '@/shared/types'
import { Button } from './Button'
import { cn } from '@/lib/utils'
import { ArrowRight, Megaphone, Globe, BarChart2, Dna } from 'lucide-react'

const priorityConfig = {
  1: { label: 'Critical', className: 'border-l-red-500 bg-red-50/50' },
  2: { label: 'High', className: 'border-l-amber-500 bg-amber-50/30' },
  3: { label: 'Medium', className: 'border-l-blue-500 bg-blue-50/30' },
  4: { label: 'Low', className: 'border-l-slate-300 bg-white' },
}

const serviceIcon = {
  campaigns: Megaphone,
  ads: BarChart2,
  webdev: Globe,
  brand_dna: Dna,
}

interface SuggestionCardProps {
  suggestion: Suggestion
}

export function SuggestionCard({ suggestion }: SuggestionCardProps) {
  const navigate = useNavigate()
  const { label, className } = priorityConfig[suggestion.priority as keyof typeof priorityConfig] ?? priorityConfig[4]
  const Icon = serviceIcon[suggestion.service as keyof typeof serviceIcon] ?? ArrowRight

  return (
    <div className={cn('border-l-4 rounded-r-xl p-4 shadow-sm border border-l-4', className)}>
      <div className="flex items-start gap-3">
        <div className="mt-0.5 flex-shrink-0 w-7 h-7 rounded-lg bg-white border border-slate-200 flex items-center justify-center shadow-sm">
          <Icon className="w-3.5 h-3.5 text-slate-500" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <p className="text-sm font-semibold text-slate-800">{suggestion.title}</p>
            <span className="text-xs text-slate-400">{label}</span>
          </div>
          <p className="text-xs text-slate-500 leading-relaxed">{suggestion.description}</p>
        </div>
      </div>
      <div className="mt-3 flex justify-end">
        <Button variant="ghost" size="sm" onClick={() => navigate(suggestion.action_url)}>
          {suggestion.action_label}
          <ArrowRight className="w-3.5 h-3.5" />
        </Button>
      </div>
    </div>
  )
}
