import client from './client'

export function fetchProjects(status) {
  const params = status ? { status } : {}
  return client.get('/api/projects', { params })
}

export function fetchProject(id) {
  return client.get(`/api/projects/${id}`)
}

export function createProject(data) {
  return client.post('/api/projects', data)
}

export function cancelProject(id) {
  return client.delete(`/api/projects/${id}`)
}

export function retryTask(projectId, taskId) {
  return client.post(`/api/projects/${projectId}/retry/${taskId}`)
}

export function fetchClients() {
  return client.get('/api/projects/clients/')
}

export function createClient(data) {
  return client.post('/api/projects/clients/', data)
}
