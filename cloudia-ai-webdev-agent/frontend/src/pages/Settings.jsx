import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  CheckCircle2, XCircle, Loader2, AlertCircle, Eye, EyeOff, Trash2,
  TestTube2, Globe, ShoppingBag, Plus, Key, Server
} from 'lucide-react'
import client from '../api/client'

// ---- API helpers ----
function fetchSystemStatus() {
  return client.get('/api/settings')
}

function fetchCredentials() {
  return client.get('/api/settings/credentials')
}

function addCredential(data) {
  return client.post('/api/settings/credentials', data)
}

function testCredential(id) {
  return client.get(`/api/settings/credentials/${id}/test`)
}

function deleteCredential(id) {
  return client.delete(`/api/settings/credentials/${id}`)
}

// ---- Sub-components ----

function StatusIndicator({ ok, label }) {
  return (
    <div className="flex items-center gap-3 py-3 border-b border-slate-700 last:border-0">
      <div className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${ok ? 'bg-green-400' : 'bg-red-400'}`} />
      <span className="text-sm text-slate-300 flex-1">{label}</span>
      <span className={`text-xs font-medium ${ok ? 'text-green-400' : 'text-red-400'}`}>
        {ok ? 'Online' : 'Offline'}
      </span>
    </div>
  )
}

function SystemStatus() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['settings'],
    queryFn: fetchSystemStatus,
    refetchInterval: 15000,
  })

  return (
    <section className="bg-slate-800 border border-slate-700 rounded-lg p-5">
      <div className="flex items-center gap-2 mb-4">
        <Server size={16} className="text-slate-400" />
        <h2 className="text-sm font-semibold text-slate-200">System Status</h2>
      </div>

      {isLoading && (
        <div className="flex items-center gap-2 text-slate-400 text-sm py-2">
          <Loader2 size={14} className="animate-spin" />
          Checking status...
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 text-red-400 text-sm py-2">
          <AlertCircle size={14} />
          {error.message}
        </div>
      )}

      {data && !isLoading && (
        <div>
          <StatusIndicator ok={data.status === 'ok' || data.db === 'ok' || !!data.database} label="Database" />
          <StatusIndicator ok={data.redis === 'ok' || !!data.redis_connected} label="Redis" />
          <StatusIndicator ok={data.celery === 'ok' || !!data.worker_online || data.status === 'ok'} label="Celery Worker" />
          {data.status && (
            <div className="mt-3 pt-3 border-t border-slate-700">
              <span className="text-xs text-slate-500">Overall: </span>
              <span className={`text-xs font-medium ${data.status === 'ok' ? 'text-green-400' : 'text-amber-400'}`}>
                {data.status}
              </span>
            </div>
          )}
        </div>
      )}
    </section>
  )
}

function ApiKeySection() {
  const [apiKey, setApiKey] = useState(localStorage.getItem('cloudia_api_key') || '')
  const [show, setShow] = useState(false)
  const [saved, setSaved] = useState(false)

  const handleSave = (e) => {
    e.preventDefault()
    localStorage.setItem('cloudia_api_key', apiKey.trim())
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <section className="bg-slate-800 border border-slate-700 rounded-lg p-5">
      <div className="flex items-center gap-2 mb-4">
        <Key size={16} className="text-slate-400" />
        <h2 className="text-sm font-semibold text-slate-200">API Key</h2>
      </div>
      <p className="text-xs text-slate-400 mb-4">
        This key is sent as <code className="bg-slate-700 px-1 py-0.5 rounded text-slate-300">X-API-Key</code> header on all requests. Stored in browser localStorage.
      </p>
      <form onSubmit={handleSave} className="flex gap-2">
        <div className="relative flex-1">
          <input
            type={show ? 'text' : 'password'}
            value={apiKey}
            onChange={e => { setApiKey(e.target.value); setSaved(false) }}
            placeholder="Enter API key..."
            className="w-full rounded bg-slate-700 border border-slate-600 text-slate-100 text-sm px-3 py-2 pr-9 focus:outline-none focus:border-blue-500 placeholder-slate-500 font-mono"
          />
          <button
            type="button"
            onClick={() => setShow(v => !v)}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200 transition-colors"
          >
            {show ? <EyeOff size={14} /> : <Eye size={14} />}
          </button>
        </div>
        <button
          type="submit"
          className={`px-4 py-2 rounded text-sm font-medium transition-colors ${
            saved
              ? 'bg-green-800/50 text-green-300'
              : 'bg-blue-600 hover:bg-blue-700 text-white'
          }`}
        >
          {saved ? 'Saved!' : 'Save'}
        </button>
      </form>
    </section>
  )
}

function CredentialRow({ cred, onDelete, onTest }) {
  const [testResult, setTestResult] = useState(null)
  const [testing, setTesting] = useState(false)
  const [testError, setTestError] = useState(null)
  const [confirmDelete, setConfirmDelete] = useState(false)

  const handleTest = async () => {
    setTesting(true)
    setTestResult(null)
    setTestError(null)
    try {
      const result = await testCredential(cred.id)
      setTestResult(result)
    } catch (err) {
      setTestError(err.message)
    } finally {
      setTesting(false)
    }
  }

  return (
    <div className="flex items-start gap-3 py-3 border-b border-slate-700 last:border-0">
      <div className="flex-shrink-0 mt-0.5">
        {cred.platform === 'wordpress' ? (
          <Globe size={16} className="text-slate-400" />
        ) : (
          <ShoppingBag size={16} className="text-slate-400" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-medium text-slate-200 capitalize">{cred.platform}</span>
          <span className="text-xs text-slate-500 font-mono truncate max-w-48">
            {cred.site_url || cred.shop_url || '—'}
          </span>
        </div>
        {(testResult || testError) && (
          <div className={`mt-1 text-xs flex items-center gap-1 ${testResult?.success || testResult?.ok ? 'text-green-400' : 'text-red-400'}`}>
            {testResult?.success || testResult?.ok
              ? <CheckCircle2 size={11} />
              : <XCircle size={11} />}
            {testError || testResult?.message || (testResult?.success || testResult?.ok ? 'Connection successful' : 'Connection failed')}
          </div>
        )}
      </div>
      <div className="flex items-center gap-2 flex-shrink-0">
        <button
          onClick={handleTest}
          disabled={testing}
          className="flex items-center gap-1 px-2.5 py-1.5 rounded text-xs font-medium bg-slate-700 hover:bg-slate-600 text-slate-300 transition-colors disabled:opacity-50"
          title="Test connection"
        >
          {testing ? <Loader2 size={11} className="animate-spin" /> : <TestTube2 size={11} />}
          Test
        </button>
        {confirmDelete ? (
          <>
            <button
              onClick={() => onDelete(cred.id)}
              className="px-2.5 py-1.5 rounded text-xs font-medium bg-red-900/50 hover:bg-red-800 text-red-300 transition-colors"
            >
              Confirm
            </button>
            <button
              onClick={() => setConfirmDelete(false)}
              className="px-2.5 py-1.5 rounded text-xs font-medium bg-slate-700 hover:bg-slate-600 text-slate-300 transition-colors"
            >
              Cancel
            </button>
          </>
        ) : (
          <button
            onClick={() => setConfirmDelete(true)}
            className="flex items-center gap-1 px-2.5 py-1.5 rounded text-xs font-medium bg-slate-700 hover:bg-red-900/40 text-slate-400 hover:text-red-400 transition-colors"
            title="Delete credential"
          >
            <Trash2 size={11} />
          </button>
        )}
      </div>
    </div>
  )
}

const EMPTY_CRED = {
  platform: 'wordpress',
  site_url: '',
  admin_user: '',
  app_password: '',
  shop_url: '',
  access_token: '',
}

function CredentialsSection() {
  const queryClient = useQueryClient()
  const [showAdd, setShowAdd] = useState(false)
  const [newCred, setNewCred] = useState(EMPTY_CRED)
  const [addError, setAddError] = useState(null)
  const [fieldErrors, setFieldErrors] = useState({})

  const { data, isLoading, error } = useQuery({
    queryKey: ['credentials'],
    queryFn: fetchCredentials,
  })

  const addMutation = useMutation({
    mutationFn: (data) => addCredential(data),
    onSuccess: () => {
      setAddError(null)
      setNewCred(EMPTY_CRED)
      setShowAdd(false)
      setFieldErrors({})
      queryClient.invalidateQueries({ queryKey: ['credentials'] })
    },
    onError: (err) => setAddError(err.message),
  })

  const deleteMutation = useMutation({
    mutationFn: (id) => deleteCredential(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['credentials'] })
    },
  })

  const credentials = Array.isArray(data) ? data : data?.results || []

  const handleAdd = (e) => {
    e.preventDefault()
    const errs = {}
    if (newCred.platform === 'wordpress') {
      if (!newCred.site_url.trim()) errs.site_url = 'Required'
      if (!newCred.admin_user.trim()) errs.admin_user = 'Required'
      if (!newCred.app_password.trim()) errs.app_password = 'Required'
    } else {
      if (!newCred.shop_url.trim()) errs.shop_url = 'Required'
      if (!newCred.access_token.trim()) errs.access_token = 'Required'
    }
    if (Object.keys(errs).length > 0) { setFieldErrors(errs); return }
    setFieldErrors({})

    const payload = newCred.platform === 'wordpress'
      ? { platform: 'wordpress', site_url: newCred.site_url, admin_user: newCred.admin_user, app_password: newCred.app_password }
      : { platform: 'shopify', shop_url: newCred.shop_url, access_token: newCred.access_token }

    addMutation.mutate(payload)
  }

  const inputClass = "w-full rounded bg-slate-700 border border-slate-600 text-slate-100 text-sm px-3 py-2 focus:outline-none focus:border-blue-500 placeholder-slate-500 transition-colors"
  const errInputClass = "w-full rounded bg-slate-700 border border-red-600 text-slate-100 text-sm px-3 py-2 focus:outline-none focus:border-red-500 placeholder-slate-500 transition-colors"

  return (
    <section className="bg-slate-800 border border-slate-700 rounded-lg p-5">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-slate-200">Site Credentials</h2>
        <button
          onClick={() => { setShowAdd(v => !v); setAddError(null); setFieldErrors({}) }}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium bg-slate-700 hover:bg-slate-600 text-slate-200 transition-colors"
        >
          <Plus size={13} />
          Add Credential
        </button>
      </div>

      {isLoading && <div className="text-sm text-slate-500 py-2">Loading...</div>}
      {error && <div className="text-sm text-red-400 py-2 flex items-center gap-2"><AlertCircle size={14} />{error.message}</div>}

      {credentials.length === 0 && !isLoading && (
        <p className="text-sm text-slate-500 py-2">No credentials configured</p>
      )}

      {credentials.map(cred => (
        <CredentialRow
          key={cred.id}
          cred={cred}
          onDelete={(id) => deleteMutation.mutate(id)}
        />
      ))}

      {showAdd && (
        <form onSubmit={handleAdd} className="mt-4 pt-4 border-t border-slate-700 space-y-3">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">New Credential</h3>

          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Platform</label>
            <select
              value={newCred.platform}
              onChange={e => setNewCred(prev => ({ ...EMPTY_CRED, platform: e.target.value }))}
              className={inputClass}
            >
              <option value="wordpress">WordPress</option>
              <option value="shopify">Shopify</option>
            </select>
          </div>

          {newCred.platform === 'wordpress' ? (
            <>
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Site URL <span className="text-red-400">*</span></label>
                <input
                  type="url"
                  value={newCred.site_url}
                  onChange={e => setNewCred(p => ({ ...p, site_url: e.target.value }))}
                  placeholder="https://example.co.za"
                  className={fieldErrors.site_url ? errInputClass : inputClass}
                />
                {fieldErrors.site_url && <p className="text-xs text-red-400 mt-0.5">{fieldErrors.site_url}</p>}
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Admin Username <span className="text-red-400">*</span></label>
                <input
                  type="text"
                  value={newCred.admin_user}
                  onChange={e => setNewCred(p => ({ ...p, admin_user: e.target.value }))}
                  placeholder="admin"
                  className={fieldErrors.admin_user ? errInputClass : inputClass}
                  autoComplete="off"
                />
                {fieldErrors.admin_user && <p className="text-xs text-red-400 mt-0.5">{fieldErrors.admin_user}</p>}
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Application Password <span className="text-red-400">*</span></label>
                <input
                  type="password"
                  value={newCred.app_password}
                  onChange={e => setNewCred(p => ({ ...p, app_password: e.target.value }))}
                  placeholder="xxxx xxxx xxxx xxxx"
                  className={fieldErrors.app_password ? errInputClass : inputClass}
                  autoComplete="new-password"
                />
                {fieldErrors.app_password && <p className="text-xs text-red-400 mt-0.5">{fieldErrors.app_password}</p>}
              </div>
            </>
          ) : (
            <>
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Shop URL <span className="text-red-400">*</span></label>
                <input
                  type="text"
                  value={newCred.shop_url}
                  onChange={e => setNewCred(p => ({ ...p, shop_url: e.target.value }))}
                  placeholder="your-store.myshopify.com"
                  className={fieldErrors.shop_url ? errInputClass : inputClass}
                />
                {fieldErrors.shop_url && <p className="text-xs text-red-400 mt-0.5">{fieldErrors.shop_url}</p>}
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Access Token <span className="text-red-400">*</span></label>
                <input
                  type="password"
                  value={newCred.access_token}
                  onChange={e => setNewCred(p => ({ ...p, access_token: e.target.value }))}
                  placeholder="shpat_..."
                  className={fieldErrors.access_token ? errInputClass : inputClass}
                  autoComplete="new-password"
                />
                {fieldErrors.access_token && <p className="text-xs text-red-400 mt-0.5">{fieldErrors.access_token}</p>}
              </div>
            </>
          )}

          {addError && (
            <p className="text-xs text-red-400 bg-red-950/30 rounded px-2 py-1">{addError}</p>
          )}

          <div className="flex gap-2 pt-1">
            <button
              type="submit"
              disabled={addMutation.isPending}
              className="flex items-center gap-1.5 px-4 py-2 rounded text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white transition-colors disabled:opacity-50"
            >
              {addMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
              {addMutation.isPending ? 'Saving...' : 'Save Credential'}
            </button>
            <button
              type="button"
              onClick={() => { setShowAdd(false); setAddError(null); setFieldErrors({}) }}
              className="px-4 py-2 rounded text-sm font-medium bg-slate-700 hover:bg-slate-600 text-slate-300 transition-colors"
            >
              Cancel
            </button>
          </div>
        </form>
      )}
    </section>
  )
}

export default function Settings() {
  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-100">Settings</h1>
        <p className="text-sm text-slate-400 mt-0.5">System configuration and credentials</p>
      </div>

      <SystemStatus />
      <ApiKeySection />
      <CredentialsSection />

      {/* Media APIs info */}
      <section className="bg-slate-800 border border-slate-700 rounded-lg p-5">
        <h2 className="text-sm font-semibold text-slate-200 mb-4">Media APIs</h2>
        <p className="text-xs text-slate-500 mb-3">
          Media API keys (Unsplash, Pexels) are configured server-side via environment variables and cannot be managed here.
        </p>
        <div className="space-y-2">
          {['Unsplash', 'Pexels'].map(service => (
            <div key={service} className="flex items-center gap-3 py-2 border-b border-slate-700 last:border-0">
              <div className="w-2.5 h-2.5 rounded-full bg-slate-600 flex-shrink-0" />
              <span className="text-sm text-slate-400">{service}</span>
              <span className="text-xs text-slate-600 ml-auto font-mono">••••••••••••</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
