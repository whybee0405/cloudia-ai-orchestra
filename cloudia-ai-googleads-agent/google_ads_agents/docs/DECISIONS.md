# Architectural Decisions Log

Decisions made during design and build. Updated when deviations from the spec occur.

---

## 2026-05-24 — Initial build

### ADR-001: Single process, no message queue

**Decision:** Run all agents inside one Python process via APScheduler. FastAPI runs in a daemon thread in the same process.

**Why:** Infrastructure cost target is R200–400/month for 15 clients. A message queue (Redis, RabbitMQ) + separate worker processes would double the infrastructure cost and complexity. APScheduler's BlockingScheduler is sufficient for the load: 5 agents × 15 clients = 75 agent runs in the busiest 6-hour window. At typical runtimes of 10–30 seconds per account, this is well within a single process.

**Trade-off:** If the process crashes, scheduled jobs are lost until restart. Mitigation: `agent_runs` table tracks every run. A simple systemd unit with `Restart=always` is sufficient.

---

### ADR-002: Agents never call Google Ads API or Anthropic directly

**Decision:** All Google Ads calls go through `google_ads/client.py`. All Claude calls go through `ai/claude.py`.

**Why:** Centralises authentication, logging, error handling, and retry logic. Makes agents unit-testable by mocking two interfaces instead of the full SDK.

---

### ADR-003: Calibration period skips agents entirely

**Decision:** Accounts with `baseline_set_at = None` or `baseline_set_at < 30 days ago` are skipped by all agents (status='skipped' in agent_runs). Auditor still saves snapshots.

**Why:** Claude needs baseline data to generate contextual recommendations. Without a baseline, anomaly detection would generate false positives (anything looks anomalous without a reference point) and manager decisions would be generic rather than client-specific.

---

### ADR-004: Approval queue is the only write gate

**Decision:** No agent writes to Google Ads directly. All recommendations go to `approval_queue` with `status='pending'`. Execution only happens via `POST /queue/{id}/execute` after a human sets `status='approved'`.

**Why:** This is the core product principle: agents observe and recommend, humans approve. Protects clients from AI errors on live ad spend.

---

### ADR-005: Costs stored in micros, displayed in ZAR

**Decision:** All cost and bid values are stored in Google Ads micros (1 ZAR = 1,000,000 micros) in the database. They are converted to ZAR immediately before being sent to Claude, and displayed in ZAR in the API and emails.

**Why:** Micros are the native unit of the Google Ads API. Storing in micros avoids precision loss from floating-point ZAR arithmetic. Conversion is a single divide-by-1,000,000 operation.

---

### ADR-006: campaign_builder.py creates campaigns in PAUSED state

**Decision:** The Creator agent's approved campaigns are always created with `status=PAUSED` in Google Ads, regardless of the brief.

**Why:** A newly created campaign should never start spending automatically. The account manager must review it in Google Ads and manually enable it. This is a safety default.

---

### ADR-007: Claude JSON responses sanitised before parsing

**Decision:** `ClaudeClient.complete_json()` strips markdown code fences before calling `json.loads()`.

**Why:** Claude occasionally wraps JSON in `` ```json ``` `` fences despite prompt instructions. Stripping them prevents fragile failures in production.

---

### ADR-008: Per-account exception isolation in orchestrator

**Decision:** `orchestrator.py` catches and logs exceptions per account without stopping the loop.

**Why:** A bad API response or DB error for one client must not prevent the remaining 14 clients from being processed. Each failure is logged to `agent_runs` with `status='failed'`.
