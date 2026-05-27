import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { approveGate, rejectGate, requestRevision } from '../api/approvals'

export function useApprovals(projectId) {
  const queryClient = useQueryClient()
  const [error, setError] = useState(null)

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['approvals'] })
    if (projectId) {
      queryClient.invalidateQueries({ queryKey: ['project', String(projectId)] })
      queryClient.invalidateQueries({ queryKey: ['project', Number(projectId)] })
    }
  }

  const approveMutation = useMutation({
    mutationFn: ({ id, reviewedBy }) => approveGate(id, reviewedBy),
    onSuccess: () => {
      setError(null)
      invalidate()
    },
    onError: (err) => {
      setError(err.message)
    },
  })

  const rejectMutation = useMutation({
    mutationFn: ({ id, notes, reviewedBy }) => rejectGate(id, notes, reviewedBy),
    onSuccess: () => {
      setError(null)
      invalidate()
    },
    onError: (err) => {
      setError(err.message)
    },
  })

  const revisionMutation = useMutation({
    mutationFn: ({ id, notes, reviewedBy }) => requestRevision(id, notes, reviewedBy),
    onSuccess: () => {
      setError(null)
      invalidate()
    },
    onError: (err) => {
      setError(err.message)
    },
  })

  return {
    approve: (id, reviewedBy) => approveMutation.mutateAsync({ id, reviewedBy }),
    reject: (id, notes, reviewedBy) => rejectMutation.mutateAsync({ id, notes, reviewedBy }),
    requestRevision: (id, notes, reviewedBy) => revisionMutation.mutateAsync({ id, notes, reviewedBy }),
    isApproving: approveMutation.isPending,
    isRejecting: rejectMutation.isPending,
    isRequestingRevision: revisionMutation.isPending,
    error,
    clearError: () => setError(null),
  }
}
