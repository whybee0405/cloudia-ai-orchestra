import { useState, useEffect } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Save, CheckCircle2, RefreshCw, AlertCircle } from 'lucide-react'
import { StatusBadge } from './StatusBadge'
import { updateContent, approveContent, regenerateContent } from '../api/content'

function CharCounter({ value = '', max }) {
  const len = (value || '').length
  const over = len > max
  return (
    <span className={`text-xs ${over ? 'text-red-400' : 'text-slate-500'}`}>
      {len}/{max}
    </span>
  )
}

export function ContentEditor({ piece, projectId }) {
  const queryClient = useQueryClient()
  const [fields, setFields] = useState({
    title: piece.title || '',
    h1: piece.h1 || '',
    body_content: piece.body_content || '',
    cta_text: piece.cta_text || '',
    meta_title: piece.meta_title || '',
    meta_description: piece.meta_description || '',
  })
  const [dirty, setDirty] = useState(false)
  const [saveError, setSaveError] = useState(null)
  const [actionError, setActionError] = useState(null)

  // Reset if piece changes externally
  useEffect(() => {
    setFields({
      title: piece.title || '',
      h1: piece.h1 || '',
      body_content: piece.body_content || '',
      cta_text: piece.cta_text || '',
      meta_title: piece.meta_title || '',
      meta_description: piece.meta_description || '',
    })
    setDirty(false)
  }, [piece.id])

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['content', String(projectId)] })
    queryClient.invalidateQueries({ queryKey: ['content', Number(projectId)] })
  }

  const saveMutation = useMutation({
    mutationFn: () => updateContent(piece.id, fields),
    onSuccess: () => {
      setSaveError(null)
      setDirty(false)
      invalidate()
    },
    onError: (err) => setSaveError(err.message),
  })

  const approveMutation = useMutation({
    mutationFn: () => approveContent(piece.id),
    onSuccess: () => {
      setActionError(null)
      invalidate()
    },
    onError: (err) => setActionError(err.message),
  })

  const regenerateMutation = useMutation({
    mutationFn: () => regenerateContent(piece.id),
    onSuccess: () => {
      setActionError(null)
      invalidate()
    },
    onError: (err) => setActionError(err.message),
  })

  const handleChange = (field, value) => {
    setFields(prev => ({ ...prev, [field]: value }))
    setDirty(true)
    setSaveError(null)
  }

  const handleSave = (e) => {
    e.preventDefault()
    saveMutation.mutate()
  }

  const inputClass = "w-full rounded bg-slate-700 border border-slate-600 text-slate-100 text-sm px-3 py-2 focus:outline-none focus:border-blue-500 placeholder-slate-500 transition-colors"

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-700 flex items-center justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="text-sm font-mono text-slate-200 truncate">/{piece.page_slug}</h3>
              <span className="text-xs px-1.5 py-0.5 rounded bg-slate-700 text-slate-400">{piece.content_type}</span>
              <StatusBadge status={piece.status} size="xs" />
              {dirty && (
                <span className="text-xs text-amber-400 flex items-center gap-1">
                  <AlertCircle size={10} />
                  Unsaved changes
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          {piece.status === 'draft' && !dirty && (
            <button
              onClick={() => approveMutation.mutate()}
              disabled={approveMutation.isPending}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium bg-green-800/50 hover:bg-green-700/60 text-green-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <CheckCircle2 size={12} />
              {approveMutation.isPending ? 'Approving...' : 'Approve'}
            </button>
          )}
          <button
            onClick={() => regenerateMutation.mutate()}
            disabled={regenerateMutation.isPending}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium bg-slate-700 hover:bg-slate-600 text-slate-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            title="Regenerate content with AI"
          >
            <RefreshCw size={12} className={regenerateMutation.isPending ? 'animate-spin' : ''} />
            {regenerateMutation.isPending ? 'Regenerating...' : 'Regenerate'}
          </button>
          <button
            onClick={handleSave}
            disabled={!dirty || saveMutation.isPending}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium bg-blue-600 hover:bg-blue-700 text-white transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <Save size={12} />
            {saveMutation.isPending ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>

      {(saveError || actionError) && (
        <div className="px-4 py-2 bg-red-950/30 border-b border-red-900/30">
          <p className="text-xs text-red-400">{saveError || actionError}</p>
        </div>
      )}

      <form onSubmit={handleSave} className="p-4 space-y-4">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Title</label>
            <input
              type="text"
              value={fields.title}
              onChange={e => handleChange('title', e.target.value)}
              placeholder="Page title"
              className={inputClass}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">H1 Heading</label>
            <input
              type="text"
              value={fields.h1}
              onChange={e => handleChange('h1', e.target.value)}
              placeholder="Main heading"
              className={inputClass}
            />
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-400 mb-1">Body Content</label>
          <textarea
            value={fields.body_content}
            onChange={e => handleChange('body_content', e.target.value)}
            rows={8}
            placeholder="Main page content..."
            className={`${inputClass} resize-y`}
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-400 mb-1">CTA Text</label>
          <input
            type="text"
            value={fields.cta_text}
            onChange={e => handleChange('cta_text', e.target.value)}
            placeholder="Call to action button text"
            className={inputClass}
          />
        </div>

        <div className="border-t border-slate-700 pt-4">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-3">SEO Metadata</p>
          <div className="space-y-3">
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-xs font-medium text-slate-400">Meta Title</label>
                <CharCounter value={fields.meta_title} max={60} />
              </div>
              <input
                type="text"
                value={fields.meta_title}
                onChange={e => handleChange('meta_title', e.target.value)}
                placeholder="SEO page title (60 chars max)"
                className={inputClass}
                maxLength={80}
              />
            </div>
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-xs font-medium text-slate-400">Meta Description</label>
                <CharCounter value={fields.meta_description} max={160} />
              </div>
              <textarea
                value={fields.meta_description}
                onChange={e => handleChange('meta_description', e.target.value)}
                rows={3}
                placeholder="SEO description (160 chars max)"
                className={`${inputClass} resize-none`}
                maxLength={200}
              />
            </div>
          </div>
        </div>
      </form>
    </div>
  )
}
