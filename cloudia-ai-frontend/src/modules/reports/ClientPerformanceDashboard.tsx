import { useParams } from 'react-router-dom'
import { useQueries } from '@tanstack/react-query'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend,
} from 'recharts'
import { Megaphone, BarChart2, Globe, AlertTriangle, CheckCircle } from 'lucide-react'
import { getAdsSummary, getWebdevSummary, getCampaignSummary } from '@/api/reports'
import { Card, CardBody, CardHeader } from '@/shared/components/Card'
import { Badge } from '@/shared/components/Badge'

const WEBDEV_COLOR  = '#059669'
const CAMP_COLOR    = '#9333ea'

function StatRow({ label, value }: { label: string; value: string | number | null }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-slate-100 last:border-0">
      <span className="text-xs text-slate-500">{label}</span>
      <span className="text-xs font-semibold text-slate-800">{value ?? '—'}</span>
    </div>
  )
}

function NotConnected({ service }: { service: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-8 text-center">
      <p className="text-xs text-slate-400">No {service} account linked</p>
    </div>
  )
}

export function ClientPerformanceDashboard() {
  const { clientId } = useParams<{ clientId: string }>()
  const id = clientId!

  const [adsQ, webdevQ, campaignQ] = useQueries({
    queries: [
      {
        queryKey: ['reports-ads-summary', id],
        queryFn: () => getAdsSummary(id),
        retry: false,
      },
      {
        queryKey: ['reports-webdev-summary', id],
        queryFn: () => getWebdevSummary(id),
        retry: false,
      },
      {
        queryKey: ['reports-campaign-summary', id],
        queryFn: () => getCampaignSummary(id),
        retry: false,
      },
    ],
  })

  const adsOk     = !!adsQ.data && !adsQ.error
  const webdevOk  = !!webdevQ.data && !webdevQ.error
  const campaignOk = !!campaignQ.data && !campaignQ.error

  const ads     = adsQ.data
  const webdev  = webdevQ.data
  const campaign = campaignQ.data

  // Comparison chart data
  const chartData = [
    {
      name: 'Campaigns',
      Total:   campaign?.total_campaigns   ?? 0,
      Active:  campaign?.active_campaigns  ?? 0,
      Pending: campaign?.pending_gates     ?? 0,
      fill: CAMP_COLOR,
    },
    {
      name: 'Projects',
      Total:   webdev?.total_projects    ?? 0,
      Active:  webdev?.active_projects   ?? 0,
      Pending: webdev?.pending_gates     ?? 0,
      fill: WEBDEV_COLOR,
    },
  ]

  const adsStatusVariant = (s: string | null) => {
    if (!s) return 'default'
    if (s === 'active') return 'success'
    if (s === 'paused') return 'warning'
    if (s === 'suspended') return 'danger'
    return 'info'
  }

  return (
    <div className="space-y-6">
      {/* Summary cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Campaigns card */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-purple-50 flex items-center justify-center">
                <Megaphone className="w-3.5 h-3.5 text-purple-600" />
              </div>
              <h3 className="text-sm font-semibold text-slate-700">Social Campaigns</h3>
            </div>
          </CardHeader>
          <CardBody>
            {campaignOk && campaign ? (
              <>
                <div className="flex items-end gap-2 mb-4">
                  <span className="text-3xl font-bold text-slate-900">{campaign.total_campaigns}</span>
                  <span className="text-sm text-slate-400 mb-1">campaigns</span>
                </div>
                <StatRow label="Active"         value={campaign.active_campaigns} />
                <StatRow label="Pending approvals" value={campaign.pending_gates} />
                {campaign.latest_campaign_name && (
                  <StatRow label="Latest" value={campaign.latest_campaign_name} />
                )}
              </>
            ) : campaignQ.isLoading ? (
              <div className="py-6 text-center"><span className="text-xs text-slate-400">Loading…</span></div>
            ) : (
              <NotConnected service="Campaign Director" />
            )}
          </CardBody>
        </Card>

        {/* Google Ads card */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-blue-50 flex items-center justify-center">
                <BarChart2 className="w-3.5 h-3.5 text-blue-600" />
              </div>
              <h3 className="text-sm font-semibold text-slate-700">Google Ads</h3>
            </div>
          </CardHeader>
          <CardBody>
            {adsOk && ads ? (
              <>
                <div className="flex items-center gap-2 mb-4">
                  <Badge variant={adsStatusVariant(ads.account_status)} className="capitalize">
                    {ads.account_status ?? 'Unknown'}
                  </Badge>
                  <span className="text-xs text-slate-400">{ads.customer_id}</span>
                </div>
                <StatRow label="Anomalies (7 days)" value={ads.anomalies_last_7d} />
                <StatRow label="Critical anomalies"  value={ads.critical_anomalies_last_7d} />
                <StatRow label="Pending approvals"   value={ads.pending_queue_items} />
                {ads.baseline_roas != null && (
                  <StatRow label="Baseline ROAS" value={`${ads.baseline_roas.toFixed(2)}x`} />
                )}
              </>
            ) : adsQ.isLoading ? (
              <div className="py-6 text-center"><span className="text-xs text-slate-400">Loading…</span></div>
            ) : (
              <NotConnected service="Google Ads" />
            )}
          </CardBody>
        </Card>

        {/* WebDev card */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-emerald-50 flex items-center justify-center">
                <Globe className="w-3.5 h-3.5 text-emerald-600" />
              </div>
              <h3 className="text-sm font-semibold text-slate-700">Websites</h3>
            </div>
          </CardHeader>
          <CardBody>
            {webdevOk && webdev ? (
              <>
                <div className="flex items-end gap-2 mb-4">
                  <span className="text-3xl font-bold text-slate-900">{webdev.total_projects}</span>
                  <span className="text-sm text-slate-400 mb-1">projects</span>
                </div>
                <StatRow label="Active"    value={webdev.active_projects} />
                <StatRow label="Completed" value={webdev.completed_projects} />
                <StatRow label="Pending approvals" value={webdev.pending_gates} />
              </>
            ) : webdevQ.isLoading ? (
              <div className="py-6 text-center"><span className="text-xs text-slate-400">Loading…</span></div>
            ) : (
              <NotConnected service="WebDev" />
            )}
          </CardBody>
        </Card>
      </div>

      {/* Anomaly alert strip */}
      {adsOk && ads && (ads.critical_anomalies_last_7d > 0 || ads.pending_queue_items > 0) && (
        <div className="flex items-start gap-3 rounded-xl bg-amber-50 border border-amber-200 px-4 py-3">
          <AlertTriangle className="w-4 h-4 text-amber-600 mt-0.5 shrink-0" />
          <p className="text-sm text-amber-800">
            {ads.critical_anomalies_last_7d > 0 && (
              <><strong>{ads.critical_anomalies_last_7d} critical anomaly</strong>{ads.critical_anomalies_last_7d !== 1 ? 'ies' : ''} detected in the last 7 days. </>
            )}
            {ads.pending_queue_items > 0 && (
              <><strong>{ads.pending_queue_items} approval{ads.pending_queue_items !== 1 ? 's' : ''}</strong> pending in the Google Ads queue.</>
            )}
          </p>
        </div>
      )}

      {/* Comparison chart */}
      {(campaignOk || webdevOk) && (
        <Card>
          <CardHeader>
            <h3 className="text-sm font-semibold text-slate-700">Campaigns &amp; Projects Overview</h3>
          </CardHeader>
          <CardBody>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={chartData} barCategoryGap="30%" barGap={4}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                <Tooltip
                  contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e2e8f0' }}
                />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Bar dataKey="Total"   fill="#cbd5e1" radius={[4,4,0,0]} />
                <Bar dataKey="Active"  fill={CAMP_COLOR} radius={[4,4,0,0]} />
                <Bar dataKey="Pending" fill="#f59e0b" radius={[4,4,0,0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardBody>
        </Card>
      )}

      {/* Health summary row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3">
          <CheckCircle className={`w-5 h-5 shrink-0 ${campaignOk ? 'text-emerald-500' : 'text-slate-300'}`} />
          <div>
            <p className="text-xs font-medium text-slate-700">Campaigns</p>
            <p className="text-xs text-slate-400">{campaignOk ? 'Connected' : 'Not connected'}</p>
          </div>
        </div>
        <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3">
          <CheckCircle className={`w-5 h-5 shrink-0 ${adsOk ? 'text-emerald-500' : 'text-slate-300'}`} />
          <div>
            <p className="text-xs font-medium text-slate-700">Google Ads</p>
            <p className="text-xs text-slate-400">{adsOk ? 'Connected' : 'Not connected'}</p>
          </div>
        </div>
        <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3">
          <CheckCircle className={`w-5 h-5 shrink-0 ${webdevOk ? 'text-emerald-500' : 'text-slate-300'}`} />
          <div>
            <p className="text-xs font-medium text-slate-700">Websites</p>
            <p className="text-xs text-slate-400">{webdevOk ? 'Connected' : 'Not connected'}</p>
          </div>
        </div>
      </div>

      {/* KPI targets row */}
      {adsOk && ads && (ads.primary_kpi || ads.baseline_roas != null) && (
        <Card>
          <CardHeader>
            <h3 className="text-sm font-semibold text-slate-700">Google Ads KPI Targets</h3>
          </CardHeader>
          <CardBody>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              {ads.primary_kpi && (
                <div>
                  <p className="text-xs text-slate-500 mb-1">Primary KPI</p>
                  <p className="text-sm font-semibold text-blue-700 uppercase">{ads.primary_kpi}</p>
                </div>
              )}
              {ads.primary_kpi_target != null && (
                <div>
                  <p className="text-xs text-slate-500 mb-1">KPI Target</p>
                  <p className="text-sm font-semibold text-blue-700">{ads.primary_kpi_target}</p>
                </div>
              )}
              {ads.baseline_roas != null && (
                <div>
                  <p className="text-xs text-slate-500 mb-1">Baseline ROAS</p>
                  <p className="text-sm font-semibold text-blue-700">{ads.baseline_roas.toFixed(2)}x</p>
                </div>
              )}
              <div>
                <p className="text-xs text-slate-500 mb-1">Queue Items</p>
                <p className={`text-sm font-semibold ${ads.pending_queue_items > 0 ? 'text-amber-600' : 'text-emerald-600'}`}>
                  {ads.pending_queue_items}
                </p>
              </div>
            </div>
          </CardBody>
        </Card>
      )}
    </div>
  )
}
