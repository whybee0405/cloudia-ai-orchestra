"""Auditor agent — anomaly detection every 6 hours."""

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

import config
from agents.base import AgentRunResult, BaseAgent
from ai.claude import ClaudeClient
from ai.context_builder import build_client_context
from ai.prompts.auditor import AUDITOR_SYSTEM_PROMPT
from db.models import Account, AuditLog, IndustryBenchmark
from db.snapshots import get_previous_snapshot, parse_gaql_row, save_snapshot
from google_ads.client import AdsClient
from google_ads.queries import CAMPAIGN_PERFORMANCE_7D
from notifications.email import send_alert

logger = logging.getLogger(__name__)


class AuditorAgent(BaseAgent):
    """Detects campaign anomalies by diffing current metrics against previous snapshots.

    Runs every 6 hours. Writes all findings to audit_log regardless of severity.
    Immediately emails for HIGH and CRITICAL findings.
    """

    name = "auditor"

    def execute(self, account: Account) -> AgentRunResult:
        """Run anomaly detection for one account."""
        rows = self.ads.run_query(account.customer_id, CAMPAIGN_PERFORMANCE_7D)

        if not rows:
            return AgentRunResult(
                agent_name=self.name,
                account_id=account.id,
                status="success",
                summary="No campaigns returned from API",
            )

        campaign_data = [parse_gaql_row(r) for r in rows]
        new_snapshots = save_snapshot(self.db, account.id, campaign_data)

        benchmarks = self._get_benchmarks(account.industry)
        context = build_client_context(account, benchmarks)
        thresholds = config.ANOMALY_THRESHOLDS.get(
            account.budget_sensitivity or "moderate",
            config.ANOMALY_THRESHOLDS["moderate"],
        )

        total_tokens = 0
        anomalies_found = 0

        for snapshot in new_snapshots:
            previous = get_previous_snapshot(
                self.db, account.id, snapshot.campaign_id, snapshot.snapshot_time
            )
            if previous is None:
                logger.debug("No previous snapshot for campaign %s — skipping diff", snapshot.campaign_id)
                continue

            triggered = _detect_anomalies(snapshot, previous, thresholds)

            for anomaly in triggered:
                audit_entry, tokens = self._analyse_anomaly(
                    account=account,
                    context=context,
                    snapshot=snapshot,
                    previous=previous,
                    anomaly=anomaly,
                )
                total_tokens += tokens
                anomalies_found += 1

                if audit_entry.severity in config.IMMEDIATE_ALERT_SEVERITIES and account.alert_email:
                    send_alert(
                        account_name=account.client_name,
                        anomaly_type=audit_entry.anomaly_type or "",
                        severity=audit_entry.severity or "",
                        campaign_name=snapshot.campaign_name or snapshot.campaign_id,
                        diagnosis=audit_entry.diagnosis or "",
                        recommended_action=audit_entry.recommended_action or "",
                        alert_email=account.alert_email,
                    )

        return AgentRunResult(
            agent_name=self.name,
            account_id=account.id,
            status="success",
            tokens_used=total_tokens,
            cost_usd=self.claude.estimate_cost_usd(total_tokens),
            anomalies_found=anomalies_found,
            summary=f"Checked {len(new_snapshots)} campaigns, found {anomalies_found} anomalies",
        )

    def _analyse_anomaly(
        self,
        account: Account,
        context: str,
        snapshot: Any,
        previous: Any,
        anomaly: dict[str, Any],
    ) -> tuple[AuditLog, int]:
        """Send anomaly details to Claude and write the result to audit_log.

        Claude failure is non-fatal: the audit_log entry is always written,
        with diagnosis='AI diagnosis unavailable' if Claude cannot be reached.
        """
        user_message = f"""
{context}

=== ANOMALY DETECTED ===
Campaign: {snapshot.campaign_name} (ID: {snapshot.campaign_id})
Anomaly type: {anomaly['anomaly_type']}
Delta: {anomaly['delta_value']:.4f}
Threshold exceeded: {anomaly['threshold_used']:.4f}

=== CURRENT SNAPSHOT ===
Impressions: {snapshot.impressions}
Clicks: {snapshot.clicks}
CTR: {snapshot.ctr}
Cost (micros): {snapshot.cost_micros}
Conversions: {snapshot.conversions}
Conversion rate: {snapshot.conversion_rate}
Cost per conversion: {snapshot.cost_per_conversion}

=== PREVIOUS SNAPSHOT ===
Impressions: {previous.impressions}
Clicks: {previous.clicks}
CTR: {previous.ctr}
Cost (micros): {previous.cost_micros}
Conversions: {previous.conversions}
Conversion rate: {previous.conversion_rate}
Cost per conversion: {previous.cost_per_conversion}

Analyse this anomaly and return the JSON response.
"""
        tokens = 0
        result: dict[str, Any] = {}
        diagnosis = ""
        severity = config.SEVERITY_MEDIUM

        try:
            result, tokens = self.claude.complete_json(
                system_prompt=AUDITOR_SYSTEM_PROMPT,
                user_message=user_message,
            )
            diagnosis = result.get("diagnosis", "")
            severity = result.get("severity", config.SEVERITY_MEDIUM)
        except ValueError as exc:
            logger.warning(
                "[auditor] Claude returned malformed JSON for anomaly %s on campaign %s: %s",
                anomaly["anomaly_type"],
                snapshot.campaign_id,
                exc,
            )
            diagnosis = "Claude response malformed"
            severity = config.SEVERITY_MEDIUM
        except Exception as exc:
            logger.error(
                "[auditor] Claude call failed for anomaly %s on campaign %s: %s",
                anomaly["anomaly_type"],
                snapshot.campaign_id,
                exc,
            )
            diagnosis = "AI diagnosis unavailable"
            severity = config.SEVERITY_MEDIUM

        entry = AuditLog(
            account_id=account.id,
            run_time=datetime.now(timezone.utc),
            campaign_id=snapshot.campaign_id,
            anomaly_type=result.get("anomaly_type", anomaly["anomaly_type"]),
            severity=severity,
            diagnosis=diagnosis,
            recommended_action=result.get("recommended_action", ""),
            delta_value=anomaly["delta_value"],
            threshold_used=anomaly["threshold_used"],
        )
        self.db.add(entry)
        self.db.commit()
        return entry, tokens

    def _get_benchmarks(self, industry: str | None) -> IndustryBenchmark | None:
        if not industry:
            return None
        stmt = select(IndustryBenchmark).where(IndustryBenchmark.industry == industry)
        return self.db.scalars(stmt).first()


