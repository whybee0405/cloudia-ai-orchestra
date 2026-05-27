import { api } from '../api.js';
import { toast } from '../components/toast.js';
import { modal } from '../components/modal.js';

// ─── Helpers ──────────────────────────────────────────────────────────────────

function fmtDate(v) {
  if (!v) return '—';
  return new Date(v).toLocaleString('en-ZA');
}

function fmtDelta(v) {
  if (v == null) return '—';
  const n = Number(v);
  if (isNaN(n)) return String(v);
  const formatted = (n >= 0 ? '+' : '') + n.toFixed(4);
  return `<span class="${n >= 0 ? 'text-success' : 'text-error'}">${formatted}</span>`;
}

function severityBadge(sev) {
  const map = {
    LOW:      'badge-gray',
    MEDIUM:   'badge-yellow',
    HIGH:     'badge-orange',
    CRITICAL: 'badge-red',
  };
  const cls = map[sev] || 'badge-gray';
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

// ─── Row detail modal ────────────────────────────────────────────────────────

function showAuditDetail(item, onAcknowledge) {
  const acknowledged = item.acknowledged ?? false;

  const diagHtml = item.diagnosis
    ? `<p>${escHtml(item.diagnosis)}</p>`
    : `<p class="text-muted">No diagnosis available.</p>`;

  const recommendedHtml = item.recommended_action
    ? `<p>${escHtml(item.recommended_action)}</p>`
    : `<p class="text-muted">No recommendation available.</p>`;

  const ackBtn = !acknowledged
    ? `<button id="ack-btn" class="btn btn-sm btn-primary">Acknowledge</button>`
    : `<span class="badge badge-green">Acknowledged</span>`;

  const body = `
    <div class="detail-block">
      <div class="detail-meta-row">
        <span class="detail-meta-item"><strong>Anomaly Type:</strong> ${escHtml(item.anomaly_type ?? item.type ?? '—')}</span>
        <span class="detail-meta-item"><strong>Severity:</strong> ${severityBadge(item.severity)}</span>
        <span class="detail-meta-item"><strong>Campaign ID:</strong> ${escHtml(String(item.campaign_id ?? '—'))}</span>
        <span class="detail-meta-item"><strong>Detected:</strong> ${fmtDate(item.created_at)}</span>
      </div>

      <h4 class="modal-section-title">Delta &amp; Threshold</h4>
      <div class="detail-kv-row">
        <div class="detail-kv">
          <span class="kv-label">Delta</span>
          <span class="kv-value">${fmtDelta(item.delta)}</span>
        </div>
        <div class="detail-kv">
          <span class="kv-label">Threshold</span>
          <span class="kv-value">${item.threshold != null ? Number(item.threshold).toFixed(4) : '—'}</span>
        </div>
        <div class="detail-kv">
          <span class="kv-label">Metric</span>
          <span class="kv-value">${escHtml(item.metric ?? '—')}</span>
        </div>
      </div>

      <h4 class="modal-section-title">Diagnosis</h4>
      ${diagHtml}

      <h4 class="modal-section-title">Recommended Action</h4>
      ${recommendedHtml}

      <div class="detail-ack-row">
        ${ackBtn}
      </div>
    </div>`;

  modal.show(`Audit Entry #${item.id}`, body);

  // Wire acknowledge button after modal renders
  setTimeout(() => {
    const btn = document.querySelector('#ack-btn');
    if (btn) {
      btn.addEventListener('click', () => {
        toast.info('Acknowledged locally.');
        item.acknowledged = true;
        onAcknowledge(item.id);
        // Close modal
        const closeBtn = document.querySelector('#modal-close');
        closeBtn?.click();
      });
    }
  }, 50);
}

// ─── Table builder ───────────────────────────────────────────────────────────

function buildTable(items, accounts, onRowClick) {
  if (items.length === 0) {
    return `
      <div class="empty-state">
        <div class="empty-icon empty-icon-check">
          <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" width="64" height="64">
            <circle cx="32" cy="32" r="30" stroke="var(--color-success, #22c55e)" stroke-width="3" fill="none"/>
            <polyline points="18,33 27,43 46,22" stroke="var(--color-success, #22c55e)" stroke-width="3"
              stroke-linecap="round" stroke-linejoin="round" fill="none"/>
          </svg>
        </div>
        <p class="empty-title">No anomalies detected</p>
        <p class="text-muted">All campaign metrics are within normal thresholds.</p>
      </div>`;
  }

  const accountMap = {};
  (accounts ?? []).forEach(a => { accountMap[a.id] = a.client_name ?? a.name ?? `Account ${a.id}`; });

  const rows = items.map(item => `
    <tr class="audit-row clickable-row" data-id="${item.id}" title="Click for details">
      <td>${item.id}</td>
      <td>${escHtml(accountMap[item.account_id] ?? String(item.account_id ?? '—'))}</td>
      <td>${escHtml(String(item.campaign_id ?? '—'))}</td>
      <td>${escHtml(item.anomaly_type ?? item.type ?? '—')}</td>
      <td>${severityBadge(item.severity)}</td>
      <td>${fmtDelta(item.delta)}</td>
      <td>${fmtDate(item.created_at)}</td>
      <td>
        ${item.acknowledged
          ? `<span class="badge badge-green">Yes</span>`
          : `<span class="badge badge-gray">No</span>`}
      </td>
    </tr>`).join('');

  return `
    <div class="table-scroll">
      <table class="table table-hoverable" id="audit-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Account</th>
            <th>Campaign ID</th>
            <th>Anomaly Type</th>
            <th>Severity</th>
            <th>Delta</th>
            <th>Time</th>
            <th>Acknowledged</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
}

// ─── Main render ──────────────────────────────────────────────────────────────

export async function renderAudit(container, workforceId) {
  let allItems   = [];
  let accounts   = [];
  let filterAccount  = '';
  let filterSeverity = '';
  let filterAck      = '';

  // ── Scaffold ─────────────────────────────────────────────────────────────
  container.innerHTML = `
    <div class="view-audit">
      <div class="card filter-bar">
        <div class="filter-group">
          <label class="filter-label" for="au-account">Account</label>
          <select id="au-account" class="select">
            <option value="">All Accounts</option>
          </select>
        </div>
        <div class="filter-group">
          <label class="filter-label" for="au-severity">Severity</label>
          <select id="au-severity" class="select">
            <option value="">All</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>
        </div>
        <div class="filter-group">
          <label class="filter-label" for="au-ack">Acknowledged</label>
          <select id="au-ack" class="select">
            <option value="">All</option>
            <option value="no">Unacknowledged</option>
          </select>
        </div>
      </div>

      <div class="card">
        <div id="audit-table-wrap">${spinner()}</div>
      </div>
    </div>`;

  const tableWrap  = container.querySelector('#audit-table-wrap');
  const selAccount = container.querySelector('#au-account');
  const selSev     = container.querySelector('#au-severity');
  const selAck     = container.querySelector('#au-ack');

  // ── Load accounts for dropdown ────────────────────────────────────────────
  try {
    accounts = await api.get('/accounts');
    (accounts ?? []).forEach(acc => {
      const opt = document.createElement('option');
      opt.value = acc.id;
      opt.textContent = acc.client_name ?? acc.name ?? `Account ${acc.id}`;
      selAccount.appendChild(opt);
    });
  } catch (_) { /* non-fatal */ }

  // ── Filter ────────────────────────────────────────────────────────────────
  function applyFilters() {
    let items = allItems;
    if (filterAccount)  items = items.filter(i => String(i.account_id) === filterAccount);
    if (filterSeverity) items = items.filter(i => i.severity === filterSeverity);
    if (filterAck === 'no') items = items.filter(i => !i.acknowledged);
    return items;
  }

  function onAcknowledge(id) {
    const item = allItems.find(i => i.id === id);
    if (item) item.acknowledged = true;
    renderTable();
  }

  function renderTable() {
    const filtered = applyFilters();
    tableWrap.innerHTML = buildTable(filtered, accounts, null);

    tableWrap.querySelectorAll('.audit-row').forEach(row => {
      row.addEventListener('click', () => {
        const item = allItems.find(i => String(i.id) === row.dataset.id);
        if (item) showAuditDetail(item, onAcknowledge);
      });
    });
  }

  // ── Load data ─────────────────────────────────────────────────────────────
  async function loadData() {
    try {
      let url = '/audit?limit=200';
      if (filterAccount)  url += `&account_id=${filterAccount}`;
      if (filterSeverity) url += `&severity=${filterSeverity}`;
      const data = await api.get(url);
      allItems = data ?? [];
      renderTable();
    } catch (err) {
      tableWrap.innerHTML = `<div class="card card-error"><p class="text-error">Failed to load audit log: ${escHtml(err.message ?? String(err))}</p></div>`;
    }
  }

  // ── Filter listeners ──────────────────────────────────────────────────────
  selAccount.addEventListener('change', (e) => { filterAccount = e.target.value; loadData(); });
  selSev.addEventListener('change',     (e) => { filterSeverity = e.target.value; loadData(); });
  selAck.addEventListener('change',     (e) => { filterAck = e.target.value; renderTable(); });

  await loadData();
}
