# CloudIA Google Ads Agent Workforce — Hierarchy & Communication Diagram

## Overview

The agent workforce operates as a three-level hierarchy. The **Director** sits at the top and coordinates all scheduled work. Below it are three **Divisions**, each specialising in a domain. Within the Optimization Division, two **Sub-agents** run in parallel. The **Creator** is intentionally outside the hierarchy — it is always triggered on-demand by a human via the API.

---

## Hierarchy Diagram

```
╔══════════════════════════════════════════════════════════════════════╗
║                         HUMAN OPERATOR                              ║
║  (approves/rejects/executes items via Dashboard or API)             ║
╚═════════════════════════════╦════════════════════════════════════════╝
                              │ POST /campaigns/create (on-demand)
                              │
                              ▼
╔══════════════════════════════════════════════════════════════════════╗
║                     CREATOR AGENT                                   ║
║  On-demand only. Generates campaign structures from human briefs.   ║
║  → Writes 1 approval_queue item (status=pending)                    ║
║  → Reports directly to human via API response (201 Created)         ║
╚══════════════════════════════════════════════════════════════════════╝

                (separate on-demand path, never scheduled)


╔══════════════════════════════════════════════════════════════════════╗
║                       DIRECTOR AGENT                                ║
║                                                                     ║
║  Scheduled entry point for all automated work.                      ║
║  • Fetches all active accounts                                      ║
║  • Delegates to 3 divisions (sequentially or flag-gated)            ║
║  • Collects DivisionReport from each division                       ║
║  • Calls Claude once to synthesise a holistic executive report      ║
║  • Returns DirectorReport (executive_summary, priority_actions,     ║
║    risk_flags, commendations, next_cycle_focus)                     ║
╚══════╦══════════════════════╦═══════════════════════╦═══════════════╝
       │                      │                       │
       ▼                      ▼                       ▼
╔══════════════╗  ╔═══════════════════════╗  ╔════════════════════╗
║  ANALYSIS    ║  ║    OPTIMIZATION       ║  ║    REPORTING       ║
║  DIVISION    ║  ║    DIVISION           ║  ║    DIVISION        ║
║              ║  ║                       ║  ║                    ║
║ Every 6 hrs  ║  ║ Daily 10:00 SAST      ║  ║ Monday 08:00 SAST  ║
║              ║  ║                       ║  ║ (weekly flag only) ║
║ Per account: ║  ║ Per account:          ║  ║                    ║
║ run Auditor  ║  ║ run Manager +         ║  ║ Per account:       ║
║              ║  ║ KeywordScout          ║  ║ run Reporter       ║
║ ↳ Returns    ║  ║ in PARALLEL threads   ║  ║                    ║
║ DivisionReport  ║                       ║  ║ ↳ Returns          ║
║ (anomalies   ║  ║ ↳ Returns             ║  ║ DivisionReport     ║
║  counts,     ║  ║ DivisionReport        ║  ║ (report sent flag, ║
║  per-account ║  ║ (decisions, tokens,   ║  ║  tokens)           ║
║  summaries)  ║  ║  per-agent summaries) ║  ║                    ║
╚══════╦═══════╝  ╚══════╦══════╦═════════╝  ╚══════════╦═════════╝
       │                 │      │                        │
       ▼                 ▼      ▼                        ▼
╔══════════════╗  ╔════════════╗ ╔═════════════╗  ╔══════════════╗
║   AUDITOR    ║  ║  MANAGER   ║ ║  KEYWORD    ║  ║   REPORTER   ║
║   AGENT      ║  ║  AGENT     ║ ║  SCOUT      ║  ║   AGENT      ║
║              ║  ║            ║ ║  AGENT      ║  ║              ║
║ Anomaly      ║  ║ Bid/budget ║ ║             ║  ║ Weekly perf  ║
║ detection    ║  ║ optimise   ║ ║ Keyword     ║  ║ report       ║
║              ║  ║            ║ ║ discovery   ║  ║              ║
║ Reads:       ║  ║ Reads:     ║ ║             ║  ║ Reads:       ║
║ campaign     ║  ║ campaign   ║ ║ Reads:      ║  ║ campaign     ║
║ snapshots    ║  ║ metrics    ║ ║ search      ║  ║ 7d metrics   ║
║              ║  ║ ad groups  ║ ║ terms +     ║  ║              ║
║ ↓ Claude     ║  ║            ║ ║ keywords    ║  ║ ↓ Claude     ║
║ diagnosis    ║  ║ ↓ Claude   ║ ║             ║  ║ narrative    ║
║              ║  ║ decisions  ║ ║ ↓ Claude    ║  ║              ║
║ Writes:      ║  ║            ║ ║ reco's      ║  ║ Sends:       ║
║ audit_log    ║  ║ Writes:    ║ ║             ║  ║ email report ║
║ agent_runs   ║  ║ approval_  ║ ║ Writes:     ║  ║              ║
║              ║  ║ queue      ║ ║ approval_   ║  ║ Writes:      ║
║              ║  ║ agent_runs ║ ║ queue       ║  ║ agent_runs   ║
╚══════════════╝  ╚════════════╝ ║ agent_runs  ║  ╚══════════════╝
                                 ╚═════════════╝
```

