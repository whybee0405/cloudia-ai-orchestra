import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getAssets, getAsset, updateAsset } from '../api/assets';

export function useAssets(filters = {}) {
  return useQuery({
    queryKey: ['assets', filters],
    queryFn: () => getAssets(filters),
    staleTime: 10000,
  });
}

export function useAsset(id) {
  return useQuery({
    queryKey: ['asset', id],
    queryFn: () => getAsset(id),
    enabled: !!id,
  });
}

export function useUpdateAsset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }) => updateAsset(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['assets'] });
      queryClient.invalidateQueries({ queryKey: ['asset', id] });
    },
  });
}
