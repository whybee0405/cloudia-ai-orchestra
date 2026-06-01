import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQueries } from '@tanstack/react-query'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend,
} from 'recharts'
import { DollarSign, Cpu } from 'lucide-react'
import { getDirectorClientByBrandDna } from '@/api/campaigns'
import { getAccountByBrandDna } from '@/api/google-ads'
import { getClientByBrandDna } from '@/api/webdev'
import { getCampaignAgentCosts, getAdsAgentCosts, getWebdevAgentCosts, type AgentCostReport as CostData } from '@/api/reports'
import { Card, CardBody, CardHeader } from '@/shared/components/Card'
import { Badge } from '@/shared/components/Badge'
import { PageLoader } from '@/shared/components/LoadingSpinner'
import { DateRangePicker } from './components/DateRangePicker'

const SERVICE_COLOR: Record<string, string> = {
  'campaign-director': '#9333ea',
  'google-ads':        '#2563eb',
  'webdev':            '#059669',
}

const SERVICE_LABEL: Record<string, string> = {
  'campaign-director': 'Campaigns',
  'google-ads':        'Google Ads',
  'webdev':            'Websites',
}

const SERVICE_BADGE: Record<string, 'default' | 'success' | 'info' | 'warning'> = {
  'campaign-director': 'default',
  'google-ads':        'info',
  'webdev':            'success',
}

function defaultFrom() {
  const d = new Date()
  d.setDate(d.getDate() - 30)
  return d.toISOString().slice(0, 10)
}

function defaultTo() {
  return new Date().toISOString().slice(0, 10)
}

function mergeDailyData(reports: (CostData | undefined)[]) {
  const byDay: Record<string, Record<string, number>> = {}

  for (const r of reports) {
    if (!r) continue
    for (const d of r.by_day) {
      if (!byDay[d.date]) byDay[d.date] = {}
      byDay[d.date][r.service] = (byDay[d.date][r.service] ?? 0) + d.cost_usd
    }
  }

  return Object.entries(byDay)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, values]) => ({ date, ...values }))
}