---

## Reporting Flow (bottom-up)

Each level approves/validates before reporting to its superior:

```
Sub-agent (Auditor/Manager/Scout/Reporter)
  │  Produces: AgentRunResult
  │  Writes:   agent_runs row, approval_queue items (where applicable)
  │  QC:       BaseAgent.run() catches exceptions, logs to agent_runs.error
  ▼
Division (Analysis / Optimization / Reporting)
  │  Produces: DivisionReport
  │  Contains: per-account AgentTaskResult list, error list, totals
  │  QC:       Exceptions in one account do not stop other accounts
  ▼
Director
  │  Produces: DirectorReport
  │  Contains: all DivisionReports + Claude synthesis
  │  QC:       Synthesis falls back gracefully on Claude failure
  ▼
Human Operator
     Reviews: DirectorReport executive_summary, priority_actions, risk_flags
     Acts on: approval_queue items via Dashboard (approve → execute)
```

---

## Data Written to Database per Cycle

| Agent | Table | Row type |
|---|---|---|
| Auditor | `audit_log` | One row per anomaly detected |
| Auditor | `agent_runs` | One row per account run |
| Manager | `approval_queue` | One row per valid decision |
| Manager | `agent_runs` | One row per account run |
| KeywordScout | `approval_queue` | One row per keyword recommendation |
| KeywordScout | `agent_runs` | One row per account run |
| Reporter | `agent_runs` | One row per account run |
| Creator | `approval_queue` | One row per campaign structure |

---

## Scheduling

| Trigger | Director call | Divisions run |
|---|---|---|
| Every 6 hours | `director.run_analysis_only()` | Analysis only |
| Daily 10:00 SAST | `director.run_full_cycle()` | Analysis + Optimization |
| Monday 08:00 SAST | `director.run_full_cycle(include_reporting=True)` | All three divisions |
| POST /campaigns/create | (not via Director) | Creator only |

---

## Parallel Execution Detail (Optimization Division)

```
OptimizationDivision.run(accounts)
│
├─ Account A ──────────────────────────────────────────────────────────
│   ├── Thread 1: ManagerAgent.run(A) ──────────────────┐
│   │                                                    │ ThreadPoolExecutor
│   └── Thread 2: KeywordScoutAgent.run(A) ─────────────┘ max_workers=2
│   Both complete → results merged into account A DivisionReport
│
├─ Account B ──────────────────────────────────────────────────────────
│   ├── Thread 1: ManagerAgent.run(B) ──────────────────┐
│   └── Thread 2: KeywordScoutAgent.run(B) ─────────────┘
│
└─ All account results → aggregated DivisionReport → returned to Director
```

> **Note:** Each account's Manager + Scout pair runs in its own thread pool.
> Accounts are processed sequentially to avoid overwhelming the Google Ads API
> with concurrent calls per account.

---

## Human-in-the-Loop Guarantee

Every item written to `approval_queue` starts as `status='pending'`.
No agent can execute against the Google Ads API without:

1. A human calling `POST /queue/{id}/approve` (sets `status='approved'`)
2. A human calling `POST /queue/{id}/execute` (runs the action, sets `status='executed'`)

The Director's role is to coordinate intelligence — never to auto-execute.
