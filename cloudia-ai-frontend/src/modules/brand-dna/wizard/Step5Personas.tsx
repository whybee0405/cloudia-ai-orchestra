import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listPersonas, createPersona, deletePersona, getPersonaTemplates } from '@/api/brand-dna'
import type { ICPPersona, PersonaCreate, PersonaTemplate } from '@/shared/types'
import { Card, CardBody, CardHeader } from '@/shared/components/Card'
import { Button } from '@/shared/components/Button'
import { Input, TagInput } from '@/shared/components/Input'
import { Users, Plus, Trash2, ChevronDown, ChevronUp } from 'lucide-react'
import type { WizardData } from './BrandDNAWizard'

interface Props {
  clientId: string
  data: WizardData
  onChange: (patch: Partial<WizardData>) => void
  onNext: () => void
  onBack: () => void
  isSaving: boolean
}

const BLANK_PERSONA: PersonaCreate = {
  persona_name: '', age_min: undefined, age_max: undefined,
  gender_skew: 'balanced', income_bracket: 'middle', location_type: 'urban',
  interests: [], values: [], pain_points: [], goals: [],
  preferred_channels: [], seo_keywords: [], vocabulary: [], order: 1,
}

export function Step5Personas({ clientId, data, onNext, onBack }: Props) {
  const qc = useQueryClient()
  const [expanded, setExpanded] = useState<number | null>(null)
  const [showTemplates, setShowTemplates] = useState(false)
  const [newPersona, setNewPersona] = useState<PersonaCreate | null>(null)

  const { data: personas } = useQuery({ queryKey: ['personas', clientId], queryFn: () => listPersonas(clientId) })
  const { data: templates } = useQuery({ queryKey: ['persona-templates'], queryFn: () => getPersonaTemplates() })

  const createMut = useMutation({
    mutationFn: (p: PersonaCreate) => createPersona(clientId, p),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['personas', clientId] }); setNewPersona(null) },
  })

  const deleteMut = useMutation({
    mutationFn: (id: number) => deletePersona(clientId, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['personas', clientId] }),
  })

  const addFromTemplate = (tpl: PersonaTemplate) => {
    createMut.mutate({ ...tpl, order: (personas?.length ?? 0) + 1 })
    setShowTemplates(false)
  }

  const pList = personas ?? []

  return (
    <Card>
      <CardHeader>
        <h2 className="text-sm font-semibold text-slate-700">Step 5 — ICP Personas</h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Define 1–5 ideal customer profiles. These drive SEO keywords and copy tone across all agent outputs.
        </p>
      </CardHeader>
      <CardBody className="space-y-4">
        {/* Existing personas */}
        {pList.length === 0 && !newPersona && (
          <div className="text-center py-6 border-2 border-dashed border-slate-200 rounded-xl">
            <Users className="w-8 h-8 text-slate-300 mx-auto mb-2" />
            <p className="text-sm text-slate-500">No personas yet. Add one from templates or from scratch.</p>
          </div>
        )}

        {pList.map(p => (
          <PersonaRow
            key={p.id}
            persona={p}
            expanded={expanded === p.id}
            onToggle={() => setExpanded(expanded === p.id ? null : p.id)}
            onDelete={() => deleteMut.mutate(p.id)}
          />
        ))}

        {/* New persona form */}
        {newPersona && (
          <NewPersonaForm
            value={newPersona}
            onChange={setNewPersona}
            onSave={() => createMut.mutate({ ...newPersona, order: pList.length + 1 })}
            onCancel={() => setNewPersona(null)}
            isSaving={createMut.isPending}
          />
        )}

        {/* Actions */}
        {pList.length < 5 && !newPersona && (
          <div className="flex gap-2">
            <Button variant="secondary" size="sm" onClick={() => setNewPersona({ ...BLANK_PERSONA })}>
              <Plus className="w-3.5 h-3.5" /> Add from scratch
            </Button>
            <Button variant="secondary" size="sm" onClick={() => setShowTemplates(s => !s)}>
              Use template
            </Button>
          </div>
        )}

        {/* Template gallery */}
        {showTemplates && templates && (
          <div className="border border-slate-200 rounded-xl overflow-hidden">
            <div className="px-4 py-2 bg-slate-50 border-b border-slate-200">
              <p className="text-xs font-semibold text-slate-600">Industry Templates — {data.industry ? data.industry.replace(/_/g, ' ') : 'Select an industry in Step 1 for tailored options'}</p>
            </div>
            <div className="divide-y divide-slate-100 max-h-64 overflow-y-auto">
              {(data.industry ? (templates.templates[data.industry] ?? []) : Object.values(templates.templates).flat()).map((tpl, i) => (
                <button
                  key={i}
                  onClick={() => addFromTemplate(tpl)}
                  className="w-full text-left px-4 py-3 hover:bg-brand-50 transition-colors"
                >
                  <p className="text-sm font-medium text-slate-800">{tpl.persona_name}</p>
                  <p className="text-xs text-slate-500">Age {tpl.age_min}–{tpl.age_max} · {tpl.income_bracket} income · {tpl.location_type}</p>
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="flex justify-between pt-2">
          <Button variant="secondary" onClick={onBack}>← Back</Button>
          <Button onClick={onNext}>Continue →</Button>
        </div>
      </CardBody>
    </Card>
  )
}

function PersonaRow({ persona, expanded, onToggle, onDelete }: {
  persona: ICPPersona
  expanded: boolean
  onToggle: () => void
  onDelete: () => void
}) {
  return (
    <div className="border border-slate-200 rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 cursor-pointer hover:bg-slate-50" onClick={onToggle}>
        <div>
          <p className="text-sm font-medium text-slate-800">{persona.persona_name}</p>
          <p className="text-xs text-slate-500">
            {persona.age_min && persona.age_max ? `Age ${persona.age_min}–${persona.age_max}` : ''}
            {persona.seo_keywords?.length ? ` · ${persona.seo_keywords.length} keywords` : ''}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={e => { e.stopPropagation(); onDelete() }} className="text-slate-400 hover:text-red-500 transition-colors">
            <Trash2 className="w-3.5 h-3.5" />
          </button>
          {expanded ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
        </div>
      </div>
      {expanded && (
        <div className="px-4 pb-4 pt-2 border-t border-slate-100 space-y-2">
          {persona.seo_keywords?.length ? (
            <div>
              <p className="text-xs font-medium text-slate-500 mb-1">SEO Keywords</p>
              <div className="flex flex-wrap gap-1">
                {persona.seo_keywords.map(k => (
                  <span key={k} className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded-md">{k}</span>
                ))}
              </div>
            </div>
          ) : null}
          {persona.vocabulary?.length ? (
            <div>
              <p className="text-xs font-medium text-slate-500 mb-1">Vocabulary</p>
              <p className="text-xs text-slate-600">{persona.vocabulary.join(', ')}</p>
            </div>
          ) : null}
        </div>
      )}
    </div>
  )
}

function NewPersonaForm({ value, onChange, onSave, onCancel, isSaving }: {
  value: PersonaCreate
  onChange: (v: PersonaCreate) => void
  onSave: () => void
  onCancel: () => void
  isSaving: boolean
}) {
  const set = (patch: Partial<PersonaCreate>) => onChange({ ...value, ...patch })
  return (
    <div className="border-2 border-brand-200 rounded-xl p-4 space-y-4 bg-brand-50/30">
      <p className="text-sm font-semibold text-slate-700">New Persona</p>
      <Input label="Persona Name" value={value.persona_name} onChange={e => set({ persona_name: e.target.value })} placeholder="e.g. The Busy Professional" />
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <Input label="Age Min" type="number" value={value.age_min ?? ''} onChange={e => set({ age_min: parseInt(e.target.value) || undefined })} />
        <Input label="Age Max" type="number" value={value.age_max ?? ''} onChange={e => set({ age_max: parseInt(e.target.value) || undefined })} />
      </div>
      <TagInput label="SEO Keywords" tags={value.seo_keywords ?? []} onChange={v => set({ seo_keywords: v })} placeholder="e.g. gym near me — press Enter" />
      <TagInput label="Vocabulary / Language Cues" tags={value.vocabulary ?? []} onChange={v => set({ vocabulary: v })} placeholder="e.g. hustle, gains — press Enter" />
      <TagInput label="Pain Points" tags={value.pain_points ?? []} onChange={v => set({ pain_points: v })} placeholder="press Enter to add" />
      <TagInput label="Goals" tags={value.goals ?? []} onChange={v => set({ goals: v })} placeholder="press Enter to add" />
      <div className="flex gap-2 justify-end">
        <Button variant="secondary" size="sm" onClick={onCancel}>Cancel</Button>
        <Button size="sm" onClick={onSave} loading={isSaving}>Save Persona</Button>
      </div>
    </div>
  )
}
