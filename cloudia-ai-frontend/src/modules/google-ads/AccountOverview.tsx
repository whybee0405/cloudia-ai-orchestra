import type { AdsAccount } from '@/api/google-ads'
import { Card, CardBody, CardHeader } from '@/shared/components/Card'
import { Badge } from '@/shared/components/Badge'

const STATUS_BADGE: Record<string, 'default' | 'success' | 'warning' | 'info'> = {
  calibrating: 'warning',
  active: 'success',
  paused: 'default',
  churned: 'default',
}

function MetricRow({ label, value }: { label: string; value: string | number | null }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-slate-100 last:border-0">
      <span className="text-xs text-slate-500">{label}</span>
      <span className="text-sm font-medium text-slate-800">
        {value != null ? String(value) : <span className="text-slate-300">—</span>}
      </span>
    </div>
  )
}

function fmt(n: number | null, prefix = ''): string | null {
  if (n == null) return null
  return `${prefix}${n.toLocaleString('en-ZA', { maximumFractionDigits: 2 })}`
}

function pct(n: number | null): string | null {
  if (n == null) return null
  return `${(n * 100).toFixed(2)}%`
}

export function AccountOverview({ account }: { account: AdsAccount }) {
  const status = account.status ?? 'calibrating'

  return (
    <div className="space-y-5">
      {/* Status + identity */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-700">Account</h2>
            <Badge variant={STATUS_BADGE[status] ?? 'default'} className="capitalize">
              {status}
            </Badge>
          </div>
        </CardHeader>
        <CardBody className="space-y-0">
          <MetricRow label="Customer ID" value={account.customer_id} />
          <MetricRow label="MCC ID" value={account.mcc_id} />
          <MetricRow label="Industry" value={account.industry} />
          <MetricRow label="Business type" value={account.business_type} />
          <MetricRow label="Budget sensitivity" value={account.budget_sensitivity} />
          <MetricRow label="Monthly ad spend" value={fmt(account.monthly_ad_spend, 'R')} />
        </CardBody>
      </Card>

      <div className="grid grid-cols-2 gap-5">
        {/* KPIs */}
        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold text-slate-700">KPI Targets</h2>
          </CardHeader>
          <CardBody className="space-y-0">
            <MetricRow
              label={account.primary_kpi ?? 'Primary KPI'}
              value={account.primary_kpi_target != null ? String(account.primary_kpi_target) : null}
            />
            <MetricRow
              label={account.secondary_kpi ?? 'Secondary KPI'}
              value={account.secondary_kpi_target != null ? String(account.secondary_kpi_target) : null}
            />
          </CardBody>
        </Card>

        {/* Baselines */}
        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold text-slate-700">Baseline Metrics</h2>
          </CardHeader>
          <CardBody className="space-y-0">
            <MetricRow label="CTR" value={pct(account.baseline_ctr)} />
            <MetricRow label="CVR" value={pct(account.baseline_cvr)} />
            <MetricRow label="CPC" value={fmt(account.baseline_cpc, 'R')} />
            <MetricRow label="CPA" value={fmt(account.baseline_cpa, 'R')} />
            <MetricRow label="ROAS" value={fmt(account.baseline_roas)} />
          </CardBody>
        </Card>
      </div>

      {status === 'calibrating' && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 text-sm text-amber-800">
          <strong>Calibrating</strong> — this account is in the 30-day baseline collection window.
          Agents will activate once baselines are established.
        </div>
      )}
    </div>
  )
}
