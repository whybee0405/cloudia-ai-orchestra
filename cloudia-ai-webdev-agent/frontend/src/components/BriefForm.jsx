import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Globe, ShoppingBag, Cpu, Plus, X, Check, ChevronRight, ChevronLeft } from 'lucide-react'
import { fetchClients, createClient } from '../api/projects'

const TOTAL_STEPS = 7

const DEFAULT_PAGES = ['Home', 'About', 'Services', 'Contact', 'Blog', 'FAQ', 'Gallery', 'Portfolio']

const FONT_OPTIONS = [
  'system-ui',
  'Inter',
  'Roboto',
  'Open Sans',
  'Lato',
  'Montserrat',
  'Poppins',
  'Playfair Display',
  'Merriweather',
  'Source Sans Pro',
]

const initialState = {
  // Step 1
  clientMode: 'existing', // 'existing' | 'new'
  selectedClientId: '',
  newClient: {
    name: '',
    email: '',
    phone: '',
    company: '',
  },
  // Step 2
  platform: '',
  // Step 3
  business_description: '',
  target_customer: '',
  usp: '',
  cta_goal: '',
  // Step 4
  pages: ['Home', 'About', 'Services', 'Contact'],
  customPage: '',
  // Step 5
  brand: {
    primary_color: '#3b82f6',
    secondary_color: '#1e293b',
    accent_color: '#f59e0b',
    heading_font: 'system-ui',
    body_font: 'system-ui',
    logo_url: '',
  },
  // Step 6
  credentials: {
    wordpress: { site_url: '', admin_user: '', app_password: '' },
    shopify: { shop_url: '', access_token: '' },
  },
}

function StepIndicator({ current, total }) {
  return (
    <div className="mb-8">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-slate-400">Step {current} of {total}</span>
        <span className="text-xs text-slate-400">{Math.round((current / total) * 100)}% complete</span>
      </div>
      <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
        <div
          className="h-full bg-blue-600 rounded-full transition-all duration-300"
          style={{ width: `${(current / total) * 100}%` }}
        />
      </div>
    </div>
  )
}

function FieldError({ message }) {
  if (!message) return null
  return <p className="mt-1 text-xs text-red-400">{message}</p>
}

const inputClass = "w-full rounded bg-slate-700 border border-slate-600 text-slate-100 text-sm px-3 py-2 focus:outline-none focus:border-blue-500 placeholder-slate-500 transition-colors"
const errorInputClass = "w-full rounded bg-slate-700 border border-red-600 text-slate-100 text-sm px-3 py-2 focus:outline-none focus:border-red-500 placeholder-slate-500 transition-colors"

