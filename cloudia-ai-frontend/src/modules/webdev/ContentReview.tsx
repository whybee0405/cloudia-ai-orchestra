import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { CheckCircle, RefreshCw, Edit3, ChevronDown, ChevronUp, CheckSquare } from 'lucide-react'
import {
  getProjectContent,
  updateContent,
  approveContent,
  approveAllContent,
  regenerateContent,
  type ContentPiece,
  type ContentUpdate,
} from '@/api/webdev'
import { Card, CardBody, CardHeader } from '@/shared/components/Card'
import { Button } from '@/shared/components/Button'
import { Badge } from '@/shared/components/Badge'
import { PageLoader } from '@/shared/components/LoadingSpinner'

const STATUS_BADGE: Record<string, 'default' | 'success' | 'warning' | 'info'> = {
  draft: 'default',
  approved: 'success',
  revision_requested: 'warning',
  regenerating: 'info',
}

function ContentCard({ piece, projectId }: { piece: ContentPiece; projectId: number }) {
  const qc = useQueryClient()
  const [expanded, setExpanded] = useState(false)
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState<ContentUpdate>({})

  const invalidate = () => qc.invalidateQueries({ queryKey: ['webdev-content', projectId] })

  const { mutate: approve, isPending: approving } = useMutation({
    mutationFn: () => approveContent(piece.id),
    onSuccess: invalidate,
  })
  const { mutate: regenerate, isPending: regenerating } = useMutation({
    mutationFn: () => regenerateContent(piece.id),
    onSuccess: invalidate,
  })
  const { mutate: save, isPending: saving } = useMutation({
    mutationFn: () => updateContent(piece.id, draft),
    onSuccess: () => { invalidate(); setEditing(false) },
  })

  const isApproved = piece.status === 'approved'

  return (
    <Card className={isApproved ? 'border-green-200 bg-green-50/20' : ''}>
      <CardBody className="space-y-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <Badge variant={STATUS_BADGE[piece.status] ?? 'default'} className="capitalize">
                {piece.status.replace(/_/g, ' ')}
              </Badge>
              <span className="text-xs text-slate-400 uppercase tracking-wide">{piece.content_type}</span>
              {piece.page_slug && <span className="text-xs text-slate-400">/{piece.page_slug}</span>}
            </div>
            <p className="text-sm font-semibold text-slate-800 truncate">
              {piece.title ?? piece.h1 ?? `Content #${piece.id}`}
            </p>
          </div>
          <button
            onClick={() => setExpanded(o => !o)}
            className="text-slate-400 hover:text-slate-600 transition-colors shrink-0"
          >
            {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>

        {expanded && (
          <div className="space-y-3 pt-1 border-t border-slate-100">
            {editing ? (
              <div className="space-y-3">
                {(['title', 'h1', 'body_content', 'cta_text', 'meta_title', 'meta_description'] as const).map(field => (
                  <div key={field}>
                    <label className="block text-xs font-medium text-slate-500 mb-1 capitalize">
                      {field.replace(/_/g, ' ')}
                    </label>
                    {field === 'body_content' ? (
                      <textarea
                        rows={6}
                        className="w-full text-xs border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-1 focus:ring-brand-500 resize-none font-mono"
                        defaultValue={piece[field] ?? ''}
                        onChange={e => setDraft(d => ({ ...d, [field]: e.target.value }))}
                      />
                    ) : (
                      <input
                        className="w-full text-xs border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-1 focus:ring-brand-500"
                        defaultValue={piece[field] ?? ''}
                        onChange={e => setDraft(d => ({ ...d, [field]: e.target.value }))}
                      />
                    )}
                  </div>
                ))}
                <div className="flex items-center gap-2">
                  <Button size="sm" onClick={() => save()} loading={saving}>Save</Button>
                  <Button size="sm" variant="secondary" onClick={() => setEditing(false)}>Cancel</Button>
                </div>
              </div>
            ) : (
              <div className="space-y-2 text-xs text-slate-600">
                {piece.h1 && <p><span className="font-medium text-slate-400">H1:</span> {piece.h1}</p>}
                {piece.body_content && (
                  <p className="leading-relaxed line-clamp-5 whitespace-pre-line">{piece.body_content}</p>
                )}
                {piece.meta_title && <p><span className="font-medium text-slate-400">Meta title:</span> {piece.meta_title}</p>}
                {piece.meta_description && <p><span className="font-medium text-slate-400">Meta desc:</span> {piece.meta_description}</p>}
              </div>
            )}
          </div>
        )}

        {!isApproved && !editing && (
          <div className="flex items-center gap-2 pt-1">
            <Button size="sm" onClick={() => approve()} loading={approving}>
              <CheckCircle className="w-3.5 h-3.5" /> Approve
            </Button>
            <Button size="sm" variant="secondary" onClick={() => setEditing(true)}>
              <Edit3 className="w-3.5 h-3.5" /> Edit
            </Button>
            <Button size="sm" variant="secondary" onClick={() => regenerate()} loading={regenerating}>
              <RefreshCw className="w-3.5 h-3.5" /> Regenerate
            </Button>
          </div>
        )}
      </CardBody>
    </Card>
  )
}

export function ContentReview({ projectId }: { projectId: number }) {
  const qc = useQueryClient()

  const { data: content, isLoading } = useQuery({
    queryKey: ['webdev-content', projectId],
    queryFn: () => getProjectContent(projectId),
  })

  const { mutate: approveAll, isPending: approvingAll } = useMutation({
    mutationFn: () => approveAllContent(projectId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['webdev-content', projectId] }),
  })

  if (isLoading) return <PageLoader />

  const unapproved = (content ?? []).filter(c => c.status !== 'approved').length

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-semibold text-slate-700">Content Review</h2>
              <span className="text-xs text-slate-400">{content?.length ?? 0} piece{content?.length !== 1 ? 's' : ''}</span>
            </div>
            {unapproved > 0 && (
              <Button size="sm" onClick={() => approveAll()} loading={approvingAll}>
                <CheckSquare className="w-3.5 h-3.5" /> Approve All ({unapproved})
              </Button>
            )}
          </div>
        </CardHeader>
      </Card>

      {(content ?? []).length === 0 && (
        <Card>
          <CardBody className="py-12 text-center">
            <p className="text-sm text-slate-400">No content generated yet. The pipeline is still running.</p>
          </CardBody>
        </Card>
      )}

      {content?.map(piece => (
        <ContentCard key={piece.id} piece={piece} projectId={projectId} />
      ))}
    </div>
  )
}
