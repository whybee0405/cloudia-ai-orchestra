import { api } from './client';

export const getCampaigns = (filters = {}) =>
  api.get('/campaigns', { params: filters }).then((r) => r.data);

export const getCampaign = (id) =>
  api.get(`/campaigns/${id}`).then((r) => r.data);

export const createCampaign = (data) =>
  api.post('/campaigns', data).then((r) => r.data);

export const pauseCampaign = (id) =>
  api.post(`/campaigns/${id}/pause`).then((r) => r.data);

export const resumeCampaign = (id) =>
  api.post(`/campaigns/${id}/resume`).then((r) => r.data);
