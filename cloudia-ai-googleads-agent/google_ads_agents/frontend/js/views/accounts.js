import { api } from '../api.js';
import { toast } from '../components/toast.js';
import { modal } from '../components/modal.js';

// ─── Helpers ──────────────────────────────────────────────────────────────────

function fmtDate(v) {
  if (!v) return '—';
  return new Date(v).toLocaleString('en-ZA');
}

function fmtZAR(v) {
  if (v == null || v === '') return '—';
  const n = Number(v);
  if (isNaN(n)) return '—';
  return `R ${n.toLocaleString('en-ZA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function statusBadge(status) {
  const map = {
    calibrating: 'badge-yellow',
    active:      'badge-green',
    paused:      'badge-gray',
    churned:     'badge-red',
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

// ─── Details modal ───────────────────────────────────────────────────────────

function showAccountDetails(account) {
  let jsonStr;
  try {
    jsonStr = JSON.stringify(account, null, 2);
  } catch (_) {
    jsonStr = String(account);
  }
  modal.show(
    `Account — ${escHtml(account.client_name ?? account.name ?? `#${account.id}`)}`,
    `<pre class="json-viewer">${escHtml(jsonStr)}</pre>`
  );
}

// ─── Set Baseline modal ───────────────────────────────────────────────────────

function openSetBaseline(account) {
  modal.form(
    `Set Baseline — ${escHtml(account.client_name ?? account.name ?? `#${account.id}`)}`,
    [
      {
        name: 'ctr',
        label: 'CTR (Click-Through Rate)',
        type: 'number',
        required: true,
        placeholder: 'e.g. 0.05 (5%)',
      },
      {
        name: 'cvr',
        label: 'CVR (Conversion Rate)',
        type: 'number',
        required: true,
        placeholder: 'e.g. 0.02 (2%)',
      },
      {
        name: 'cpc',
        label: 'CPC — Cost per Click (ZAR)',
        type: 'number',
        required: true,
        placeholder: 'e.g. 12.50',
      },
      {
        name: 'cpa',
        label: 'CPA — Cost per Acquisition (ZAR)',
        type: 'number',
        required: true,
        placeholder: 'e.g. 250.00',
      },
      {
        name: 'roas',
        label: 'ROAS (Return on Ad Spend)',
        type: 'number',
        required: true,
        placeholder: 'e.g. 3.5',
      },
    ],
    async (data) => {
      try {
        const payload = {
          ctr:  parseFloat(data.ctr),
          cvr:  parseFloat(data.cvr),
          cpc:  parseFloat(data.cpc),
          cpa:  parseFloat(data.cpa),
          roas: parseFloat(data.roas),
        };

        // Validate
        for (const [k, v] of Object.entries(payload)) {
          if (isNaN(v)) {
            toast.error(`Invalid value for ${k.toUpperCase()}.`);
            return;
          }
        }

        await api.post(`/accounts/${account.id}/baseline`, payload);
        toast.success(`Baseline updated for ${account.client_name ?? `Account #${account.id}`}.`);
      } catch (err) {
        toast.error(`Failed to set baseline: ${err.message ?? String(err)}`);
      }
    }
  );
}

// ─── Table builder ────────────────────────────────────────────────────────────

function buildTable(accounts) {
  if (accounts.length === 0) {
    return `
      <div class="empty-state">
        <div class="empty-icon">&#x1F4C2;</div>
        <p class="empty-title">No accounts found</p>
        <p class="text-muted">No client accounts have been set up yet.</p>
      </div>`;
  }

  const rows = accounts.map(acc => {
    const primaryKpi = acc.primary_kpi
      ? `${escHtml(acc.primary_kpi)}${acc.kpi_target != null ? ` / ${escHtml(String(acc.kpi_target))}` : ''}`
      : '—';

    const monthlySpend = acc.monthly_spend_zar != null
      ? fmtZAR(acc.monthly_spend_zar)
      : '—';

    return `
      <tr>
        <td><strong>${escHtml(acc.client_name ?? acc.name ?? '—')}</strong></td>
        <td class="text-mono">${escHtml(String(acc.customer_id ?? '—'))}</td>
        <td>${statusBadge(acc.status)}</td>
        <td>${escHtml(acc.industry ?? '—')}</td>
        <td>${primaryKpi}</td>
        <td>${monthlySpend}</td>
        <td>${fmtDate(acc.onboarded_at ?? acc.created_at)}</td>
        <td class="actions-cell">
          <button class="btn btn-sm btn-ghost details-btn" data-id="${acc.id}">Details</button>
          <button class="btn btn-sm btn-primary baseline-btn" data-id="${acc.id}">Set Baseline</button>
        </td>
      </tr>`;
  }).join('');

  return `
    <div class="table-scroll">
      <table class="table table-hoverable">
        <thead>
          <tr>
            <th>Client Name</th>
            <th>Customer ID</th>
            <th>Status</th>
            <th>Industry</th>
            <th>Primary KPI / Target</th>
            <th>Monthly Spend (ZAR)</th>
            <th>Onboarded At</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
}

// ─── Main render ──────────────────────────────────────────────────────────────

export async function renderAccounts(container) {
  container.innerHTML = `
    <div class="view-accounts">
      <div class="card">
        <div id="accounts-table-wrap">${spinner()}</div>
      </div>
    </div>`;

  const tableWrap = container.querySelector('#accounts-table-wrap');

  let accounts = [];
  try {
    accounts = await api.get('/accounts');
    accounts = accounts ?? [];
  } catch (err) {
    tableWrap.innerHTML = `<div class="card-error"><p class="text-error">Failed to load accounts: ${escHtml(err.message ?? String(err))}</p></div>`;
    return;
  }

  tableWrap.innerHTML = buildTable(accounts);

  // Wire up action buttons
  tableWrap.querySelectorAll('.details-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const acc = accounts.find(a => String(a.id) === btn.dataset.id);
      if (acc) showAccountDetails(acc);
    });
  });

  tableWrap.querySelectorAll('.baseline-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const acc = accounts.find(a => String(a.id) === btn.dataset.id);
      if (acc) openSetBaseline(acc);
    });
  });
}
