import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { suggestPersonas, createPersona } from '@/api/brand-dna'
import type { PersonaArchetype } from '@/api/brand-dna'
import { Button } from '@/shared/components/Button'
import { cn } from '@/lib/utils'
import { Sparkles, Plus, CheckCircle, Users } from 'lucide-react'

interface Props {
  clientId: string
}

export function PersonaArchetypeCards({ clientId }: Props) {
  const qc = useQueryClient()
  const [archetypes, setArchetypes] = useState<PersonaArchetype[]>([])
  const [added, setAdded] = useState<Set<number>>(new Set())
  const [shown, setShown] = useState(false)

  const suggestMut = useMutation({
    mutationFn: () => suggestPersonas(clientId),
    onSuccess: (data) => { setArchetypes(data.archetypes); setShown(true) },
  })

  const addMut = useMutation({
    mutationFn: (a: PersonaArchetype) => createPersona(clientId, {
      persona_name: a.persona_name,
      age_min: a.age_min,
      age_max: a.age_max,
      gender_skew: a.gender_skew,
      income_bracket: a.income_bracket,
      location_type: a.location_type,
      interests: a.interests,
      values: a.values,
      pain_points: a.pain_points,
      goals: a.goals,
      preferred_channels: a.preferred_channels,
      seo_keywords: a.seo_keywords,
      vocabulary: a.vocabulary,
      order: 1,
    }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['personas', clientId] }),
  })

  const handleAdd = async (archetype: PersonaArchetype, idx: number) => {
    await addMut.mutateAsync(archetype)
    setAdded(prev => new Set([...prev, idx]))
  }

  if (!shown) {
    return (
      <div className="flex flex-col items-center gap-3 py-4 text-center">
        <div className="w-10 h-10 rounded-xl bg-purple-100 flex items-center justify-center">
          <Users className="w-5 h-5 text-purple-600" />
        </div>
        <div>
          <p className="text-sm font-medium text-slate-700">Get AI-suggested personas</p>
          <p className="text-xs text-slate-400 mt-0.5">We'll generate 3 archetypes based on your brand DNA</p>
        </div>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => suggestMut.mutate()}
          loading={suggestMut.isPending}
        >
          <Sparkles className="w-3.5 h-3.5" />
          Suggest Personas
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <p className="text-xs font-medium text-slate-500">Pick the personas that match your audience</p>
      {archetypes.map((a, idx) => (
        <div
          key={idx}
          className={cn(
            'rounded-xl border p-4 transition-all',
            added.has(idx) ? 'border-emerald-200 bg-emerald-50/40' : 'border-slate-200 bg-white',
          )}
        >
          <div className="flex items-start justify-between gap-3">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-2">
                <p className="text-sm font-semibold text-slate-800">{a.persona_name}</p>
                {a.age_min && a.age_max && (
                  <span className="text-xs text-slate-400">{a.age_min}–{a.age_max}</span>
                )}
                {a.income_bracket && (
                  <span className="text-xs bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded">{a.income_bracket}</span>
                )}
              </div>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs text-slate-600">
                {a.goals?.slice(0, 2).map(g => (
                  <div key={g} className="flex items-start gap-1">
                    <span className="text-emerald-500 mt-0.5 flex-shrink-0">→</span>
                    <span className="line-clamp-1">{g}</span>
                  </div>
                ))}
                {a.pain_points?.slice(0, 2).map(p => (
                  <div key={p} className="flex items-start gap-1">
                    <span className="text-red-400 mt-0.5 flex-shrink-0">✗</span>
                    <span className="line-clamp-1">{p}</span>
                  </div>
                ))}
              </div>
              {a.preferred_channels?.length ? (
                <div className="flex flex-wrap gap-1 mt-2">
                  {a.preferred_channels.map(c => (
                    <span key={c} className="text-[10px] bg-brand-50 text-brand-700 px-1.5 py-0.5 rounded-full">{c}</span>
                  ))}
                </div>
              ) : null}
            </div>
            <div className="flex-shrink-0">
              {added.has(idx) ? (
                <div className="flex items-center gap-1 text-xs text-emerald-600 font-medium">
                  <CheckCircle className="w-3.5 h-3.5" /> Added
                </div>
              ) : (
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => handleAdd(a, idx)}
                  loading={addMut.isPending}
                >
                  <Plus className="w-3.5 h-3.5" /> Add
                </Button>
              )}
            </div>
          </div>
        </div>
      ))}
      <button
        onClick={() => { setArchetypes([]); setShown(false) }}
        className="text-xs text-slate-400 hover:text-brand-600 transition-colors"
      >
        ↺ Regenerate suggestions
      </button>
    </div>
  )
}