export function BriefForm({ onSubmit, isSubmitting, submitError }) {
  const [step, setStep] = useState(1)
  const [form, setForm] = useState(initialState)
  const [errors, setErrors] = useState({})
  const [createClientError, setCreateClientError] = useState(null)
  const [isCreatingClient, setIsCreatingClient] = useState(false)
  const [createdClient, setCreatedClient] = useState(null)

  const { data: clients = [], isLoading: clientsLoading } = useQuery({
    queryKey: ['clients'],
    queryFn: fetchClients,
  })

  const setField = (key, value) => {
    setForm(prev => ({ ...prev, [key]: value }))
    setErrors(prev => ({ ...prev, [key]: undefined }))
  }

  const setBrandField = (key, value) => {
    setForm(prev => ({ ...prev, brand: { ...prev.brand, [key]: value } }))
  }

  const setNewClientField = (key, value) => {
    setForm(prev => ({ ...prev, newClient: { ...prev.newClient, [key]: value } }))
    setErrors(prev => ({ ...prev, [`nc_${key}`]: undefined }))
  }

  const setCredField = (platform, key, value) => {
    setForm(prev => ({
      ...prev,
      credentials: {
        ...prev.credentials,
        [platform]: { ...prev.credentials[platform], [key]: value },
      },
    }))
  }

  const validateStep = () => {
    const errs = {}

    if (step === 1) {
      if (form.clientMode === 'existing') {
        const effectiveId = createdClient?.id || form.selectedClientId
        if (!effectiveId) errs.selectedClientId = 'Please select a client'
      } else {
        if (!form.newClient.name.trim()) errs.nc_name = 'Client name is required'
        if (!form.newClient.email.trim()) errs.nc_email = 'Email is required'
      }
    }

    if (step === 2) {
      if (!form.platform) errs.platform = 'Please select a platform'
    }

    if (step === 3) {
      if (!form.business_description.trim()) errs.business_description = 'Required'
      if (!form.target_customer.trim()) errs.target_customer = 'Required'
      if (!form.usp.trim()) errs.usp = 'Required'
      if (!form.cta_goal.trim()) errs.cta_goal = 'Required'
    }

    if (step === 4) {
      if (form.pages.length === 0) errs.pages = 'Select at least one page'
    }

    return errs
  }

  const handleNext = async (e) => {
    e.preventDefault()

    // Handle new client creation inline at step 1
    if (step === 1 && form.clientMode === 'new' && !createdClient) {
      const errs = validateStep()
      if (Object.keys(errs).length > 0) { setErrors(errs); return }
      setIsCreatingClient(true)
      setCreateClientError(null)
      try {
        const result = await createClient(form.newClient)
        setCreatedClient(result)
        setErrors({})
        setStep(s => s + 1)
      } catch (err) {
        setCreateClientError(err.message)
      } finally {
        setIsCreatingClient(false)
      }
      return
    }

    const errs = validateStep()
    if (Object.keys(errs).length > 0) { setErrors(errs); return }
    setErrors({})
    setStep(s => Math.min(s + 1, TOTAL_STEPS))
  }

  const handleBack = (e) => {
    e.preventDefault()
    setErrors({})
    setStep(s => Math.max(s - 1, 1))
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    const errs = validateStep()
    if (Object.keys(errs).length > 0) { setErrors(errs); return }

    const clientId = createdClient?.id || form.selectedClientId

    const brief = {
      business_description: form.business_description,
      target_customer: form.target_customer,
      usp: form.usp,
      cta_goal: form.cta_goal,
      pages: form.pages,
      brand: form.brand,
      credentials: form.platform === 'wordpress' ? form.credentials.wordpress : form.credentials.shopify,
    }

    onSubmit({
      client_id: Number(clientId),
      platform: form.platform === 'auto' ? null : form.platform,
      brief,
    })
  }

  const togglePage = (page) => {
    setForm(prev => ({
      ...prev,
      pages: prev.pages.includes(page)
        ? prev.pages.filter(p => p !== page)
        : [...prev.pages, page],
    }))
    setErrors(prev => ({ ...prev, pages: undefined }))
  }

  const addCustomPage = () => {
    const trimmed = form.customPage.trim()
    if (!trimmed || form.pages.includes(trimmed)) return
    setForm(prev => ({ ...prev, pages: [...prev.pages, trimmed], customPage: '' }))
  }

  const removePage = (page) => {
    setForm(prev => ({ ...prev, pages: prev.pages.filter(p => p !== page) }))
  }

  // Step renders

  const renderStep1 = () => (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-slate-100 mb-1">Client</h2>
        <p className="text-sm text-slate-400">Select an existing client or create a new one</p>
      </div>

      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => { setField('clientMode', 'existing'); setCreatedClient(null) }}
          className={`px-4 py-2 rounded text-sm font-medium transition-colors ${
            form.clientMode === 'existing'
              ? 'bg-blue-600 text-white'
              : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
          }`}
        >
          Existing Client
        </button>
        <button
          type="button"
          onClick={() => { setField('clientMode', 'new'); setCreatedClient(null) }}
          className={`px-4 py-2 rounded text-sm font-medium transition-colors ${
            form.clientMode === 'new'
              ? 'bg-blue-600 text-white'
              : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
          }`}
        >
          New Client
        </button>
      </div>

      {form.clientMode === 'existing' ? (
        <div>
          <label className="block text-xs font-medium text-slate-400 mb-1">Select Client</label>
          {clientsLoading ? (
            <div className="text-sm text-slate-500">Loading clients...</div>
          ) : (
            <select
              value={form.selectedClientId}
              onChange={e => setField('selectedClientId', e.target.value)}
              className={errors.selectedClientId ? errorInputClass : inputClass}
            >
              <option value="">— Choose a client —</option>
              {(Array.isArray(clients) ? clients : clients?.results || []).map(c => (
                <option key={c.id} value={c.id}>
                  {c.name} {c.company ? `(${c.company})` : ''}
                </option>
              ))}
            </select>
          )}
          <FieldError message={errors.selectedClientId} />
        </div>
      ) : (
        <div className="space-y-4">
          {createdClient ? (
            <div className="flex items-center gap-2 p-3 rounded bg-green-900/20 border border-green-800/40 text-green-300 text-sm">
              <Check size={16} />
              Client "{createdClient.name}" created successfully (ID: {createdClient.id})
            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">
                    Full Name <span className="text-red-400">*</span>
                  </label>
                  <input
                    type="text"
                    value={form.newClient.name}
                    onChange={e => setNewClientField('name', e.target.value)}
                    placeholder="Jane Smith"
                    className={errors.nc_name ? errorInputClass : inputClass}
                  />
                  <FieldError message={errors.nc_name} />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">
                    Email <span className="text-red-400">*</span>
                  </label>
                  <input
                    type="email"
                    value={form.newClient.email}
                    onChange={e => setNewClientField('email', e.target.value)}
                    placeholder="jane@company.co.za"
                    className={errors.nc_email ? errorInputClass : inputClass}
                  />
                  <FieldError message={errors.nc_email} />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">Phone</label>
                  <input
                    type="tel"
                    value={form.newClient.phone}
                    onChange={e => setNewClientField('phone', e.target.value)}
                    placeholder="+27 82 000 0000"
                    className={inputClass}
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">Company</label>
                  <input
                    type="text"
                    value={form.newClient.company}
                    onChange={e => setNewClientField('company', e.target.value)}
                    placeholder="Acme Pty Ltd"
                    className={inputClass}
                  />
                </div>
              </div>
              {createClientError && (
                <p className="text-xs text-red-400 bg-red-950/30 rounded px-2 py-1">{createClientError}</p>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )

  const renderStep2 = () => (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-slate-100 mb-1">Platform</h2>
        <p className="text-sm text-slate-400">Choose the website platform to build on</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {[
          {
            key: 'wordpress',
            label: 'WordPress',
            icon: Globe,
            desc: 'Full CMS with themes, plugins, and content management. Best for content-heavy sites.',
          },
          {
            key: 'shopify',
            label: 'Shopify',
            icon: ShoppingBag,
            desc: 'E-commerce first. Products, collections, checkout, and payment processing built-in.',
          },
          {
            key: 'auto',
            label: 'Auto-Detect',
            icon: Cpu,
            desc: 'Let the AI analyse the brief and pick the most suitable platform automatically.',
          },
        ].map(({ key, label, icon: Icon, desc }) => (
          <button
            key={key}
            type="button"
            onClick={() => setField('platform', key)}
            className={`text-left p-4 rounded-lg border-2 transition-colors ${
              form.platform === key
                ? 'border-blue-500 bg-blue-950/30'
                : 'border-slate-700 bg-slate-800 hover:border-slate-600'
            }`}
          >
            <div className="flex items-center gap-2 mb-2">
              <Icon size={20} className={form.platform === key ? 'text-blue-400' : 'text-slate-400'} />
              <span className={`font-medium text-sm ${form.platform === key ? 'text-blue-300' : 'text-slate-200'}`}>
                {label}
              </span>
              {form.platform === key && <Check size={14} className="text-blue-400 ml-auto" />}
            </div>
            <p className="text-xs text-slate-500 leading-relaxed">{desc}</p>
          </button>
        ))}
      </div>
      <FieldError message={errors.platform} />
    </div>
  )

  const renderStep3 = () => (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-slate-100 mb-1">Business Brief</h2>
        <p className="text-sm text-slate-400">This informs every piece of content the AI generates</p>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-xs font-medium text-slate-400 mb-1">
            What does the business do? <span className="text-red-400">*</span>
          </label>
          <textarea
            value={form.business_description}
            onChange={e => setField('business_description', e.target.value)}
            rows={3}
            placeholder="e.g. We provide professional accounting and tax services to small and medium-sized businesses across South Africa..."
            className={`${errors.business_description ? errorInputClass : inputClass} resize-none`}
          />
          <FieldError message={errors.business_description} />
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-400 mb-1">
            Who is the target customer? <span className="text-red-400">*</span>
          </label>
          <textarea
            value={form.target_customer}
            onChange={e => setField('target_customer', e.target.value)}
            rows={3}
            placeholder="e.g. South African SME owners aged 30-55, running businesses with 5-50 employees, who are time-poor and need reliable financial guidance..."
            className={`${errors.target_customer ? errorInputClass : inputClass} resize-none`}
          />
          <FieldError message={errors.target_customer} />
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-400 mb-1">
            What makes them different? (USP) <span className="text-red-400">*</span>
          </label>
          <textarea
            value={form.usp}
            onChange={e => setField('usp', e.target.value)}
            rows={3}
            placeholder="e.g. We guarantee 24-hour turnaround on all tax queries, and have 15 years experience with SARS compliance..."
            className={`${errors.usp ? errorInputClass : inputClass} resize-none`}
          />
          <FieldError message={errors.usp} />
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-400 mb-1">
            What action should visitors take? (CTA goal) <span className="text-red-400">*</span>
          </label>
          <textarea
            value={form.cta_goal}
            onChange={e => setField('cta_goal', e.target.value)}
            rows={2}
            placeholder="e.g. Book a free 30-minute consultation, or Request a quote..."
            className={`${errors.cta_goal ? errorInputClass : inputClass} resize-none`}
          />
          <FieldError message={errors.cta_goal} />
        </div>
      </div>
    </div>
  )

  const renderStep4 = () => (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-slate-100 mb-1">Pages Needed</h2>
        <p className="text-sm text-slate-400">Select all pages to include in the site</p>
      </div>

      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {DEFAULT_PAGES.map(page => {
          const selected = form.pages.includes(page)
          return (
            <button
              key={page}
              type="button"
              onClick={() => togglePage(page)}
              className={`flex items-center gap-2 px-3 py-2 rounded border text-sm font-medium transition-colors ${
                selected
                  ? 'border-blue-600 bg-blue-950/30 text-blue-300'
                  : 'border-slate-700 bg-slate-800 text-slate-400 hover:border-slate-600 hover:text-slate-200'
              }`}
            >
              <div className={`w-4 h-4 rounded border flex items-center justify-center flex-shrink-0 ${
                selected ? 'bg-blue-600 border-blue-600' : 'border-slate-600'
              }`}>
                {selected && <Check size={10} className="text-white" />}
              </div>
              {page}
            </button>
          )
        })}
      </div>

      {/* Custom pages */}
      {form.pages.filter(p => !DEFAULT_PAGES.includes(p)).length > 0 && (
        <div className="flex flex-wrap gap-2">
          {form.pages.filter(p => !DEFAULT_PAGES.includes(p)).map(page => (
            <span key={page} className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-700 text-sm text-slate-200">
              {page}
              <button type="button" onClick={() => removePage(page)} className="text-slate-400 hover:text-red-400 transition-colors">
                <X size={12} />
              </button>
            </span>
          ))}
        </div>
      )}

      <div className="flex gap-2">
        <input
          type="text"
          value={form.customPage}
          onChange={e => setForm(prev => ({ ...prev, customPage: e.target.value }))}
          onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addCustomPage() } }}
          placeholder="Add custom page (press Enter or click +)"
          className={inputClass}
        />
        <button
          type="button"
          onClick={addCustomPage}
          className="flex-shrink-0 px-3 py-2 rounded bg-slate-700 hover:bg-slate-600 text-slate-200 transition-colors"
        >
          <Plus size={16} />
        </button>
      </div>
      <FieldError message={errors.pages} />
    </div>
  )

  const renderStep5 = () => (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-slate-100 mb-1">Brand</h2>
        <p className="text-sm text-slate-400">Colours, fonts, and brand assets</p>
      </div>

      <div className="space-y-5">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-3">Colours</p>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            {[
              { key: 'primary_color', label: 'Primary' },
              { key: 'secondary_color', label: 'Secondary' },
              { key: 'accent_color', label: 'Accent' },
            ].map(({ key, label }) => (
              <div key={key}>
                <label className="block text-xs font-medium text-slate-400 mb-2">{label}</label>
                <div className="flex items-center gap-2">
                  <input
                    type="color"
                    value={form.brand[key]}
                    onChange={e => setBrandField(key, e.target.value)}
                    className="h-9 w-12 rounded cursor-pointer bg-slate-700 border border-slate-600 p-0.5"
                  />
                  <input
                    type="text"
                    value={form.brand[key]}
                    onChange={e => {
                      const val = e.target.value
                      if (/^#[0-9a-fA-F]{0,6}$/.test(val)) setBrandField(key, val)
                    }}
                    className="flex-1 rounded bg-slate-700 border border-slate-600 text-slate-100 text-sm px-2 py-2 font-mono focus:outline-none focus:border-blue-500"
                    maxLength={7}
                    placeholder="#000000"
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-3">Typography</p>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {[
              { key: 'heading_font', label: 'Heading Font' },
              { key: 'body_font', label: 'Body Font' },
            ].map(({ key, label }) => (
              <div key={key}>
                <label className="block text-xs font-medium text-slate-400 mb-1">{label}</label>
                <select
                  value={form.brand[key]}
                  onChange={e => setBrandField(key, e.target.value)}
                  className={inputClass}
                >
                  {FONT_OPTIONS.map(f => (
                    <option key={f} value={f}>{f}</option>
                  ))}
                </select>
              </div>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-400 mb-1">Logo URL</label>
          <input
            type="url"
            value={form.brand.logo_url}
            onChange={e => setBrandField('logo_url', e.target.value)}
            placeholder="https://example.com/logo.png"
            className={inputClass}
          />
          <p className="mt-1 text-xs text-slate-500">Optional. Publicly accessible URL to the client's logo file.</p>
        </div>
      </div>
    </div>
  )

  const renderStep6 = () => {
    const platform = form.platform
    const isWP = platform === 'wordpress' || platform === 'auto'
    const isShopify = platform === 'shopify'

    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-lg font-semibold text-slate-100 mb-1">Platform Credentials</h2>
          <p className="text-sm text-slate-400">
            {platform === 'auto'
              ? 'Provide both sets of credentials — the AI will use whichever platform it selects'
              : `Connection credentials for the ${platform} site`}
          </p>
        </div>

        {(isWP || platform === 'auto') && (
          <div className="space-y-3 p-4 rounded-lg border border-slate-700 bg-slate-800/50">
            <div className="flex items-center gap-2 mb-1">
              <Globe size={16} className="text-slate-400" />
              <p className="text-sm font-medium text-slate-300">WordPress</p>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Site URL</label>
              <input
                type="url"
                value={form.credentials.wordpress.site_url}
                onChange={e => setCredField('wordpress', 'site_url', e.target.value)}
                placeholder="https://example.co.za"
                className={inputClass}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Admin Username</label>
              <input
                type="text"
                value={form.credentials.wordpress.admin_user}
                onChange={e => setCredField('wordpress', 'admin_user', e.target.value)}
                placeholder="admin"
                className={inputClass}
                autoComplete="off"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Application Password</label>
              <input
                type="password"
                value={form.credentials.wordpress.app_password}
                onChange={e => setCredField('wordpress', 'app_password', e.target.value)}
                placeholder="xxxx xxxx xxxx xxxx"
                className={inputClass}
                autoComplete="new-password"
              />
              <p className="mt-1 text-xs text-slate-500">Generate under Users → Profile → Application Passwords in wp-admin</p>
            </div>
          </div>
        )}

        {(isShopify || platform === 'auto') && (
          <div className="space-y-3 p-4 rounded-lg border border-slate-700 bg-slate-800/50">
            <div className="flex items-center gap-2 mb-1">
              <ShoppingBag size={16} className="text-slate-400" />
              <p className="text-sm font-medium text-slate-300">Shopify</p>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Shop URL</label>
              <input
                type="text"
                value={form.credentials.shopify.shop_url}
                onChange={e => setCredField('shopify', 'shop_url', e.target.value)}
                placeholder="your-store.myshopify.com"
                className={inputClass}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Admin API Access Token</label>
              <input
                type="password"
                value={form.credentials.shopify.access_token}
                onChange={e => setCredField('shopify', 'access_token', e.target.value)}
                placeholder="shpat_..."
                className={inputClass}
                autoComplete="new-password"
              />
              <p className="mt-1 text-xs text-slate-500">Create a private app or custom app in Shopify admin → Apps → Develop apps</p>
            </div>
          </div>
        )}
      </div>
    )
  }

  const renderStep7 = () => {
    const effectiveClientId = createdClient?.id || form.selectedClientId
    const clientList = Array.isArray(clients) ? clients : clients?.results || []
    const client = createdClient || clientList.find(c => String(c.id) === String(effectiveClientId))

    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-lg font-semibold text-slate-100 mb-1">Review & Launch</h2>
          <p className="text-sm text-slate-400">Confirm all details before submitting to the agent pipeline</p>
        </div>

        <div className="space-y-3">
          {[
            { label: 'Client', value: client ? `${client.name}${client.company ? ` — ${client.company}` : ''}` : `ID ${effectiveClientId}` },
            { label: 'Platform', value: form.platform === 'auto' ? 'Auto-detect' : form.platform === 'wordpress' ? 'WordPress' : 'Shopify' },
            { label: 'Pages', value: form.pages.join(', ') || 'None selected' },
            { label: 'Business', value: form.business_description || '—' },
            { label: 'Target Customer', value: form.target_customer || '—' },
            { label: 'USP', value: form.usp || '—' },
            { label: 'CTA Goal', value: form.cta_goal || '—' },
          ].map(({ label, value }) => (
            <div key={label} className="flex gap-4 py-2 border-b border-slate-700/50">
              <span className="flex-shrink-0 w-32 text-xs font-medium text-slate-500 pt-0.5">{label}</span>
              <span className="text-sm text-slate-200 break-words">{value}</span>
            </div>
          ))}

          <div className="flex gap-4 py-2 border-b border-slate-700/50">
            <span className="flex-shrink-0 w-32 text-xs font-medium text-slate-500 pt-0.5">Brand Colours</span>
            <div className="flex items-center gap-3">
              {[
                { key: 'primary_color', label: 'Primary' },
                { key: 'secondary_color', label: 'Secondary' },
                { key: 'accent_color', label: 'Accent' },
              ].map(({ key, label }) => (
                <div key={key} className="flex items-center gap-1.5">
                  <div
                    className="w-5 h-5 rounded border border-slate-600"
                    style={{ backgroundColor: form.brand[key] }}
                  />
                  <span className="text-xs text-slate-400">{label}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {submitError && (
          <div className="p-3 rounded bg-red-950/30 border border-red-900/40 text-sm text-red-400">
            {submitError}
          </div>
        )}

        <div className="pt-2">
          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full sm:w-auto flex items-center justify-center gap-2 px-8 py-3 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? (
              <>
                <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Launching Pipeline...
              </>
            ) : (
              'Launch Agent Pipeline'
            )}
          </button>
        </div>
      </div>
    )
  }

  const stepRenderers = [renderStep1, renderStep2, renderStep3, renderStep4, renderStep5, renderStep6, renderStep7]

  const isLastStep = step === TOTAL_STEPS
  const isFirstStep = step === 1

  return (
    <form onSubmit={isLastStep ? handleSubmit : handleNext} noValidate>
      <StepIndicator current={step} total={TOTAL_STEPS} />

      <div className="min-h-64">
        {stepRenderers[step - 1]?.()}
      </div>

      <div className="mt-8 flex items-center justify-between">
        <button
          type="button"
          onClick={handleBack}
          disabled={isFirstStep}
          className="flex items-center gap-2 px-4 py-2 rounded text-sm font-medium bg-slate-700 hover:bg-slate-600 text-slate-200 transition-colors disabled:opacity-0 disabled:pointer-events-none"
        >
          <ChevronLeft size={16} />
          Back
        </button>

        {!isLastStep && (
          <button
            type="submit"
            disabled={isCreatingClient}
            className="flex items-center gap-2 px-6 py-2 rounded text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isCreatingClient ? 'Creating client...' : 'Next'}
            <ChevronRight size={16} />
          </button>
        )}
      </div>
    </form>
  )
}
