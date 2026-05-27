/**
 * Modal component.
 *
 * Three modes:
 *   modal.confirm(title, bodyHtml, onConfirm)            — confirmation dialog
 *   modal.form(title, fields, onSubmit)                  — data-entry form
 *   modal.show(title, htmlContent, { size? })            — read-only display
 *   modal.close()                                        — close programmatically
 *
 * form() fields schema:
 *   [{ name, label, type='text', required=false, placeholder='', options=[], value='', hint='' }]
 *   Supported types: text, email, number, select, textarea, checkbox
 */

const overlay   = () => document.getElementById('modal-overlay');
const box       = () => document.getElementById('modal-box');
const titleEl   = () => document.getElementById('modal-title');
const bodyEl    = () => document.getElementById('modal-body');
const footerEl  = () => document.getElementById('modal-footer');
const closeBtn  = () => document.getElementById('modal-close');

let _onEscClose = null;

function _open() {
  const el = overlay();
  el.hidden = false;

  // Trap focus inside modal
  const firstFocusable = el.querySelector('button, input, select, textarea, [tabindex]:not([tabindex="-1"])');
  if (firstFocusable) firstFocusable.focus();

  // Close on overlay click (outside box)
  el.addEventListener('mousedown', _overlayClickHandler);

  // Close on Escape
  _onEscClose = (e) => { if (e.key === 'Escape') close(); };
  document.addEventListener('keydown', _onEscClose);
}

function _overlayClickHandler(e) {
  if (e.target === overlay()) close();
}

function close() {
  const el = overlay();
  el.hidden = true;
  el.removeEventListener('mousedown', _overlayClickHandler);
  if (_onEscClose) {
    document.removeEventListener('keydown', _onEscClose);
    _onEscClose = null;
  }
  // Remove size modifier
  box().classList.remove('modal-lg');
}

/**
 * Confirmation dialog — Yes / Cancel
 * @param {string}   title
 * @param {string}   bodyHtml  - HTML string shown in modal body
 * @param {Function} onConfirm - called when user clicks Confirm
 * @param {object}   [opts]    - { confirmLabel, confirmClass, size }
 */
function confirm(title, bodyHtml, onConfirm, opts = {}) {
  const {
    confirmLabel = 'Confirm',
    confirmClass = 'btn-danger',
    size,
  } = opts;

  _setTitle(title);
  bodyEl().innerHTML = bodyHtml;
  if (size === 'lg') box().classList.add('modal-lg');

  footerEl().innerHTML = `
    <button class="btn btn-ghost" id="modal-cancel-btn">Cancel</button>
    <button class="btn ${confirmClass}" id="modal-confirm-btn">${_escape(confirmLabel)}</button>
  `;

  document.getElementById('modal-cancel-btn').addEventListener('click', close);
  document.getElementById('modal-confirm-btn').addEventListener('click', () => {
    close();
    onConfirm();
  });
  closeBtn().addEventListener('click', close, { once: true });

  _open();
}

/**
 * Form dialog
 * @param {string}   title
 * @param {Array}    fields - see schema above
 * @param {Function} onSubmit - called with plain object { fieldName: value }
 * @param {object}   [opts]   - { submitLabel, size }
 */
function form(title, fields, onSubmit, opts = {}) {
  const {
    submitLabel = 'Submit',
    size,
  } = opts;

  _setTitle(title);
  if (size === 'lg') box().classList.add('modal-lg');

  bodyEl().innerHTML = _buildFormHTML(fields);

  footerEl().innerHTML = `
    <button class="btn btn-ghost" id="modal-cancel-btn">Cancel</button>
    <button class="btn btn-primary" id="modal-submit-btn">${_escape(submitLabel)}</button>
  `;

  document.getElementById('modal-cancel-btn').addEventListener('click', close);
  closeBtn().addEventListener('click', close, { once: true });

  document.getElementById('modal-submit-btn').addEventListener('click', () => {
    const formEl = bodyEl().querySelector('form');
    if (!formEl.reportValidity()) return;

    const data = {};
    fields.forEach((field) => {
      const el = formEl.elements[field.name];
      if (!el) return;
      if (field.type === 'checkbox') {
        data[field.name] = el.checked;
      } else {
        data[field.name] = el.value;
      }
    });

    close();
    onSubmit(data);
  });

  // Support submit via Enter in single-line inputs
  const formEl = bodyEl().querySelector('form');
  formEl.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && e.target.tagName !== 'TEXTAREA') {
      e.preventDefault();
      document.getElementById('modal-submit-btn')?.click();
    }
  });

  _open();
}

/**
 * Read-only display modal
 * @param {string} title
 * @param {string} htmlContent
 * @param {object} [opts] - { size }
 */
function show(title, htmlContent, opts = {}) {
  const { size } = opts;

  _setTitle(title);
  if (size === 'lg') box().classList.add('modal-lg');

  bodyEl().innerHTML = htmlContent;
  footerEl().innerHTML = `<button class="btn btn-ghost" id="modal-close-ok">Close</button>`;

  document.getElementById('modal-close-ok').addEventListener('click', close);
  closeBtn().addEventListener('click', close, { once: true });

  _open();
}

/* ---- Internal helpers ---- */

function _setTitle(title) {
  titleEl().textContent = title;
}

function _buildFormHTML(fields) {
  const rows = fields.map((f) => {
    const type      = f.type || 'text';
    const required  = f.required ? 'required' : '';
    const reqMark   = f.required ? '<span class="required">*</span>' : '';
    const ph        = f.placeholder ? `placeholder="${_escape(f.placeholder)}"` : '';
    const val       = f.value ? `value="${_escape(String(f.value))}"` : '';
    const hint      = f.hint ? `<span class="form-hint">${_escape(f.hint)}</span>` : '';

    let input;

    if (type === 'select') {
      const optionsHtml = (f.options || []).map((o) => {
        const oVal   = typeof o === 'object' ? o.value : o;
        const oLabel = typeof o === 'object' ? o.label : o;
        const sel    = String(f.value) === String(oVal) ? 'selected' : '';
        return `<option value="${_escape(String(oVal))}" ${sel}>${_escape(oLabel)}</option>`;
      }).join('');
      input = `<select name="${_escape(f.name)}" class="form-control" ${required}>${optionsHtml}</select>`;

    } else if (type === 'textarea') {
      input = `<textarea name="${_escape(f.name)}" class="form-control" ${ph} ${required}>${_escape(f.value || '')}</textarea>`;

    } else if (type === 'checkbox') {
      const checked = f.value ? 'checked' : '';
      return `
        <div class="form-group" style="flex-direction:row;align-items:center;gap:8px;">
          <input type="checkbox" name="${_escape(f.name)}" id="field_${_escape(f.name)}" ${checked} style="width:16px;height:16px;cursor:pointer;" />
          <label for="field_${_escape(f.name)}" style="margin:0;cursor:pointer;">${_escape(f.label)}</label>
          ${hint}
        </div>`;

    } else {
      input = `<input type="${_escape(type)}" name="${_escape(f.name)}" class="form-control" ${ph} ${val} ${required} />`;
    }

    return `
      <div class="form-group">
        <label for="field_${_escape(f.name)}">${_escape(f.label)}${reqMark}</label>
        ${input.replace('<input ', `<input id="field_${_escape(f.name)}" `).replace('<select ', `<select id="field_${_escape(f.name)}" `).replace('<textarea ', `<textarea id="field_${_escape(f.name)}" `)}
        ${hint}
      </div>`;
  });

  return `<form id="modal-form" novalidate>${rows.join('')}</form>`;
}

function _escape(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

export const modal = { confirm, form, show, close };
