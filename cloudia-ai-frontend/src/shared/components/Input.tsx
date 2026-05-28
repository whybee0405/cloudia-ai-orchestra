import type { InputHTMLAttributes, TextareaHTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  hint?: string
}

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string
  error?: string
  hint?: string
}

const fieldBase = 'w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent transition-shadow'

export function Input({ label, error, hint, className, id, ...props }: InputProps) {
  const inputId = id ?? label?.toLowerCase().replace(/\s+/g, '-')
  return (
    <div className="space-y-1">
      {label && <label htmlFor={inputId} className="block text-sm font-medium text-slate-700">{label}</label>}
      <input id={inputId} className={cn(fieldBase, error && 'border-red-400 focus:ring-red-400', className)} {...props} />
      {hint && !error && <p className="text-xs text-slate-500">{hint}</p>}
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  )
}

export function Textarea({ label, error, hint, className, id, ...props }: TextareaProps) {
  const inputId = id ?? label?.toLowerCase().replace(/\s+/g, '-')
  return (
    <div className="space-y-1">
      {label && <label htmlFor={inputId} className="block text-sm font-medium text-slate-700">{label}</label>}
      <textarea id={inputId} className={cn(fieldBase, 'resize-none', error && 'border-red-400', className)} {...props} />
      {hint && !error && <p className="text-xs text-slate-500">{hint}</p>}
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  )
}

interface TagInputProps {
  label?: string
  hint?: string
  tags: string[]
  onChange: (tags: string[]) => void
  placeholder?: string
}

export function TagInput({ label, hint, tags, onChange, placeholder = 'Type and press Enter' }: TagInputProps) {
  const add = (val: string) => {
    const trimmed = val.trim()
    if (trimmed && !tags.includes(trimmed)) onChange([...tags, trimmed])
  }
  const remove = (tag: string) => onChange(tags.filter(t => t !== tag))

  return (
    <div className="space-y-1">
      {label && <label className="block text-sm font-medium text-slate-700">{label}</label>}
      <div className={cn(fieldBase, 'flex flex-wrap gap-1.5 min-h-[42px] h-auto py-2 cursor-text')}
        onClick={e => (e.currentTarget.querySelector('input') as HTMLInputElement)?.focus()}>
        {tags.map(tag => (
          <span key={tag} className="inline-flex items-center gap-1 bg-brand-100 text-brand-700 text-xs font-medium px-2 py-0.5 rounded-md">
            {tag}
            <button type="button" onClick={() => remove(tag)} className="hover:text-brand-900 leading-none">×</button>
          </span>
        ))}
        <input
          className="flex-1 min-w-[120px] outline-none bg-transparent text-sm placeholder:text-slate-400"
          placeholder={tags.length === 0 ? placeholder : ''}
          onKeyDown={e => {
            if (e.key === 'Enter' || e.key === ',') {
              e.preventDefault()
              add(e.currentTarget.value)
              e.currentTarget.value = ''
            }
            if (e.key === 'Backspace' && !e.currentTarget.value && tags.length > 0) {
              remove(tags[tags.length - 1])
            }
          }}
          onBlur={e => { if (e.target.value) { add(e.target.value); e.target.value = '' } }}
        />
      </div>
      {hint && <p className="text-xs text-slate-500">{hint}</p>}
    </div>
  )
}
