import { WORKFORCES, GLOBAL_NAV, API_BASE } from '../config.js';

/**
 * Module-level badge store: { [workforceId]: number }
 * Tracks pending queue item counts per workforce.
 */
const _pendingCounts = {};

/**
 * Update the pending badge count for a workforce and re-render the badge in the DOM.
 * Call this after approving / rejecting queue items, or after initial load.
 * @param {string} workforceId
 * @param {number} count
 */
export function updateQueueBadge(workforceId, count) {
  _pendingCounts[workforceId] = count;
  // Live-update the badge without a full re-render
  const badge = document.querySelector(`[data-badge-workforce="${workforceId}"]`);
  if (badge) {
    if (count > 0) {
      badge.textContent = count > 99 ? '99+' : String(count);
      badge.hidden = false;
    } else {
      badge.hidden = true;
    }
  }
}

/**
 * Render the full sidebar and attach click handlers.
 * Call after every route change.
 * @param {string} activeRoute — current hash route, e.g. "/google-ads/queue"
 */
export function renderSidebar(activeRoute) {
  const el = document.getElementById('sidebar');
  if (!el) return;
  el.innerHTML = _buildSidebarHTML(activeRoute);
  _attachHandlers(el);
  // Kick off API health check
  _checkApiStatus();
}

/* ------------------------------------------------------------------ */
/*  Build HTML                                                          */
/* ------------------------------------------------------------------ */

function _buildSidebarHTML(activeRoute) {
  const globalItems = GLOBAL_NAV.map((item) =>
    _navItemHTML(`/${item.id}`, item.label, _icon(item.icon), activeRoute)
  ).join('');

  const workforcesSections = WORKFORCES.map((wf) =>
    _workforceSectionHTML(wf, activeRoute)
  ).join('');

  return `
    ${_brandHTML()}
    <nav class="sidebar-nav" role="navigation" aria-label="Main navigation">
      <div class="sidebar-section">
        ${globalItems}
      </div>
      ${workforcesSections}
    </nav>
    ${_footerHTML()}
  `;
}

function _brandHTML() {
  return `
    <div class="sidebar-brand" onclick="window.navigate('/dashboard')" role="link" tabindex="0" aria-label="CloudIA Agent Control — go to dashboard">
      <div class="sidebar-logo">
        ${_icon('logo')}
      </div>
      <div class="sidebar-brand-text">
        <span class="sidebar-brand-name">CloudIA</span>
        <span class="sidebar-brand-sub">Agent Control</span>
      </div>
    </div>
  `;
}

function _workforceSectionHTML(wf, activeRoute) {
  if (wf.disabled) {
    return `
      <div class="sidebar-section">
        <div class="sidebar-divider"></div>
        <div class="sidebar-section-label">
          <span class="sidebar-section-dot" style="background:${wf.color || '#94a3b8'};opacity:0.5;"></span>
          <span>${_escapeHtml(wf.name)}</span>
        </div>
        <div class="sidebar-nav-item disabled" aria-disabled="true">
          <span class="sidebar-nav-icon">${_icon('workforce')}</span>
          <span class="sidebar-nav-label">${_escapeHtml(wf.name)}</span>
          <span class="sidebar-coming-soon">Soon</span>
        </div>
      </div>
    `;
  }

  const navItems = (wf.nav || []).map((item) => {
    const route = `/${wf.id}/${item.id}`;
    const active = activeRoute === route || activeRoute.startsWith(route);

    let badge = '';
    if (item.id === 'queue') {
      const count = _pendingCounts[wf.id] || 0;
      const countStr = count > 99 ? '99+' : String(count);
      badge = `<span class="sidebar-nav-badge" data-badge-workforce="${_escapeHtml(wf.id)}" ${count === 0 ? 'hidden' : ''}>${countStr}</span>`;
    }

    return `
      <button
        class="sidebar-nav-item${active ? ' active' : ''}"
        data-route="${route}"
        aria-current="${active ? 'page' : 'false'}"
        title="${_escapeHtml(item.label)}"
      >
        <span class="sidebar-nav-icon">${_icon(item.icon)}</span>
        <span class="sidebar-nav-label">${_escapeHtml(item.label)}</span>
        ${badge}
      </button>
    `;
  }).join('');

  return `
    <div class="sidebar-section">
      <div class="sidebar-divider"></div>
      <div class="sidebar-section-label">
        <span class="sidebar-section-dot" style="background:${wf.color || '#94a3b8'};"></span>
        <span>${_escapeHtml(wf.name)}</span>
      </div>
      ${navItems}
    </div>
  `;
}

