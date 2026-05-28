import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Globe, ShoppingBag, Code2 } from 'lucide-react'
import { createProject } from '@/api/webdev'
import { Card, CardBody, CardHeader } from '@/shared/components/Card'
import { Button } from '@/shared/components/Button'
import { Input } from '@/shared/components/Input'

const PLATFORMS = [
  { id: 'wordpress', label: 'WordPress', icon: Globe },
  { id: 'shopify', label: 'Shopify', icon: ShoppingBag },
] as const

type Platform = 'wordpress' | 'shopify'

export function NewProjectForm({ webdevClientId }: { webdevClientId: number }) {
  const { clientId } = useParams<{ clientId: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()

  const [platform, setPlatform] = useState<Platform>('wordpress')
  const [projectName, setProjectName] = useState('')
  const [description, setDescription] = useState('')
  const [targetAudience, setTargetAudience] = useState('')
  const [pages, setPages] = useState('')
  const [tone, setTone] = useState('professional')
  const [error, setError] = useState('')

  const { mutate, isPending } = useMutation({
    mutationFn: () =>
      createProject({
        client_id: webdevClientId,
        platform,
        brief: {
          project_name: projectName.trim(),
          description: description.trim(),
          target_audience: targetAudience.trim() || undefined,
          estimated_pages: pages ? parseInt(pages, 10) : undefined,
          tone_of_voice: tone,
        },
      }),
    onSuccess: (project) => {
      qc.invalidateQueries({ queryKey: ['webdev-projects', webdevClientId] })
      navigate(`/clients/${clientId}/webdev/${project.id}`)
    },
    onError: (err: Error) => setError(err.message),
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    if (!projectName.trim()) { setError('Project name is required.'); return }
    if (!description.trim()) { setError('Brief description is required.'); return }
    mutate()
  }

  return (
    <div className="p-8">
      <button
        onClick={() => navigate(`/clients/${clientId}/webdev`)}
        className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 mb-6"
      >
        <ArrowLeft className="w-4 h-4" /> Back to Projects
      </button>

      <div className="max-w-lg">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-purple-100 flex items-center justify-center">
            <Code2 className="w-5 h-5 text-purple-600" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-900">New Website Project</h1>
            <p className="text-sm text-slate-500">The Director agent will plan your pipeline from this brief.</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <Card>
            <CardHeader><h2 className="text-sm font-semibold text-slate-700">Platform</h2></CardHeader>
            <CardBody>
              <div className="grid grid-cols-2 gap-3">
                {PLATFORMS.map(({ id, label, icon: Icon }) => (
                  <button
                    key={id}
                    type="button"
                    onClick={() => setPlatform(id)}
                    className={`flex items-center gap-2.5 px-4 py-3 rounded-lg border-2 text-sm font-medium transition-colors ${
                      platform === id
                        ? 'border-purple-500 bg-purple-50 text-purple-700'
                        : 'border-slate-200 text-slate-600 hover:border-slate-300'
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    {label}
                  </button>
                ))}
              </div>
            </CardBody>
          </Card>

          <Card>
            <CardHeader><h2 className="text-sm font-semibold text-slate-700">Project Brief</h2></CardHeader>
            <CardBody className="space-y-4">
              <Input
                label="Project name *"
                placeholder="Acme Corp Website Redesign"
                value={projectName}
                onChange={e => setProjectName(e.target.value)}
              />
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Description *</label>
                <textarea
                  rows={4}
                  className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-500 resize-none"
                  placeholder="Describe the website goals, key sections, and any specific requirements..."
                  value={description}
                  onChange={e => setDescription(e.target.value)}
                />
              </div>
              <Input
                label="Target audience"
                placeholder="e.g. B2B SaaS buyers, local Cape Town homeowners"
                value={targetAudience}
                onChange={e => setTargetAudience(e.target.value)}
              />
              <div className="grid grid-cols-2 gap-3">
                <Input
                  label="Estimated pages"
                  type="number"
                  min={1}
                  placeholder="8"
                  value={pages}
                  onChange={e => setPages(e.target.value)}
                />
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">Tone of voice</label>
                  <select
                    className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-500 capitalize"
                    value={tone}
                    onChange={e => setTone(e.target.value)}
                  >
                    {['professional', 'friendly', 'bold', 'minimal', 'playful'].map(t => (
                      <option key={t} value={t}>{t}</option>
                    ))}
                  </select>
                </div>
              </div>
            </CardBody>
          </Card>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <div className="flex items-center gap-3">
            <Button type="submit" loading={isPending}>
              <Code2 className="w-4 h-4" />
              Create Project
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => navigate(`/clients/${clientId}/webdev`)}
            >
              Cancel
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}
