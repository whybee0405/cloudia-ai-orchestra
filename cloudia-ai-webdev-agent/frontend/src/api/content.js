import client from './client'

export function fetchProjectContent(projectId) {
  return client.get(`/api/content/project/${projectId}`)
}

export function updateContent(id, data) {
  return client.patch(`/api/content/${id}`, data)
}

export function approveContent(id) {
  return client.post(`/api/content/${id}/approve`)
}

export function bulkApproveContent(projectId) {
  return client.post(`/api/content/project/${projectId}/approve-all`)
}

export function regenerateContent(id) {
  return client.post(`/api/content/${id}/regenerate`)
}
