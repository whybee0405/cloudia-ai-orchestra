import { api } from '../api.js';
import { toast } from '../components/toast.js';
import { modal } from '../components/modal.js';
import { WORKFORCES } from '../config.js';
import { updateQueueBadge } from '../components/sidebar.js';

// ─── Helpers ─────────────────────────────────────────────────────────────────

function fmtDate(v) {
  if (!v) return '—';
  return new Date(v).toLocaleString('en-ZA');
}

function statusBadge(status) {
  const map = {
    pending:  'badge-yellow',
    approved: 'badge-blue',
    executed: 'badge-green',
    failed:   'badge-red',
    rejected: 'badge-gray',
  };
  const cls = map[status] || 'badge-gray';
  return `<span class="badge ${cls}">${status ?? '—'}</span>`;
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

// ─── Badge update helper ──────────────────────────────────────────────────────

async function refreshBadge(workforceId) {
  try {
    const all = await api.get('/queue');
    const count = (all ?? []).filter(i => i.status === 'pending').length;
    updateQueueBadge(workforceId, count);
  } catch (_) {
    // badge update is best-effort
  }
}

// ─── Action Handlers ─────────────────────────────────────────────────────────

function handleApprove(item, workforceId, refreshFn) {
  modal.form(
    'Approve Queue Item',
    [
      {
        name: 'reviewed_by',
        label: 'Your Name',
        type: 'text',
        required: true,
        placeholder: 'e.g. Jane Smith',
      },
    ],
    async (data) => {
      try {
        await api.post(`/queue/${item.id}/approve`, { reviewed_by: data.reviewed_by });
        toast.success(`Item #${item.id} approved.`);
        await refreshBadge(workforceId);
        refreshFn();
      } catch (err) {
        toast.error(`Approve failed: ${err.message ?? err}`);
      }
    }
  );
}

function handleReject(item, workforceId, refreshFn) {
  modal.form(
    'Reject Queue Item',
    [
      {
        name: 'reviewed_by',
        label: 'Your Name',
        type: 'text',
        required: true,
        placeholder: 'e.g. Jane Smith',
      },
      {
        name: 'reason',
        label: 'Reason (optional)',
        type: 'text',
        required: false,
        placeholder: 'e.g. Budget not approved',
      },
    ],
    async (data) => {
      try {
        await api.post(`/queue/${item.id}/reject`, { reviewed_by: data.reviewed_by, reason: data.reason });
        toast.success(`Item #${item.id} rejected.`);
        await refreshBadge(workforceId);
        refreshFn();
      } catch (err) {
        toast.error(`Reject failed: ${err.message ?? err}`);
      }
    }
  );
}

function handleExecute(item, workforceId, refreshFn) {
  modal.confirm(
    'Execute this action?',
    `<p>You are about to <strong>execute</strong> queue item <strong>#${item.id}</strong>.</p>
     <p class="text-muted">This will apply the agent's recommended change to the live Google Ads account. This action cannot be undone.</p>`,
    async () => {
      try {
        await api.post(`/queue/${item.id}/execute`, {});
        toast.success(`Item #${item.id} executed.`);
        await refreshBadge(workforceId);
        refreshFn();
      } catch (err) {
        toast.error(`Execute failed: ${err.message ?? err}`);
      }
    }
  );
}

function handleDetails(item) {
  let payloadHtml = '—';
  if (item.action_payload) {
    try {
      const pretty = JSON.stringify(
        typeof item.action_payload === 'string' ? JSON.parse(item.action_payload) : item.action_payload,
        null, 2
      );
      payloadHtml = `<pre class="json-viewer">${escHtml(pretty)}</pre>`;
    } catch (_) {
      payloadHtml = `<pre class="json-viewer">${escHtml(String(item.action_payload))}</pre>`;
    }
  }

  const reasoning = item.reasoning
    ? `<p>${escHtml(item.reasoning)}</p>`
    : `<p class="text-muted">No reasoning provided.</p>`;

  let historyHtml = '';
  if (Array.isArray(item.status_history) && item.status_history.length > 0) {
    const rows = item.status_history.map(h => `
      <tr>
        <td>${escHtml(h.status ?? '—')}</td>
        <td>${escHtml(h.changed_by ?? '—')}</td>
        <td>${fmtDate(h.changed_at)}</td>
        <td>${escHtml(h.note ?? '—')}</td>
      </tr>`).join('');
    historyHtml = `
      <h4 class="modal-section-title">Status History</h4>
      <div class="table-scroll">
        <table class="table table-sm">
          <thead><tr><th>Status</th><th>By</th><th>At</th><th>Note</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;
  }

  modal.show(
    `Queue Item #${item.id} — Details`,
    `<div class="detail-block">
       <h4 class="modal-section-title">Reasoning</h4>
       ${reasoning}
       <h4 class="modal-section-title">Action Payload</h4>
       ${payloadHtml}
       ${historyHtml}
     </div>`
  );
}

// ─── Table render ─────────────────────────────────────────────────────────────

function buildTable(items, workforceId, refreshFn) {
  if (items.length === 0) {
    return `<div class="empty-state">
      <div class="empty-icon">&#x1F4ED;</div>
      <p class="empty-title">No queue items found</p>
      <p class="text-muted">Adjust your filters or wait for the agent to create new actions.</p>
    </div>`;
  }

  const rows = items.map(item => {
    let actions = `<button class="btn btn-sm btn-ghost details-btn" data-id="${item.id}">Details</button>`;
    if (item.status === 'pending') {
      actions = `
        <button class="btn btn-sm btn-success approve-btn" data-id="${item.id}">Approve</button>
        <button class="btn btn-sm btn-danger reject-btn" data-id="${item.id}">Reject</button>
        ${actions}`;
    } else if (item.status === 'approved') {
      actions = `<button class="btn btn-sm btn-primary execute-btn" data-id="${item.id}">Execute</button>${actions}`;
    }

    return `
      <tr data-id="${item.id}">
        <td>${item.id}</td>
        <td>${escHtml(item.account_name ?? String(item.account_id ?? '—'))}</td>
        <td>${escHtml(item.agent ?? '—')}</td>
        <td>${escHtml(item.action_type ?? '—')}</td>
        <td>${escHtml(item.target_name ?? '—')}</td>
        <td>${statusBadge(item.status)}</td>
        <td>${fmtDate(item.created_at)}</td>
        <td class="actions-cell">${actions}</td>
      </tr>`;
  }).join('');

  const html = `
    <div class="table-scroll">
      <table class="table" id="queue-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Account</th>
            <th>Agent</th>
            <th>Action Type</th>
            <th>Target Name</th>
            <th>Status</th>
            <th>Created At</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;

  return html;
}

// ─── Main render ──────────────────────────────────────────────────────────────

export async function renderQueue(container, workforceId) {
  // State
  let allItems = [];
  let accounts = [];
  let filterAccount = '';
  let filterStatus  = '';
  let filterAgent   = '';
  let pollTimer     = null;

  const agents = WORKFORCES?.[workforceId]?.agents ?? [];

  // ── Initial scaffold ─────────────────────────────────────────────────────
  container.innerHTML = `
    <div class="view-queue">
      <div class="card filter-bar">
        <div class="filter-group">
          <label class="filter-label" for="q-account">Account</label>
          <select id="q-account" class="select">
            <option value="">All Accounts</option>
          </select>
        </div>
        <div class="filter-group">
          <label class="filter-label" for="q-status">Status</label>
          <select id="q-status" class="select">
            <option value="">All</option>
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
            <option value="executed">Executed</option>
            <option value="failed">Failed</option>
          </select>
        </div>
        ${agents.length > 0 ? `
        <div class="filter-group">
          <label class="filter-label" for="q-agent">Agent</label>
          <select id="q-agent" class="select">
            <option value="">All Agents</option>
            ${agents.map(a => `<option value="${escHtml(a)}">${escHtml(a)}</option>`).join('')}
          </select>
        </div>` : ''}
        <div class="filter-group filter-group-right">
          <span id="q-last-updated" class="text-muted text-sm"></span>
        </div>
      </div>

      <div class="card">
        <div id="queue-table-wrap">${spinner()}</div>
      </div>
    </div>`;

  const tableWrap   = container.querySelector('#queue-table-wrap');
  const lastUpdEl   = container.querySelector('#q-last-updated');
  const selAccount  = container.querySelector('#q-account');
  const selStatus   = container.querySelector('#q-status');
  const selAgent    = container.querySelector('#q-agent');

  // ── Populate account dropdown ────────────────────────────────────────────
  try {
    accounts = await api.get('/accounts');
    (accounts ?? []).forEach(acc => {
      const opt = document.createElement('option');
      opt.value = acc.id;
      opt.textContent = acc.client_name ?? acc.name ?? `Account ${acc.id}`;
      selAccount.appendChild(opt);
    });
  } catch (_) {
    // non-fatal — filter just won't have account names
  }

  // ── Filter + render ──────────────────────────────────────────────────────
  function applyFilters() {
    let items = allItems;
    if (filterAccount) items = items.filter(i => String(i.account_id) === filterAccount);
    if (filterStatus)  items = items.filter(i => i.status === filterStatus);
    if (filterAgent)   items = items.filter(i => i.agent === filterAgent);
    return items;
  }

  function renderTable() {
    const filtered = applyFilters();
    tableWrap.innerHTML = buildTable(filtered, workforceId, loadData);
    attachTableHandlers(tableWrap);
  }

  function attachTableHandlers(wrap) {
    wrap.querySelectorAll('.approve-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const item = allItems.find(i => i.id == btn.dataset.id);
        if (item) handleApprove(item, workforceId, loadData);
      });
    });

    wrap.querySelectorAll('.reject-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const item = allItems.find(i => i.id == btn.dataset.id);
        if (item) handleReject(item, workforceId, loadData);
      });
    });

    wrap.querySelectorAll('.execute-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const item = allItems.find(i => i.id == btn.dataset.id);
        if (item) handleExecute(item, workforceId, loadData);
      });
    });

    wrap.querySelectorAll('.details-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const item = allItems.find(i => i.id == btn.dataset.id);
        if (item) handleDetails(item);
      });
    });
  }

  // ── Data loader ──────────────────────────────────────────────────────────
  async function loadData() {
    try {
      const accountParam = filterAccount ? `?account_id=${filterAccount}` : '';
      const data = await api.get(`/queue${accountParam}`);
      allItems = data ?? [];
      renderTable();
      lastUpdEl.textContent = `Last updated: ${new Date().toLocaleTimeString('en-ZA')}`;
    } catch (err) {
      tableWrap.innerHTML = `<div class="card card-error"><p class="text-error">Failed to load queue: ${escHtml(err.message ?? String(err))}</p></div>`;
    }
  }

  // ── Filter listeners ─────────────────────────────────────────────────────
  selAccount?.addEventListener('change', (e) => {
    filterAccount = e.target.value;
    loadData();
  });

  selStatus?.addEventListener('change', (e) => {
    filterStatus = e.target.value;
    renderTable();
  });

  selAgent?.addEventListener('change', (e) => {
    filterAgent = e.target.value;
    renderTable();
  });

  // ── Initial load ─────────────────────────────────────────────────────────
  await loadData();

  // ── Auto-refresh every 30 s ───────────────────────────────────────────────
  pollTimer = setInterval(() => {
    if (document.hidden) return;
    loadData();
  }, 30_000);

  // Cleanup on navigation away (best-effort via MutationObserver)
  const observer = new MutationObserver(() => {
    if (!document.body.contains(container)) {
      clearInterval(pollTimer);
      observer.disconnect();
    }
  });
  observer.observe(document.body, { childList: true, subtree: true });
}