function _navItemHTML(route, label, iconSvg, activeRoute) {
  const active = activeRoute === route || (route !== '/' && activeRoute.startsWith(route + '/'));
  return `
    <button
      class="sidebar-nav-item${active ? ' active' : ''}"
      data-route="${route}"
      aria-current="${active ? 'page' : 'false'}"
      title="${_escapeHtml(label)}"
    >
      <span class="sidebar-nav-icon">${iconSvg}</span>
      <span class="sidebar-nav-label">${_escapeHtml(label)}</span>
    </button>
  `;
}

function _footerHTML() {
  return `
    <div class="sidebar-footer">
      <div class="api-status" id="api-status-indicator">
        <span class="api-status-dot checking" id="api-status-dot"></span>
        <span class="api-status-text" id="api-status-text">Checking API...</span>
      </div>
    </div>
  `;
}

/* ------------------------------------------------------------------ */
/*  Event Handlers                                                      */
/* ------------------------------------------------------------------ */

function _attachHandlers(el) {
  el.querySelectorAll('[data-route]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const route = btn.getAttribute('data-route');
      if (route) window.navigate(route);
    });
    btn.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        const route = btn.getAttribute('data-route');
        if (route) window.navigate(route);
      }
    });
  });

  // Brand click already uses onclick; add keyboard support
  const brand = el.querySelector('.sidebar-brand');
  if (brand) {
    brand.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        window.navigate('/dashboard');
      }
    });
  }
}

/* ------------------------------------------------------------------ */
/*  API Health Check                                                    */
/* ------------------------------------------------------------------ */

async function _checkApiStatus() {
  const dot  = document.getElementById('api-status-dot');
  const text = document.getElementById('api-status-text');
  if (!dot || !text) return;

  try {
    const res = await fetch(`${API_BASE}/health`, { method: 'GET', signal: AbortSignal.timeout(4000) });
    if (res.ok) {
      dot.className  = 'api-status-dot connected';
      text.textContent = 'API connected';
    } else {
      dot.className  = 'api-status-dot offline';
      text.textContent = `API error ${res.status}`;
    }
  } catch {
    dot.className  = 'api-status-dot offline';
    text.textContent = 'API offline';
  }
}

/* ------------------------------------------------------------------ */
/*  SVG Icon Library                                                    */
/* ------------------------------------------------------------------ */

function _icon(name) {
  const icons = {
    logo: `<svg viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
      <rect x="2" y="2" width="6" height="6" rx="1.5"/>
      <rect x="10" y="2" width="6" height="6" rx="1.5"/>
      <rect x="2" y="10" width="6" height="6" rx="1.5"/>
      <path d="M13 10v6M10 13h6"/>
    </svg>`,

    dashboard: `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
      <rect x="1.5" y="1.5" width="5" height="5" rx="1"/>
      <rect x="9.5" y="1.5" width="5" height="5" rx="1"/>
      <rect x="1.5" y="9.5" width="5" height="5" rx="1"/>
      <rect x="9.5" y="9.5" width="5" height="5" rx="1"/>
    </svg>`,

    accounts: `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
      <circle cx="8" cy="5" r="3"/>
      <path d="M2 14c0-3.31 2.69-6 6-6s6 2.69 6 6"/>
    </svg>`,

    queue: `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
      <rect x="2" y="2.5" width="12" height="3" rx="1"/>
      <rect x="2" y="6.5" width="12" height="3" rx="1"/>
      <rect x="2" y="10.5" width="7" height="3" rx="1"/>
      <path d="M11.5 11l1.5 1.5L15 10"/>
    </svg>`,

    audit: `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
      <path d="M10 1.5H4a1 1 0 00-1 1v11a1 1 0 001 1h8a1 1 0 001-1V5l-3-3.5z"/>
      <path d="M10 1.5V5h3"/>
      <line x1="5" y1="8" x2="11" y2="8"/>
      <line x1="5" y1="10.5" x2="9" y2="10.5"/>
    </svg>`,

    runs: `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
      <circle cx="8" cy="8" r="6.5"/>
      <polygon points="6.5,5.5 11,8 6.5,10.5" fill="currentColor" stroke="none"/>
    </svg>`,

    creator: `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
      <rect x="1.5" y="1.5" width="13" height="13" rx="2"/>
      <line x1="8" y1="4.5" x2="8" y2="11.5"/>
      <line x1="4.5" y1="8" x2="11.5" y2="8"/>
    </svg>`,

    workforce: `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
      <circle cx="5" cy="5" r="2.5"/>
      <circle cx="11" cy="5" r="2.5"/>
      <path d="M1 14c0-2.21 1.79-4 4-4s4 1.79 4 4"/>
      <path d="M9 14c0-2.21 1.79-4 4-4"/>
    </svg>`,
  };

  return icons[name] || icons.dashboard;
}

function _escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
