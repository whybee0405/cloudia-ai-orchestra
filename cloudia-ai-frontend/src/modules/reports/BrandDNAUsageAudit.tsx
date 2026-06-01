import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
  BarChart, Bar,
} from 'recharts'
import { Dna, Users, Info } from 'lucide-react'
import { getBrandDNAUsage } from '@/api/reports'
import { Card, CardBody, CardHeader } from '@/shared/components/Card'
import { Badge } from '@/shared/components/Badge'
import { PageLoader } from '@/shared/components/LoadingSpinner'
import { DateRangePicker } from './components/DateRangePicker'

const SERVICE_BADGE: Record<string, 'default' | 'info' | 'success'> = {
  'campaign-director': 'default',
  'google-ads':        'info',
  'webdev':            'success',
}

const SERVICE_LABEL: Record<string, string> = {
  'campaign-director': 'Campaigns',
  'google-ads':        'Google Ads',
  'webdev':            'Websites',
}

function defaultFrom() {
  const d = new Date()
  d.setDate(d.getDate() - 30)
  return d.toISOString().slice(0, 10)
}

function defaultTo() {
  return new Date().toISOString().slice(0, 10)
}

export function BrandDNAUsageAudit() {
  const { clientId } = useParams<{ clientId: string }>()
  const [dateFrom, setDateFrom] = useState(defaultFrom)
  const [dateTo,   setDateTo]   = useState(defaultTo)

  const { data: usage, isLoading } = useQuery({
    queryKey: ['reports-brand-usage', clientId, dateFrom, dateTo],
    queryFn: () => getBrandDNAUsage(clientId!, { date_from: dateFrom, date_to: dateTo }),
    enabled: !!clientId,
  })

  if (isLoading) return <PageLoader />

  const serviceData = Object.entries(usage?.by_service ?? {}).map(([name, count]) => ({
    name: SERVICE_LABEL[name] ?? name,
    count,
  }))

  return (
    <div className="space-y-5">
      {/* Controls */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 className="text-sm font-medium text-slate-700">Brand DNA Context Usage</h3>
        <DateRangePicker
          dateFrom={dateFrom} dateTo={dateTo}
          onFromChange={setDateFrom} onToChange={setDateTo}
        />
      </div>

      {/* Total accesses stat */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="rounded-xl border border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center gap-2 mb-1">
            <Dna className="w-4 h-4 text-violet-500" />
            <p className="text-xs text-slate-500">Total Context Fetches</p>
          </div>
          <p className="text-3xl font-bold text-slate-900">{usage?.total_accesses ?? 0}</p>
          <p className="text-xs text-slate-400 mt-1">
            Brand DNA context served to agents
          </p>
        </div>
        {serviceData.map(s => (
          <div key={s.name} className="rounded-xl border border-slate-200 bg-white px-5 py-4">
            <p className="text-xs text-slate-500 mb-1">{s.name}</p>
            <p className="text-3xl font-bold text-violet-700">{s.count}</p>
            <p className="text-xs text-slate-400 mt-1">fetches</p>
          </div>
        ))}
      </div>

      {/* Daily trend chart */}
      {(usage?.by_day.length ?? 0) > 0 && (
        <Card>
          <CardHeader>
            <h3 className="text-sm font-semibold text-slate-700">Daily Access Trend</h3>
          </CardHeader>
          <CardBody>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={usage!.by_day}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={d => d.slice(5)} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                <Tooltip contentStyle={{ fontSize: 11, borderRadius: 8, border: '1px solid #e2e8f0' }} />
                <Line
                  type="monotone"
                  dataKey="count"
                  stroke="#7c3aed"
                  strokeWidth={2}
                  dot={false}
                  name="Fetches"
                />
              </LineChart>
            </ResponsiveContainer>
          </CardBody>
        </Card>
      )}

      {/* By service chart */}
      {serviceData.length > 0 && (
        <Card>
          <CardHeader>
            <h3 className="text-sm font-semibold text-slate-700">Accesses by Service</h3>
          </CardHeader>
          <CardBody>
            <ResponsiveContainer width="100%" height={150}>
              <BarChart data={serviceData} layout="vertical" barCategoryGap="30%">
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
                <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
                <YAxis dataKey="name" type="category" tick={{ fontSize: 11 }} width={90} />
                <Tooltip contentStyle={{ fontSize: 11, borderRadius: 8, border: '1px solid #e2e8f0' }} />
                <Bar dataKey="count" fill="#7c3aed" radius={[0,4,4,0]} name="Fetches" />
              </BarChart>
            </ResponsiveContainer>
          </CardBody>
        </Card>
      )}

      {/* By agent table */}
      {(usage?.by_agent.length ?? 0) > 0 && (
        <Card>
          <CardHeader>
            <h3 className="text-sm font-semibold text-slate-700">By Agent</h3>
          </CardHeader>
          <CardBody>
            <div>
              {usage!.by_agent.map(a => (
                <div key={`${a.service}::${a.agent_name}`} className="flex items-center justify-between py-2.5 border-b border-slate-100 last:border-0">
                  <div className="flex items-center gap-2">
                    <Badge variant={SERVICE_BADGE[a.service] ?? 'default'}>
                      {SERVICE_LABEL[a.service] ?? a.service}
                    </Badge>
                    <span className="text-xs text-slate-700">{a.agent_name.replace(/_/g, ' ')}</span>
                  </div>
                  <span className="text-xs font-semibold text-violet-700">{a.count}</span>
                </div>
              ))}
            </div>
          </CardBody>
        </Card>
      )}

      {/* Persona usage */}
      {(usage?.persona_usage.length ?? 0) > 0 && (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Users className="w-4 h-4 text-slate-400" />
              <h3 className="text-sm font-semibold text-slate-700">Persona Usage</h3>
            </div>
          </CardHeader>
          <CardBody>
            <div>
              {usage!.persona_usage.map(p => (
                <div key={p.persona_id} className="flex items-center justify-between py-2.5 border-b border-slate-100 last:border-0">
                  <span className="text-xs text-slate-700">{p.persona_name}</span>
                  <span className="text-xs font-semibold text-slate-600">{p.access_count} fetches</span>
                </div>
              ))}
            </div>
          </CardBody>
        </Card>
      )}

      {usage?.total_accesses === 0 && (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <Info className="w-8 h-8 text-slate-300 mb-3" />
          <p className="text-sm text-slate-500">No Brand DNA context fetches logged yet.</p>
          <p className="text-xs text-slate-400 mt-1">
            Access logs are recorded when agents fetch brand context during pipeline execution.
            Due to client-side caching (5 min TTL), log entries represent cache misses, not every prompt injection.
          </p>
        </div>
      )}
    </div>
  )
}
