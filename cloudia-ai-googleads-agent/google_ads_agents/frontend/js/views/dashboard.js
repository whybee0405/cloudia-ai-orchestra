import { api } from '../api.js';
import { WORKFORCES } from '../config.js';
import { toast } from '../components/toast.js';
import { updateQueueBadge } from '../components/sidebar.js';

// ─── Helpers ─────────────────────────────────────────────────────────────────

function fmtDate(v) {
  if (!v) return '—';
  return new Date(v).toLocaleString('en-ZA');
}

function statusBadge(status) {
  const map = {
    pending:  'badge-pending',
    approved: 'badge-approved',
    executed: 'badge-executed',
    failed:   'badge-failed',
    rejected: 'badge-rejected',
  };
  const cls = map[status] || 'badge-skipped';
  return `<span class="badge ${cls}">${status ?? '—'}</span>`;
}

function severityBadge(sev) {
  const map = {
    LOW:      'badge-low',
    MEDIUM:   'badge-medium',
    HIGH:     'badge-high',
    CRITICAL: 'badge-critical',
  };
  const cls = map[(sev || '').toUpperCase()] || 'badge-low';
  return `<span class="badge ${cls}">${sev ?? '—'}</span>`;
}

function escHtml(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function spinner() {
  return `<div class="spinner-wrap"><div class="spinner"></div></div>`;
}

// ─── Stat Cards ───────────────────────────────────────────────────────────────

async function renderStatCards(el) {
  el.innerHTML = spinner();

  let accounts = [], queue = [], audit = [], health = null;

  const results = await Promise.allSettled([
    api.get('/accounts'),
    api.get('/queue'),
    api.get('/audit?limit=100'),
    api.get('/health'),
  ]);

  if (results[0].status === 'fulfilled') accounts = results[0].value ?? [];
  if (results[1].status === 'fulfilled') queue    = results[1].value ?? [];
  if (results[2].status === 'fulfilled') audit    = results[2].value ?? [];
  if (results[3].status === 'fulfilled') health   = results[3].value;

  const pendingCount = Array.isArray(queue)
    ? queue.filter(q => q.status === 'pending').length
    : (queue?.total ?? 0);

  // Sync sidebar badge for each active workforce
  WORKFORCES.filter(wf => !wf.disabled).forEach((wf) => {
    // Best-effort — use the google-ads count for now; individual fetches happen per view
    if (wf.id === 'google-ads') updateQueueBadge(wf.id, pendingCount);
  });

  // Anomalies last 24 h
  const since = Date.now() - 24 * 60 * 60 * 1000;
  const recentAnomalies = Array.isArray(audit)
    ? audit.filter(a => new Date(a.created_at).getTime() >= since).length
    : 0;

  const activeWorkforces = WORKFORCES.filter(wf => !wf.disabled).length;

  el.innerHTML = `
    <div class="stat-grid">
      <div class="stat-card">
        <div class="stat-card-icon primary">
          ${_svgAccounts()}
        </div>
        <div class="stat-card-body">
          <div class="stat-card-number">${accounts.length}</div>
          <div class="stat-card-label">Active Accounts</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-card-icon warning">
          ${_svgQueue()}
        </div>
        <div class="stat-card-body">
          <div class="stat-card-number">${pendingCount}</div>
          <div class="stat-card-label">Pending Queue Items</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-card-icon danger">
          ${_svgAudit()}
        </div>
        <div class="stat-card-body">
          <div class="stat-card-number">${recentAnomalies}</div>
          <div class="stat-card-label">Anomalies (last 24 h)</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-card-icon ${health ? 'success' : 'danger'}">
          ${_svgHealth()}
        </div>
        <div class="stat-card-body">
          <div class="stat-card-number">
            <span class="badge ${health ? 'badge-approved' : 'badge-failed'}" style="font-size:0.85rem;padding:4px 10px;">
              ${health ? 'Healthy' : 'Offline'}
            </span>
          </div>
          <div class="stat-card-label">API Status</div>
        </div>
      </div>
    </div>`;
}

// ─── Recent Queue Items ───────────────────────────────────────────────────────

async function renderRecentQueue(el) {
  el.innerHTML = spinner();

  let items = [];
  try {
    const all = await api.get('/queue?status=pending&limit=5');
    items = (Array.isArray(all) ? all : (all?.items ?? []))
      .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
      .slice(0, 5);
  } catch (err) {
    el.innerHTML = `<p class="text-error empty-inline">Failed to load queue items.</p>`;
    return;
  }

  if (items.length === 0) {
    el.innerHTML = `
      <div class="empty-state" style="padding:32px 24px;">
        ${_svgEmptyCheck()}
        <p class="empty-title">Queue is clear</p>
        <p class="text-muted" style="font-size:0.8rem;">No pending items right now.</p>
      </div>`;
    return;
  }

  const rows = items.map(item => `
    <tr class="clickable-row" data-route="/google-ads/queue">
      <td style="font-weight:500;">#${item.id}</td>
      <td>${escHtml(item.account_name ?? String(item.account_id ?? '—'))}</td>
      <td>${escHtml(item.agent ?? '—')}</td>
      <td>${escHtml(item.action_type ?? '—')}</td>
      <td>${statusBadge(item.status)}</td>
    </tr>`).join('');

  el.innerHTML = `
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Account</th>
            <th>Agent</th>
            <th>Action</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;

  el.querySelectorAll('.clickable-row').forEach(row => {
    row.addEventListener('click', () => window.navigate(row.dataset.route));
  });
}

// ─── Recent Audit / Anomalies ─────────────────────────────────────────────────

async function renderRecentAlerts(el) {
  el.innerHTML = spinner();

  let items = [];
  try {
    const all = await api.get('/audit?limit=5');
    items = Array.isArray(all) ? all : (all?.items ?? []);
  } catch (err) {
    el.innerHTML = `<p class="text-error empty-inline">Failed to load audit entries.</p>`;
    return;
  }

  if (items.length === 0) {
    el.innerHTML = `
      <div class="empty-state" style="padding:32px 24px;">
        ${_svgEmptyCheck()}
        <p class="empty-title">No recent anomalies</p>
        <p class="text-muted" style="font-size:0.8rem;">All metrics are within thresholds.</p>
      </div>`;
    return;
  }

  const rows = items.map(item => `
    <tr>
      <td style="font-weight:500;">#${item.id}</td>
      <td>${escHtml(String(item.campaign_id ?? '—'))}</td>
      <td>${escHtml(item.anomaly_type ?? item.type ?? '—')}</td>
      <td>${severityBadge(item.severity)}</td>
      <td class="text-muted" style="font-size:0.8rem;">${fmtDate(item.created_at)}</td>
    </tr>`).join('');

  el.innerHTML = `
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Campaign</th>
            <th>Type</th>
            <th>Severity</th>
            <th>Time</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
}

// ─── Workforce cards ──────────────────────────────────────────────────────────

function renderWorkforces(el) {
  const cards = WORKFORCES.map((wf) => {
    const disabled = !!wf.disabled;
    const initials = wf.name.split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase();

    return `
      <div class="workforce-card${disabled ? ' disabled' : ''}"
           ${!disabled ? `data-navigate="/${wf.id}/queue"` : ''}
           style="cursor:${disabled ? 'not-allowed' : 'pointer'}; opacity:${disabled ? '0.6' : '1'};">
        <div class="workforce-card-left">
          <div class="workforce-icon" style="background:${wf.color || '#64748b'};">${initials}</div>
          <div>
            <div class="workforce-card-name">${escHtml(wf.name)}</div>
            <div class="workforce-card-desc">${escHtml(wf.description || '')}</div>
          </div>
        </div>
        <div class="flex items-center gap-2">
          ${disabled
            ? '<span class="badge badge-skipped">Coming soon</span>'
            : '<span class="badge badge-approved">Active</span><span style="color:var(--text-muted);margin-left:4px;">›</span>'
          }
        </div>
      </div>`;
  }).join('');

  el.innerHTML = cards;

  el.querySelectorAll('[data-navigate]').forEach(card => {
    card.addEventListener('click', () => window.navigate(card.dataset.navigate));
  });
}

// ─── Main render ──────────────────────────────────────────────────────────────

export async function renderDashboard(container) {
  container.innerHTML = `
    <div class="dashboard-section">
      <!-- Stat cards -->
      <div id="dash-stat-cards"></div>

      <!-- Workforce summary -->
      <div class="mt-6 mb-4">
        <p class="section-title">Workforces</p>
        <div id="dash-workforces" style="display:flex;flex-direction:column;gap:10px;"></div>
      </div>

      <!-- Two-col: queue + alerts -->
      <div class="two-col">
        <div class="card">
          <div class="card-header">
            <h3>Pending Queue Items</h3>
            <button class="btn btn-ghost btn-sm" data-navigate="/google-ads/queue">View all ›</button>
          </div>
          <div id="dash-recent-queue" class="card-body no-pad"></div>
        </div>

        <div class="card">
          <div class="card-header">
            <h3>Recent Anomalies</h3>
            <button class="btn btn-ghost btn-sm" data-navigate="/google-ads/audit">View all ›</button>
          </div>
          <div id="dash-recent-alerts" class="card-body no-pad"></div>
        </div>
      </div>
    </div>`;

  const statEl     = container.querySelector('#dash-stat-cards');
  const wfEl       = container.querySelector('#dash-workforces');
  const queueEl    = container.querySelector('#dash-recent-queue');
  const alertEl    = container.querySelector('#dash-recent-alerts');

  // Wire up "View all" navigation buttons in the two-col section headers
  container.querySelectorAll('[data-navigate]').forEach(btn => {
    btn.addEventListener('click', () => window.navigate(btn.dataset.navigate));
  });

  // Render workforces synchronously (no API needed)
  renderWorkforces(wfEl);

  // Parallel async loads — each section handles its own loading / error state
  await Promise.all([
    renderStatCards(statEl),
    renderRecentQueue(queueEl),
    renderRecentAlerts(alertEl),
  ]);
}

// ─── SVG icons ────────────────────────────────────────────────────────────────

function _svgAccounts() {
  return `<svg viewBox="0 0 22 22" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="11" cy="7" r="4"/><path d="M3 20c0-4.42 3.58-8 8-8s8 3.58 8 8"/>
  </svg>`;
}

function _svgQueue() {
  return `<svg viewBox="0 0 22 22" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
    <rect x="3" y="3" width="16" height="4" rx="1.5"/>
    <rect x="3" y="9" width="16" height="4" rx="1.5"/>
    <rect x="3" y="15" width="10" height="4" rx="1.5"/>
    <path d="M16 16.5l2 2 3-3"/>
  </svg>`;
}

function _svgAudit() {
  return `<svg viewBox="0 0 22 22" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
    <path d="M14 2H6a2 2 0 00-2 2v14a2 2 0 002 2h10a2 2 0 002-2V8z"/>
    <polyline points="14 2 14 8 20 8"/>
    <line x1="8" y1="12" x2="14" y2="12"/>
    <line x1="8" y1="16" x2="12" y2="16"/>
  </svg>`;
}

function _svgHealth() {
  return `<svg viewBox="0 0 22 22" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
    <path d="M11 2a9 9 0 100 18A9 9 0 0011 2z"/>
    <polyline points="7 11 10 14 15 9"/>
  </svg>`;
}

function _svgEmptyCheck() {
  return `<svg style="width:40px;height:40px;color:#cbd5e1;" viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="24" cy="24" r="20"/>
    <polyline points="14,25 21,32 34,18"/>
  </svg>`;
}
