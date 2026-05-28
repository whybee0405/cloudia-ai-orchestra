import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createClient } from '@/api/brand-dna'
import { Card, CardBody, CardHeader } from '@/shared/components/Card'
import { Input } from '@/shared/components/Input'
import { Button } from '@/shared/components/Button'
import { ArrowLeft } from 'lucide-react'

const INDUSTRIES = [
  { value: 'restaurant', label: 'Restaurant / Food Service' },
  { value: 'retail', label: 'Retail' },
  { value: 'professional_services', label: 'Professional Services' },
  { value: 'health_wellness', label: 'Health & Wellness' },
  { value: 'real_estate', label: 'Real Estate' },
  { value: 'education', label: 'Education' },
  { value: 'ecommerce', label: 'E-Commerce' },
  { value: 'hospitality_tourism', label: 'Hospitality & Tourism' },
  { value: 'automotive', label: 'Automotive' },
  { value: 'beauty_personal_care', label: 'Beauty & Personal Care' },
  { value: 'other', label: 'Other' },
]

export function CreateClient() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [form, setForm] = useState({
    name: '',
    website_url: '',
    industry: '',
    sub_industry: '',
    location: '',
    founded_year: '',
  })
  const [errors, setErrors] = useState<Record<string, string>>({})

  const mutation = useMutation({
    mutationFn: createClient,
    onSuccess: (client) => {
      queryClient.invalidateQueries({ queryKey: ['clients'] })
      navigate(`/clients/${client.id}/brand-dna/setup`)
    },
  })

  const validate = () => {
    const e: Record<string, string> = {}
    if (!form.name.trim()) e.name = 'Client name is required'
    setErrors(e)
    return Object.keys(e).length === 0
  }

  const submit = () => {
    if (!validate()) return
    mutation.mutate({
      name: form.name.trim(),
      website_url: form.website_url.trim() || undefined,
      industry: form.industry || undefined,
      sub_industry: form.sub_industry.trim() || undefined,
      location: form.location.trim() || undefined,
      founded_year: form.founded_year ? parseInt(form.founded_year) : undefined,
    })
  }

  const set = (field: string, value: string) => setForm(f => ({ ...f, [field]: value }))

  return (
    <div className="p-8 max-w-xl">
      <button
        onClick={() => navigate('/clients')}
        className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 mb-6 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Clients
      </button>

      <h1 className="text-2xl font-bold text-slate-900 mb-1">New Client</h1>
      <p className="text-sm text-slate-500 mb-6">You'll set up Brand DNA in the next step.</p>

      <Card>
        <CardHeader>
          <h2 className="text-sm font-semibold text-slate-700">Business Details</h2>
        </CardHeader>
        <CardBody className="space-y-4">
          <Input
            label="Business Name *"
            value={form.name}
            onChange={e => set('name', e.target.value)}
            placeholder="e.g. Acme Digital"
            error={errors.name}
          />
          <Input
            label="Website URL"
            value={form.website_url}
            onChange={e => set('website_url', e.target.value)}
            placeholder="https://example.co.za"
            type="url"
          />
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="block text-sm font-medium text-slate-700">Industry</label>
              <select
                value={form.industry}
                onChange={e => set('industry', e.target.value)}
                className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
              >
                <option value="">Select industry</option>
                {INDUSTRIES.map(i => (
                  <option key={i.value} value={i.value}>{i.label}</option>
                ))}
              </select>
            </div>
            <Input
              label="Sub-Industry"
              value={form.sub_industry}
              onChange={e => set('sub_industry', e.target.value)}
              placeholder="e.g. Fine Dining"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Location"
              value={form.location}
              onChange={e => set('location', e.target.value)}
              placeholder="e.g. Johannesburg"
            />
            <Input
              label="Founded Year"
              value={form.founded_year}
              onChange={e => set('founded_year', e.target.value)}
              type="number"
              min="1900"
              max={new Date().getFullYear()}
              placeholder="e.g. 2018"
            />
          </div>

          {mutation.error && (
            <p className="text-sm text-red-600">{String(mutation.error)}</p>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => navigate('/clients')}>Cancel</Button>
            <Button onClick={submit} loading={mutation.isPending}>
              Create & Set Up Brand DNA →
            </Button>
          </div>
        </CardBody>
      </Card>
    </div>
  )
}
