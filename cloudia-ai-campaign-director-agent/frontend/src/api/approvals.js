import { api } from './client';

export const getApprovals = () =>
  api.get('/approvals').then((r) => r.data);

export const approveGate = (gateId, notes = '') =>
  api.post(`/approvals/${gateId}/approve`, { notes }).then((r) => r.data);

export const rejectGate = (gateId, notes = '') =>
  api.post(`/approvals/${gateId}/reject`, { notes }).then((r) => r.data);
