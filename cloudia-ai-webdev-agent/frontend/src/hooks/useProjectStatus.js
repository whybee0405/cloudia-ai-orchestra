import { useEffect, useRef, useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'

export function useProjectStatus(projectId) {
  const queryClient = useQueryClient()
  const wsRef = useRef(null)
  const reconnectTimerRef = useRef(null)
  const mountedRef = useRef(true)

  const connect = useCallback(() => {
    if (!projectId || !mountedRef.current) return

    const baseUrl = (import.meta.env.VITE_API_URL || 'http://localhost:8000')
      .replace('http://', 'ws://')
      .replace('https://', 'wss://')

    const ws = new WebSocket(`${baseUrl}/ws/projects/${projectId}`)
    wsRef.current = ws

    ws.onopen = () => {
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current)
        reconnectTimerRef.current = null
      }
    }

    ws.onmessage = (e) => {
      try {
        JSON.parse(e.data)
        queryClient.invalidateQueries({ queryKey: ['project', String(projectId)] })
        queryClient.invalidateQueries({ queryKey: ['project', Number(projectId)] })
      } catch {
        // non-JSON message, ignore
      }
    }

    ws.onerror = () => {
      ws.close()
    }

    ws.onclose = () => {
      if (mountedRef.current) {
        reconnectTimerRef.current = setTimeout(() => {
          connect()
        }, 3000)
      }
    }
  }, [projectId, queryClient])

  useEffect(() => {
    mountedRef.current = true
    connect()

    return () => {
      mountedRef.current = false
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current)
      }
      if (wsRef.current) {
        wsRef.current.onclose = null
        wsRef.current.close()
      }
    }
  }, [connect])

  return wsRef
}
