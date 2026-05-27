import { useQuery } from '@tanstack/react-query';
import { getCampaign } from '../api/campaigns';

const POLLING_STATUSES = ['active', 'creating', 'planning'];

export function useCampaignStatus(id) {
  return useQuery({
    queryKey: ['campaign', id],
    queryFn: () => getCampaign(id),
    enabled: !!id,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return POLLING_STATUSES.includes(status) ? 5000 : false;
    },
    staleTime: 3000,
  });
}
