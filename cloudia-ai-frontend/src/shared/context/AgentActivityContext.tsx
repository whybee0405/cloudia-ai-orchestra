import { createContext, useCallback, useContext, useReducer, type ReactNode } from 'react'

export type AgentType = 'brand-dna' | 'campaign-director' | 'google-ads' | 'webdev'
export type JobStatus = 'running' | 'completed' | 'error'

export interface AgentJob {
  id: string
  agentType: AgentType
  clientId: string
  clientName: string
  task: string
  status: JobStatus
  startedAt: number
  completedAt?: number
  error?: string
}

type Action =
  | { type: 'START'; job: AgentJob }
  | { type: 'COMPLETE'; id: string }
  | { type: 'FAIL'; id: string; error?: string }

function reducer(state: AgentJob[], action: Action): AgentJob[] {
  switch (action.type) {
    case 'START':
      return [action.job, ...state].slice(0, 200)
    case 'COMPLETE':
      return state.map(j =>
        j.id === action.id ? { ...j, status: 'completed' as const, completedAt: Date.now() } : j
      )
    case 'FAIL':
      return state.map(j =>
        j.id === action.id ? { ...j, status: 'error' as const, error: action.error, completedAt: Date.now() } : j
      )
    default:
      return state
  }
}

interface ContextValue {
  jobs: AgentJob[]
  startJob: (p: Omit<AgentJob, 'id' | 'startedAt' | 'status'>) => string
  completeJob: (id: string) => void
  failJob: (id: string, error?: string) => void
}

const Ctx = createContext<ContextValue | null>(null)

export function AgentActivityProvider({ children }: { children: ReactNode }) {
  const [jobs, dispatch] = useReducer(reducer, [])

  const startJob = useCallback((p: Omit<AgentJob, 'id' | 'startedAt' | 'status'>) => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
    dispatch({ type: 'START', job: { ...p, id, status: 'running', startedAt: Date.now() } })
    return id
  }, [])

  const completeJob = useCallback((id: string) => {
    dispatch({ type: 'COMPLETE', id })
  }, [])

  const failJob = useCallback((id: string, error?: string) => {
    dispatch({ type: 'FAIL', id, error })
  }, [])

  return (
    <Ctx.Provider value={{ jobs, startJob, completeJob, failJob }}>
      {children}
    </Ctx.Provider>
  )
}

export function useAgentActivity() {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useAgentActivity requires AgentActivityProvider')
  return ctx
}
