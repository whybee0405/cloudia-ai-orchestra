import { api } from './client';

export const getAssets = (filters = {}) =>
  api.get('/assets', { params: filters }).then((r) => r.data);

export const getAsset = (id) =>
  api.get(`/assets/${id}`).then((r) => r.data);

export const getAssetUrl = (id) =>
  `${import.meta.env.VITE_API_URL || 'http://localhost:8001'}/api/assets/${id}/file`;

export const updateAsset = (id, data) =>
  api.patch(`/assets/${id}`, data).then((r) => r.data);