# ── Pure anomaly detection logic (no DB or API calls) ─────────────────────────

def _detect_anomalies(
    current: Any,
    previous: Any,
    thresholds: dict[str, float],
) -> list[dict[str, Any]]:
    """Compare two snapshots and return a list of triggered anomalies.

    Each item has: anomaly_type, delta_value, threshold_used.
    """
    anomalies: list[dict[str, Any]] = []

    def pct_change(new: float | None, old: float | None) -> float | None:
        if old is None or old == 0 or new is None:
            return None
        return ((new - old) / abs(old)) * 100

    # CTR drop
    ctr_delta = pct_change(current.ctr, previous.ctr)
    threshold = thresholds["ctr_drop_pct"]
    if ctr_delta is not None and ctr_delta < -threshold:
        anomalies.append({"anomaly_type": "ctr_drop", "delta_value": ctr_delta, "threshold_used": -threshold})

    # Spend spike
    spend_delta = pct_change(current.cost_micros, previous.cost_micros)
    threshold = thresholds["spend_spike_pct"]
    if spend_delta is not None and spend_delta > threshold:
        anomalies.append({"anomaly_type": "spend_spike", "delta_value": spend_delta, "threshold_used": threshold})

    # CVR collapse
    cvr_delta = pct_change(current.conversion_rate, previous.conversion_rate)
    threshold = thresholds["cvr_collapse_pct"]
    if cvr_delta is not None and cvr_delta < -threshold:
        anomalies.append({"anomaly_type": "cvr_collapse", "delta_value": cvr_delta, "threshold_used": -threshold})

    # CPA spike
    cpa_delta = pct_change(current.cost_per_conversion, previous.cost_per_conversion)
    threshold = thresholds["cpa_spike_pct"]
    if cpa_delta is not None and cpa_delta > threshold:
        anomalies.append({"anomaly_type": "cpa_spike", "delta_value": cpa_delta, "threshold_used": threshold})

    # Zero conversions with spend
    if (
        current.clicks
        and current.clicks > 20
        and current.cost_micros
        and current.cost_micros > 0
        and (current.conversions is None or current.conversions == 0)
    ):
        anomalies.append({"anomaly_type": "zero_conversions", "delta_value": 0.0, "threshold_used": 0.0})

    return anomalies
