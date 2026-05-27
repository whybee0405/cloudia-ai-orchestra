import { api } from './client';

export const getAnalytics = (filters = {}) =>
  api.get('/analytics', { params: filters }).then((r) => r.data);
