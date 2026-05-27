/**
 * Toast notification system.
 *
 * Usage:
 *   toast.success('Action completed!')
 *   toast.error('Something went wrong.')
 *   toast.info('Processing in background...')
 */

const ICONS = {
  success: `<svg class="toast-icon" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M13.5 4.5L6 12 2.5 8.5"/>
  </svg>`,
  error: `<svg class="toast-icon" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="8" cy="8" r="6.5"/>
    <line x1="8" y1="5" x2="8" y2="8.5"/>
    <circle cx="8" cy="11" r="0.6" fill="currentColor" stroke="none"/>
  </svg>`,
  info: `<svg class="toast-icon" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="8" cy="8" r="6.5"/>
    <line x1="8" y1="7.5" x2="8" y2="11"/>
    <circle cx="8" cy="5.5" r="0.6" fill="currentColor" stroke="none"/>
  </svg>`,
};

const DURATION_MS = 3500;
const FADE_MS = 280;

function _show(msg, type) {
  const container = document.getElementById('toast-container');
  if (!container) {
    console.warn('Toast container #toast-container not found in DOM.');
    return;
  }

  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  el.setAttribute('role', 'alert');
  el.innerHTML = `${ICONS[type] || ''}<span>${_escape(msg)}</span>`;

  container.appendChild(el);

  // Trigger slide-in on next frame
  requestAnimationFrame(() => {
    requestAnimationFrame(() => el.classList.add('toast-visible'));
  });

  // Auto-dismiss
  const dismissTimer = setTimeout(() => dismiss(el), DURATION_MS);

  // Click to dismiss early
  el.addEventListener('click', () => {
    clearTimeout(dismissTimer);
    dismiss(el);
  });
}

function dismiss(el) {
  el.classList.remove('toast-visible');
  setTimeout(() => {
    if (el.parentNode) el.parentNode.removeChild(el);
  }, FADE_MS);
}

function _escape(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

export const toast = {
  success: (msg) => _show(msg, 'success'),
  error:   (msg) => _show(msg, 'error'),
  info:    (msg) => _show(msg, 'info'),
};