export function AgentCostReport() {
  const { clientId } = useParams<{ clientId: string }>()
  const [dateFrom, setDateFrom] = useState(defaultFrom)
  const [dateTo,   setDateTo]   = useState(defaultTo)
  const params = { date_from: dateFrom, date_to: dateTo }

  // Resolve service IDs
  const [directorQ, adsAccountQ, webdevClientQ] = useQueries({
    queries: [
      { queryKey: ['director-client', clientId], queryFn: () => getDirectorClientByBrandDna(clientId!), retry: false, enabled: !!clientId },
      { queryKey: ['ads-account', clientId],     queryFn: () => getAccountByBrandDna(clientId!),       retry: false, enabled: !!clientId },
      { queryKey: ['webdev-client', clientId],   queryFn: () => getClientByBrandDna(clientId!),        retry: false, enabled: !!clientId },
    ],
  })

  // Fetch cost data
  const [campCostQ, adsCostQ, webdevCostQ] = useQueries({
    queries: [
      {
        queryKey: ['reports-costs-campaign', directorQ.data?.id, dateFrom, dateTo],
        queryFn: () => getCampaignAgentCosts(directorQ.data!.id, params),
        enabled: !!directorQ.data?.id,
      },
      {
        queryKey: ['reports-costs-ads', adsAccountQ.data?.id, dateFrom, dateTo],
        queryFn: () => getAdsAgentCosts(adsAccountQ.data!.id, params),
        enabled: !!adsAccountQ.data?.id,
      },
      {
        queryKey: ['reports-costs-webdev', webdevClientQ.data?.id, dateFrom, dateTo],
        queryFn: () => getWebdevAgentCosts(webdevClientQ.data!.id, params),
        enabled: !!webdevClientQ.data?.id,
      },
    ],
  })

  const allReports = [campCostQ.data, adsCostQ.data, webdevCostQ.data]
  const chartData  = mergeDailyData(allReports)
  const anyLoading = directorQ.isLoading || adsAccountQ.isLoading || webdevClientQ.isLoading ||
                     campCostQ.isLoading  || adsCostQ.isLoading  || webdevCostQ.isLoading

  const totalCost   = allReports.reduce((s, r) => s + (r?.period_cost_usd ?? 0), 0)
  const totalTokens = allReports.reduce((s, r) => s + (r?.period_tokens ?? 0), 0)

  const activeServices = allReports.filter(Boolean)

  return (
    <div className="space-y-5">
      {/* Controls */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 className="text-sm font-medium text-slate-700">Agent Token &amp; Cost Usage</h3>
        <DateRangePicker
          dateFrom={dateFrom} dateTo={dateTo}
          onFromChange={setDateFrom} onToChange={setDateTo}
        />
      </div>

      {anyLoading ? (
        <PageLoader />
      ) : (
        <>
          {/* Total stats */}
          <div className="grid grid-cols-2 gap-4">
            <div className="rounded-xl border border-slate-200 bg-white px-5 py-4">
              <div className="flex items-center gap-2 mb-1">
                <DollarSign className="w-4 h-4 text-slate-400" />
                <p className="text-xs text-slate-500">Total Cost</p>
              </div>
              <p className="text-3xl font-bold text-slate-900">${totalCost.toFixed(4)}</p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white px-5 py-4">
              <div className="flex items-center gap-2 mb-1">
                <Cpu className="w-4 h-4 text-slate-400" />
                <p className="text-xs text-slate-500">Total Tokens</p>
              </div>
              <p className="text-3xl font-bold text-slate-900">{(totalTokens / 1000).toFixed(1)}k</p>
            </div>
          </div>

          {/* Stacked area chart */}
          {chartData.length > 0 && (
            <Card>
              <CardHeader>
                <h3 className="text-sm font-semibold text-slate-700">Daily Cost by Service</h3>
              </CardHeader>
              <CardBody>
                <ResponsiveContainer width="100%" height={240}>
                  <AreaChart data={chartData}>
                    <defs>
                      {activeServices.map(r => r && (
                        <linearGradient key={r.service} id={`grad-${r.service}`} x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%"  stopColor={SERVICE_COLOR[r.service]} stopOpacity={0.3} />
                          <stop offset="95%" stopColor={SERVICE_COLOR[r.service]} stopOpacity={0} />
                        </linearGradient>
                      ))}
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                    <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={d => d.slice(5)} />
                    <YAxis tick={{ fontSize: 11 }} tickFormatter={v => `$${v.toFixed(3)}`} />
                    <Tooltip
                      contentStyle={{ fontSize: 11, borderRadius: 8, border: '1px solid #e2e8f0' }}
                      formatter={(v) => [`$${Number(v).toFixed(4)}`, undefined]}
                    />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    {activeServices.map(r => r && (
                      <Area
                        key={r.service}
                        type="monotone"
                        dataKey={r.service}
                        name={SERVICE_LABEL[r.service] ?? r.service}
                        stroke={SERVICE_COLOR[r.service]}
                        fill={`url(#grad-${r.service})`}
                        strokeWidth={2}
                      />
                    ))}
                  </AreaChart>
                </ResponsiveContainer>
              </CardBody>
            </Card>
          )}

          {/* Per-service breakdown tables */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {allReports.map(r => {
              if (!r) return null
              return (
                <Card key={r.service}>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <h3 className="text-sm font-semibold text-slate-700">{SERVICE_LABEL[r.service] ?? r.service}</h3>
                      <Badge variant={SERVICE_BADGE[r.service] ?? 'default'}>
                        ${r.period_cost_usd.toFixed(4)}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardBody>
                    {r.by_agent.length === 0 ? (
                      <p className="text-xs text-slate-400 py-2">No agent runs in this period.</p>
                    ) : (
                      <div className="space-y-0">
                        {r.by_agent.map(a => (
                          <div key={a.agent_name} className="py-2 border-b border-slate-100 last:border-0">
                            <div className="flex items-center justify-between">
                              <span className="text-xs font-medium text-slate-700 truncate mr-2">
                                {a.agent_name.replace(/_/g, ' ')}
                              </span>
                              <span className="text-xs font-semibold text-slate-600 shrink-0">
                                ${a.cost_usd.toFixed(4)}
                              </span>
                            </div>
                            <div className="flex items-center gap-3 mt-0.5">
                              <span className="text-xs text-slate-400">{a.runs} run{a.runs !== 1 ? 's' : ''}</span>
                              <span className="text-xs text-slate-400">{(a.tokens / 1000).toFixed(1)}k tokens</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </CardBody>
                </Card>
              )
            })}
          </div>

          {activeServices.length === 0 && (
            <div className="py-12 text-center">
              <Cpu className="w-7 h-7 text-slate-300 mx-auto mb-2" />
              <p className="text-sm text-slate-500">No services connected.</p>
            </div>
          )}
        </>
      )}
    </div>
  )
}
