/**
 * CloudIA Agent Control — Main entry point
 *
 * Handles hash-based routing, topbar updates, and app initialisation.
 * Route format:
 *   #/dashboard
 *   #/accounts
 *   #/{workforceId}/queue
 *   #/{workforceId}/audit
 *   #/{workforceId}/runs
 *   #/{workforceId}/creator
 */

import { renderSidebar } from './components/sidebar.js';
import { WORKFORCES, GLOBAL_NAV } from './config.js';

// Lazy-import view renderers — grouped here for easy discoverability
import { renderDashboard } from './views/dashboard.js';
import { renderQueue }     from './views/queue.js';
import { renderAudit }     from './views/audit.js';
import { renderAccounts }  from './views/accounts.js';
import { renderRuns }      from './views/runs.js';
import { renderCreator }   from './views/creator.js';

// ─── Navigation helper (global so templates can call window.navigate) ─────────

window.navigate = function navigate(route) {
  // Normalise — ensure leading slash
  if (!route.startsWith('/')) route = '/' + route;
  location.hash = route;
};

// ─── Route metadata ───────────────────────────────────────────────────────────

const GLOBAL_ROUTE_META = {
  dashboard: { title: 'Dashboard',  subtitle: 'System overview and agent status' },
  accounts:  { title: 'Accounts',   subtitle: 'Manage client Google Ads accounts' },
};

const WF_VIEW_META = {
  queue:   { title: 'Approval Queue',  subtitle: 'Review and approve agent recommendations' },
  audit:   { title: 'Audit Log',       subtitle: 'Anomalies detected by the auditor agent' },
  runs:    { title: 'Agent Runs',      subtitle: 'Execution history and performance metrics' },
  creator: { title: 'Campaign Creator', subtitle: 'AI-powered Google Ads campaign generation' },
};

// ─── Router ───────────────────────────────────────────────────────────────────

async function route() {
  // Parse hash: strip leading '#' then leading '/'
  const raw   = location.hash.replace(/^#/, '') || '/dashboard';
  const clean = raw.startsWith('/') ? raw.slice(1) : raw;
  const parts = clean.split('/').filter(Boolean);

  const content = document.getElementById('content');
  content.innerHTML = ''; // Clear current view

  // Re-render sidebar with new active route
  renderSidebar('/' + clean);

  // ── Route matching ──────────────────────────────────────────────────────────

  if (parts.length === 0 || parts[0] === 'dashboard') {
    _setTopbar('Dashboard', GLOBAL_ROUTE_META.dashboard.subtitle, [
      { label: 'Dashboard', route: null },
    ]);
    await renderDashboard(content);
    return;
  }

  if (parts.length === 1) {
    switch (parts[0]) {
      case 'accounts':
        _setTopbar('Accounts', GLOBAL_ROUTE_META.accounts.subtitle, [
          { label: 'Dashboard', route: '/dashboard' },
          { label: 'Accounts', route: null },
        ]);
        await renderAccounts(content);
        return;

      default:
        _renderNotFound(content, '/' + clean);
        return;
    }
  }

  if (parts.length === 2) {
    const [wfId, view] = parts;

    const wf = WORKFORCES.find(w => w.id === wfId);
    if (!wf) {
      _renderNotFound(content, '/' + clean);
      return;
    }

    if (wf.disabled) {
      _renderDisabled(content, wf);
      return;
    }

    const meta = WF_VIEW_META[view];
    if (!meta) {
      _renderNotFound(content, '/' + clean);
      return;
    }

    _setTopbar(meta.title, meta.subtitle, [
      { label: 'Dashboard', route: '/dashboard' },
      { label: wf.name, route: `/${wfId}/queue` },
      { label: meta.title, route: null },
    ]);

    switch (view) {
      case 'queue':   await renderQueue(content, wfId);   break;
      case 'audit':   await renderAudit(content, wfId);   break;
      case 'runs':    await renderRuns(content, wfId);     break;
      case 'creator': await renderCreator(content, wfId); break;
      default:        _renderNotFound(content, '/' + clean);
    }
    return;
  }

  _renderNotFound(content, '/' + clean);
}

// ─── Topbar ───────────────────────────────────────────────────────────────────

/**
 * @param {string}  title
 * @param {string}  subtitle
 * @param {Array<{ label: string, route: string|null }>} crumbs
 */
function _setTopbar(title, subtitle, crumbs = []) {
  const titleEl    = document.getElementById('page-title');
  const subtitleEl = document.getElementById('page-subtitle');
  const bcEl       = document.getElementById('breadcrumb');

  if (titleEl)    titleEl.textContent    = title;
  if (subtitleEl) subtitleEl.textContent = subtitle;

  if (bcEl) {
    bcEl.innerHTML = crumbs.map((crumb, i) => {
      const isLast = i === crumbs.length - 1;
      const sep    = i > 0 ? '<span class="bc-sep" aria-hidden="true">›</span>' : '';
      const item   = isLast || !crumb.route
        ? `<span class="bc-current">${_esc(crumb.label)}</span>`
        : `<a href="#${crumb.route}">${_esc(crumb.label)}</a>`;
      return `<span class="bc-item">${sep}${item}</span>`;
    }).join('');
  }
}

// ─── Error / fallback views ───────────────────────────────────────────────────

function _renderNotFound(container, path) {
  _setTopbar('Not Found', '', [{ label: 'Dashboard', route: '/dashboard' }, { label: '404', route: null }]);
  container.innerHTML = `
    <div class="empty-state">
      <svg class="empty-state-icon" viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="24" cy="24" r="20"/>
        <line x1="24" y1="14" x2="24" y2="26"/>
        <circle cx="24" cy="32" r="1.2" fill="currentColor" stroke="none"/>
      </svg>
      <h3>Page not found</h3>
      <p>The route <code>${_esc(path)}</code> does not exist.</p>
      <button class="btn btn-primary mt-4" onclick="window.navigate('/dashboard')">Go to Dashboard</button>
    </div>`;
}

function _renderDisabled(container, wf) {
  _setTopbar(wf.name, 'Coming soon', [
    { label: 'Dashboard', route: '/dashboard' },
    { label: wf.name, route: null },
  ]);
  container.innerHTML = `
    <div class="empty-state">
      <svg class="empty-state-icon" viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="24" cy="24" r="20"/>
        <path d="M16 24h16"/>
      </svg>
      <h3>${_esc(wf.name)} — Coming Soon</h3>
      <p>${_esc(wf.description || 'This workforce is not yet available.')}</p>
      <button class="btn btn-ghost mt-4" onclick="window.navigate('/dashboard')">Back to Dashboard</button>
    </div>`;
}

// ─── Utility ──────────────────────────────────────────────────────────────────

function _esc(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ─── Bootstrap ────────────────────────────────────────────────────────────────

window.addEventListener('hashchange', route);

window.addEventListener('DOMContentLoaded', () => {
  // Default route
  if (!location.hash || location.hash === '#') {
    location.hash = '/dashboard';
  } else {
    // Trigger routing for current hash on load
    route();
  }
});
