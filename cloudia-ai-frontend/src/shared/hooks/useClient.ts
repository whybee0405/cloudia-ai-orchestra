import { useQuery } from '@tanstack/react-query'
import { getClient, getBrandDNA, listPersonas } from '@/api/brand-dna'

export function useClient(clientId: string) {
  return useQuery({
    queryKey: ['clients', clientId],
    queryFn: () => getClient(clientId),
    enabled: !!clientId,
  })
}

export function useBrandDNA(clientId: string) {
  return useQuery({
    queryKey: ['brand-dna', clientId],
    queryFn: () => getBrandDNA(clientId),
    enabled: !!clientId,
    retry: false,
  })
}

export function usePersonas(clientId: string) {
  return useQuery({
    queryKey: ['personas', clientId],
    queryFn: () => listPersonas(clientId),
    enabled: !!clientId,
  })
}
