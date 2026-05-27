import { api } from '../api.js';
import { toast } from '../components/toast.js';

// ─── Helpers ──────────────────────────────────────────────────────────────────

function escHtml(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function csvToArray(str) {
  return (str ?? '')
    .split(',')
    .map(s => s.trim())
    .filter(Boolean);
}

function setLoading(btn, isLoading) {
  if (isLoading) {
    btn.disabled = true;
    btn.dataset.originalText = btn.textContent;
    btn.innerHTML = `<span class="spinner spinner-inline"></span> Generating&hellip;`;
  } else {
    btn.disabled = false;
    btn.textContent = btn.dataset.originalText ?? 'Generate Campaign Structure →';
  }
}

// ─── Collapsible JSON viewer ─────────────────────────────────────────────────

function buildJsonViewer(obj) {
  let jsonStr;
  try {
    jsonStr = JSON.stringify(obj, null, 2);
  } catch (_) {
    jsonStr = String(obj);
  }

  return `
    <div class="json-collapsible">
      <button class="btn btn-ghost btn-sm json-toggle" aria-expanded="false">
        Show campaign structure &#x25BC;
      </button>
      <pre class="json-viewer json-viewer-hidden">${escHtml(jsonStr)}</pre>
    </div>`;
}

// ─── Result section ──────────────────────────────────────────────────────────

function renderResult(container, result) {
  const queueId = result?.queue_item_id ?? result?.id ?? null;
  const structure = result?.campaign_structure ?? result?.brief ?? result ?? null;

  const queueLink = queueId
    ? `<a href="#queue" class="btn btn-primary btn-sm">View in Approval Queue &rsaquo;</a>`
    : '';

  const resultSection = container.querySelector('#creator-result');
  resultSection.innerHTML = `
    <div class="card card-success creator-result-card">
      <div class="result-header">
        <span class="result-check">&#x2713;</span>
        <div>
          <h3 class="result-title">Campaign structure generated!</h3>
          ${queueId
            ? `<p class="text-muted">Queue item <strong>#${queueId}</strong> is awaiting your review.</p>`
            : `<p class="text-muted">The campaign brief has been submitted and is in the queue.</p>`}
        </div>
      </div>
      <div class="result-actions">
        ${queueLink}
        <button id="creator-another-btn" class="btn btn-ghost btn-sm">Create Another</button>
      </div>
      ${structure ? buildJsonViewer(structure) : ''}
    </div>`;

  resultSection.hidden = false;

  // JSON collapse toggle
  const toggleBtn = resultSection.querySelector('.json-toggle');
  const jsonPre   = resultSection.querySelector('.json-viewer');
  if (toggleBtn && jsonPre) {
    toggleBtn.addEventListener('click', () => {
      const expanded = toggleBtn.getAttribute('aria-expanded') === 'true';
      toggleBtn.setAttribute('aria-expanded', String(!expanded));
      toggleBtn.innerHTML = expanded
        ? `Show campaign structure &#x25BC;`
        : `Hide campaign structure &#x25B2;`;
      jsonPre.classList.toggle('json-viewer-hidden', expanded);
    });
  }

  // "Create Another" resets the form
  const anotherBtn = resultSection.querySelector('#creator-another-btn');
  anotherBtn?.addEventListener('click', () => {
    resultSection.hidden = true;
    resultSection.innerHTML = '';
    const form = container.querySelector('#creator-form');
    if (form) {
      form.reset();
      // Restore language default
      const langInput = form.querySelector('[name="languages"]');
      if (langInput) langInput.value = 'English';
    }
  });
}

// ─── Main render ──────────────────────────────────────────────────────────────

