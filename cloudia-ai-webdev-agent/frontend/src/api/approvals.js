import client from './client'

export function fetchPendingApprovals() {
  return client.get('/api/approvals')
}

export function fetchApproval(id) {
  return client.get(`/api/approvals/${id}`)
}

export function approveGate(id, reviewedBy) {
  return client.post(`/api/approvals/${id}/approve`, { reviewed_by: reviewedBy })
}

export function rejectGate(id, notes, reviewedBy) {
  return client.post(`/api/approvals/${id}/reject`, { notes, reviewed_by: reviewedBy })
}

export function requestRevision(id, notes, reviewedBy) {
  return client.post(`/api/approvals/${id}/request-revision`, { notes, reviewed_by: reviewedBy })
}
