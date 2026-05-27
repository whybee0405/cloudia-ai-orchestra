// No /agent-runs endpoint exists yet — this is an informative placeholder.

export async function renderRuns(container, workforceId) {
  container.innerHTML = `
    <div class="view-runs">
      <div class="card">
        <div class="empty-state empty-state-runs">
          <div class="empty-icon runs-icon">
            <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg"
                 width="56" height="56" aria-hidden="true">
              <!-- Clock face -->
              <circle cx="32" cy="32" r="28" stroke="var(--color-muted, #94a3b8)"
                      stroke-width="3" fill="none"/>
              <!-- Hour hand -->
              <line x1="32" y1="32" x2="32" y2="14"
                    stroke="var(--color-muted, #94a3b8)" stroke-width="3"
                    stroke-linecap="round"/>
              <!-- Minute hand -->
              <line x1="32" y1="32" x2="44" y2="38"
                    stroke="var(--color-muted, #94a3b8)" stroke-width="3"
                    stroke-linecap="round"/>
              <!-- Center dot -->
              <circle cx="32" cy="32" r="2.5"
                      fill="var(--color-muted, #94a3b8)"/>
            </svg>
          </div>

          <h2 class="empty-title">Agent Runs Log &mdash; Coming Soon</h2>

          <p class="empty-subtitle text-muted">
            This view will show every agent execution with detailed metrics and logs.
          </p>

          <ul class="coming-soon-list">
            <li>
              <span class="cs-icon">&#x23F1;</span>
              <span>Start time, duration, and execution status</span>
            </li>
            <li>
              <span class="cs-icon">&#x1F4B0;</span>
              <span>Token usage and estimated cost (USD)</span>
            </li>
            <li>
              <span class="cs-icon">&#x1F4CA;</span>
              <span>Per-account anomaly and decision counts</span>
            </li>
            <li>
              <span class="cs-icon">&#x1F6A8;</span>
              <span>Error logs and stack traces for failed runs</span>
            </li>
          </ul>

          <p class="empty-footnote text-muted">
            Data is already being collected in the <code>agent_runs</code> table.
            The API endpoint and this view will be wired up in a future release.
          </p>
        </div>
      </div>
    </div>`;
}