export async function renderCreator(container, workforceId) {
  container.innerHTML = `
    <div class="view-creator">

      <!-- Intro card -->
      <div class="card creator-intro-card">
        <div class="intro-icon">&#x1F916;</div>
        <div>
          <h3 class="creator-intro-title">AI Campaign Creator</h3>
          <p class="text-muted">
            Describe your advertising goal and Claude will design a full Google Ads campaign
            structure — including ad groups, keywords, and budget allocation.
          </p>
          <p class="text-muted">
            <strong>Nothing is created in Google Ads until you review and approve it</strong>
            in the Approval Queue. You remain in full control.
          </p>
        </div>
      </div>

      <!-- Form card -->
      <div class="card">
        <h3 class="card-title">Campaign Brief</h3>
        <form id="creator-form" class="creator-form" novalidate>

          <div class="form-group">
            <label class="form-label required" for="cr-account">Account</label>
            <select id="cr-account" name="account_id" class="select" required>
              <option value="">Loading accounts…</option>
            </select>
            <p class="form-hint">Only active accounts are shown.</p>
          </div>

          <div class="form-group">
            <label class="form-label required" for="cr-goal">Goal</label>
            <input id="cr-goal" name="goal" type="text" class="input" required
              placeholder="e.g. Generate leads for brake pad replacement service" />
          </div>

          <div class="form-group">
            <label class="form-label required" for="cr-product">Product / Service</label>
            <input id="cr-product" name="product_service" type="text" class="input" required
              placeholder="e.g. Automotive brake repair" />
          </div>

          <div class="form-group">
            <label class="form-label required" for="cr-audience">Audience Description</label>
            <textarea id="cr-audience" name="audience_description" class="input textarea"
              rows="3" required
              placeholder="e.g. Vehicle owners aged 25–55 in Johannesburg who need urgent brake repairs"></textarea>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label class="form-label required" for="cr-budget">Daily Budget (ZAR)</label>
              <input id="cr-budget" name="budget_daily_zar" type="number" class="input"
                min="1" step="0.01" required placeholder="e.g. 150" />
            </div>

            <div class="form-group">
              <label class="form-label" for="cr-languages">Languages</label>
              <input id="cr-languages" name="languages" type="text" class="input"
                value="English" placeholder="e.g. English, Afrikaans" />
              <p class="form-hint">Comma-separated</p>
            </div>
          </div>

          <div class="form-group">
            <label class="form-label required" for="cr-geo">Geo Targets</label>
            <input id="cr-geo" name="geo_targets" type="text" class="input" required
              placeholder="e.g. Johannesburg, Sandton, Randburg" />
            <p class="form-hint">Comma-separated city or region names</p>
          </div>

          <div class="form-group">
            <label class="form-label required" for="cr-url">Landing Page URL</label>
            <input id="cr-url" name="landing_page_url" type="url" class="input" required
              placeholder="https://www.example.co.za/brake-repair" />
          </div>

          <div class="form-actions">
            <button type="submit" id="creator-submit-btn" class="btn btn-primary btn-lg">
              Generate Campaign Structure &rarr;
            </button>
          </div>

        </form>
      </div>

      <!-- Result section (hidden until success) -->
      <div id="creator-result" hidden></div>

    </div>`;

  // ── Populate account dropdown (active only) ───────────────────────────────
  const selAccount = container.querySelector('#cr-account');
  try {
    const accounts = await api.get('/accounts');
    const active   = (accounts ?? []).filter(a => a.status === 'active');
    selAccount.innerHTML = `<option value="">— Select an account —</option>`;
    if (active.length === 0) {
      selAccount.innerHTML += `<option value="" disabled>No active accounts</option>`;
    } else {
      active.forEach(acc => {
        const opt = document.createElement('option');
        opt.value = acc.id;
        opt.textContent = acc.client_name ?? acc.name ?? `Account ${acc.id}`;
        selAccount.appendChild(opt);
      });
    }
  } catch (_) {
    selAccount.innerHTML = `<option value="">Failed to load accounts</option>`;
  }

  // ── Form submit ───────────────────────────────────────────────────────────
  const form      = container.querySelector('#creator-form');
  const submitBtn = container.querySelector('#creator-submit-btn');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    // Basic HTML5 validation
    if (!form.checkValidity()) {
      form.reportValidity();
      return;
    }

    const formData = new FormData(form);
    const accountId = formData.get('account_id');
    if (!accountId) {
      toast.error('Please select an account.');
      return;
    }

    const budget = parseFloat(formData.get('budget_daily_zar'));
    if (isNaN(budget) || budget < 1) {
      toast.error('Daily budget must be at least R 1.');
      return;
    }

    const payload = {
      account_id: Number(accountId),
      brief: {
        goal:                   formData.get('goal').trim(),
        product_service:        formData.get('product_service').trim(),
        audience_description:   formData.get('audience_description').trim(),
        budget_daily_zar:       budget,
        geo_targets:            csvToArray(formData.get('geo_targets')),
        languages:              csvToArray(formData.get('languages')),
        landing_page_url:       formData.get('landing_page_url').trim(),
      },
    };

    // Validate arrays non-empty
    if (payload.brief.geo_targets.length === 0) {
      toast.error('Please enter at least one geo target.');
      return;
    }
    if (payload.brief.languages.length === 0) {
      payload.brief.languages = ['English'];
    }

    setLoading(submitBtn, true);
    try {
      const result = await api.post('/campaigns/create', payload);
      toast.success('Campaign structure generated and added to the queue.');
      renderResult(container, result);
    } catch (err) {
      toast.error(`Campaign creation failed: ${err.message ?? String(err)}`);
    } finally {
      setLoading(submitBtn, false);
    }
  });
}
