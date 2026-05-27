"""Applies approved actions from the approval queue to the Google Ads API.

SAFETY: This module only executes actions that have status='approved' in the
approval_queue. It never acts on pending or unreviewed items.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Any

from google.ads.googleads.errors import GoogleAdsException
from sqlalchemy.orm import Session

import config
from db.models import ApprovalQueue
from google_ads.client import AdsClient

logger = logging.getLogger(__name__)


class AlreadyExecutedError(Exception):
    """Raised when attempting to execute a queue item that is already executed."""


class SecurityError(Exception):
    """Raised when a cross-account execution is attempted."""


class Executor:
    """Translates approved queue decisions into Google Ads API mutations."""

    def __init__(self, ads_client: AdsClient, db: Session) -> None:
        self.ads = ads_client
        self.db = db

    # ── Public dispatch ──────────────────────────────────────────────────────

    def execute_approved(self, queue_item: ApprovalQueue, customer_id: str) -> dict[str, Any]:
        """Execute a single approved queue item and update its status.

        Args:
            queue_item: An ApprovalQueue row with status='approved'.
            customer_id: The Google Ads customer ID for this account.

        Returns:
            A result dict with 'success' bool and optional 'details'.

        Raises:
            PermissionError: If the item is not in 'approved' state.
            AlreadyExecutedError: If the item was already executed.
            SecurityError: If the customer_id doesn't match the linked account.
            ValueError: If action_type is unknown.
        """
        if queue_item.status == config.QUEUE_STATUS_EXECUTED:
            raise AlreadyExecutedError(
                f"Queue item {queue_item.id} was already executed at {queue_item.executed_at}"
            )

        if queue_item.status != config.QUEUE_STATUS_APPROVED:
            raise PermissionError(
                f"Queue item {queue_item.id} cannot be executed — "
                f"status is '{queue_item.status}' (must be 'approved')"
            )

        action = queue_item.action_type
        payload = queue_item.action_payload or {}

        dispatch: dict[str, Any] = {
            "increase_bid": self._set_ad_group_bid,
            "decrease_bid": self._set_ad_group_bid,
            "increase_budget": self._set_campaign_budget,
            "decrease_budget": self._set_campaign_budget,
            "pause_adgroup": self._set_ad_group_status,
            "enable_adgroup": self._set_ad_group_status,
            "pause_campaign": self._set_campaign_status,
            "add_negative_keyword": self._add_negative_keyword,
            "add_keyword": self._add_keyword,
            "create_campaign": self._create_campaign,
        }

        handler = dispatch.get(action)
        if handler is None:
            raise ValueError(f"Unknown action_type: {action!r}")

        last_exc: Exception | None = None
        for attempt in range(1, 4):
            try:
                result = handler(customer_id=customer_id, payload=payload)
                queue_item.status = config.QUEUE_STATUS_EXECUTED
                queue_item.executed_at = datetime.now(timezone.utc)
                queue_item.execution_result = result
                self.db.commit()
                logger.info("Executed queue item %d: %s (attempt %d)", queue_item.id, action, attempt)
                return result
            except GoogleAdsException as exc:
                error_messages = [e.message for e in exc.failure.errors]
                error_msg = "; ".join(error_messages)

                # Policy violations are terminal — no retry
                if any("POLICY" in (e.error_code.ListFields()[0][1].name if e.error_code.ListFields() else "") for e in exc.failure.errors):
                    queue_item.status = config.QUEUE_STATUS_FAILED
                    queue_item.failure_reason = f"Policy violation: {error_msg}"
                    queue_item.execution_result = {"error": error_msg, "policy_violation": True}
                    self.db.commit()
                    logger.error("Policy violation for queue item %d: %s", queue_item.id, error_msg)
                    raise

                # Rate limit → exponential backoff
                is_rate_limit = any("RATE_EXCEEDED" in str(e) or "QUOTA" in str(e) for e in error_messages)
                if is_rate_limit and attempt < 3:
                    wait = 2 ** attempt
                    logger.warning(
                        "Rate limit on queue item %d — backing off %ds (attempt %d/3)",
                        queue_item.id, wait, attempt,
                    )
                    time.sleep(wait)
                    last_exc = exc
                    continue

                queue_item.status = config.QUEUE_STATUS_FAILED
                queue_item.failure_reason = error_msg
                self.db.commit()
                logger.error("Execution failed for queue item %d: %s", queue_item.id, error_msg)
                raise

        # All retries exhausted
        queue_item.status = config.QUEUE_STATUS_FAILED
        queue_item.failure_reason = f"Max retries exhausted: {last_exc}"
        self.db.commit()
        raise last_exc  # type: ignore[misc]

    # ── Private action handlers ───────────────────────────────────────────────

    def _set_ad_group_bid(self, customer_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Set cpc_bid_micros on an ad group."""
        ad_group_id: str = payload["ad_group_id"]
        new_bid_micros: int = int(payload["new_value_micros"])

        ad_group_service = self.ads.get_service("AdGroupService")
        ad_group = self.ads.get_type("AdGroup")
        ad_group.resource_name = (
            ad_group_service.ad_group_path(customer_id, ad_group_id)
        )
        ad_group.cpc_bid_micros = new_bid_micros

        from google.protobuf import field_mask_pb2

        operation = self.ads.get_type("AdGroupOperation")
        operation.update = ad_group
        operation.update_mask.CopyFrom(
            field_mask_pb2.FieldMask(paths=["cpc_bid_micros"])
        )

        response = ad_group_service.mutate_ad_groups(
            customer_id=customer_id, operations=[operation]
        )
        return {"resource_name": response.results[0].resource_name, "new_bid_micros": new_bid_micros}

    def _set_campaign_budget(self, customer_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Set amount_micros on a campaign budget."""
        budget_id: str = payload["budget_id"]
        new_budget_micros: int = int(payload["new_value_micros"])

        budget_service = self.ads.get_service("CampaignBudgetService")
        budget = self.ads.get_type("CampaignBudget")
        budget.resource_name = budget_service.campaign_budget_path(customer_id, budget_id)
        budget.amount_micros = new_budget_micros

        from google.protobuf import field_mask_pb2

        operation = self.ads.get_type("CampaignBudgetOperation")
        operation.update = budget
        operation.update_mask.CopyFrom(
            field_mask_pb2.FieldMask(paths=["amount_micros"])
        )

        response = budget_service.mutate_campaign_budgets(
            customer_id=customer_id, operations=[operation]
        )
        return {"resource_name": response.results[0].resource_name, "new_budget_micros": new_budget_micros}

    def _set_ad_group_status(self, customer_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Pause or enable an ad group."""
        ad_group_id: str = payload["ad_group_id"]
        status_str: str = payload["status"]  # 'PAUSED' or 'ENABLED'

        ad_group_service = self.ads.get_service("AdGroupService")
        ad_group = self.ads.get_type("AdGroup")
        ad_group.resource_name = ad_group_service.ad_group_path(customer_id, ad_group_id)
        ad_group.status = self.ads.enums.AdGroupStatusEnum.AdGroupStatus[status_str]

        from google.protobuf import field_mask_pb2

        operation = self.ads.get_type("AdGroupOperation")
        operation.update = ad_group
        operation.update_mask.CopyFrom(field_mask_pb2.FieldMask(paths=["status"]))

        response = ad_group_service.mutate_ad_groups(
            customer_id=customer_id, operations=[operation]
        )
        return {"resource_name": response.results[0].resource_name, "status": status_str}

    def _set_campaign_status(self, customer_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Pause or enable a campaign. Requires explicit approval — treated as critical."""
        campaign_id: str = payload["campaign_id"]
        status_str: str = payload["status"]  # 'PAUSED' or 'ENABLED'

        campaign_service = self.ads.get_service("CampaignService")
        campaign = self.ads.get_type("Campaign")
        campaign.resource_name = campaign_service.campaign_path(customer_id, campaign_id)
        campaign.status = self.ads.enums.CampaignStatusEnum.CampaignStatus[status_str]

        from google.protobuf import field_mask_pb2

        operation = self.ads.get_type("CampaignOperation")
        operation.update = campaign
        operation.update_mask.CopyFrom(field_mask_pb2.FieldMask(paths=["status"]))

        response = campaign_service.mutate_campaigns(
            customer_id=customer_id, operations=[operation]
        )
        return {"resource_name": response.results[0].resource_name, "status": status_str}

    def _add_negative_keyword(self, customer_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Add a campaign-level negative keyword."""
        campaign_id: str = payload["campaign_id"]
        keyword_text: str = payload["keyword_text"]
        match_type: str = payload.get("match_type", "BROAD")

        criterion_service = self.ads.get_service("CampaignCriterionService")
        criterion = self.ads.get_type("CampaignCriterion")
        criterion.campaign = self.ads.get_service("CampaignService").campaign_path(
            customer_id, campaign_id
        )
        criterion.negative = True
        criterion.keyword.text = keyword_text
        criterion.keyword.match_type = (
            self.ads.enums.KeywordMatchTypeEnum.KeywordMatchType[match_type]
        )

        operation = self.ads.get_type("CampaignCriterionOperation")
        operation.create = criterion

        response = criterion_service.mutate_campaign_criteria(
            customer_id=customer_id, operations=[operation]
        )
        return {"resource_name": response.results[0].resource_name, "keyword": keyword_text}

    def _add_keyword(self, customer_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Add a keyword to an ad group."""
        ad_group_id: str = payload["ad_group_id"]
        keyword_text: str = payload["keyword_text"]
        match_type: str = payload.get("match_type", "BROAD")
        cpc_bid_micros: int | None = payload.get("cpc_bid_micros")

        criterion_service = self.ads.get_service("AdGroupCriterionService")
        criterion = self.ads.get_type("AdGroupCriterion")
        criterion.ad_group = self.ads.get_service("AdGroupService").ad_group_path(
            customer_id, ad_group_id
        )
        criterion.keyword.text = keyword_text
        criterion.keyword.match_type = (
            self.ads.enums.KeywordMatchTypeEnum.KeywordMatchType[match_type]
        )
        if cpc_bid_micros is not None:
            criterion.cpc_bid_micros = cpc_bid_micros

        operation = self.ads.get_type("AdGroupCriterionOperation")
        operation.create = criterion

        response = criterion_service.mutate_ad_group_criteria(
            customer_id=customer_id, operations=[operation]
        )
        return {"resource_name": response.results[0].resource_name, "keyword": keyword_text}

    def _create_campaign(self, customer_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Create a full campaign structure from a Creator agent payload.

        The payload must match the structure returned by the creator agent:
        { campaign_name, campaign_settings, ad_groups: [{ name, keywords, ads }] }
        """
        from google_ads.campaign_builder import build_campaign_from_structure

        return build_campaign_from_structure(
            ads_client=self.ads,
            customer_id=customer_id,
            structure=payload,
        )
