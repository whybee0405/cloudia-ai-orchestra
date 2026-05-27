import { api } from './client';

export const getScheduled = (filters = {}) =>
  api.get('/publishing/scheduled', { params: filters }).then((r) => r.data);

export const cancelPost = (id) =>
  api.post(`/publishing/${id}/cancel`).then((r) => r.data);
