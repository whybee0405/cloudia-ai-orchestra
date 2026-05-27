import { useQuery } from '@tanstack/react-query';
import { getAnalytics } from '../api/analytics';

export function useAnalytics(filters = {}) {
  return useQuery({
    queryKey: ['analytics', filters],
    queryFn: () => getAnalytics(filters),
    staleTime: 60000,
    enabled: !!(filters.start_date && filters.end_date) || Object.keys(filters).length === 0,
  });
}
