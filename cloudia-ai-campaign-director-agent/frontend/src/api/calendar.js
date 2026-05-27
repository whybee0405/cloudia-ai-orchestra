import { api } from './client';

export const getCalendar = (filters = {}) =>
  api.get('/calendar', { params: filters }).then((r) => r.data);

export const updateCalendarItem = (id, data) =>
  api.patch(`/calendar/${id}`, data).then((r) => r.data);

export const deleteCalendarItem = (id) =>
  api.delete(`/calendar/${id}`).then((r) => r.data);
