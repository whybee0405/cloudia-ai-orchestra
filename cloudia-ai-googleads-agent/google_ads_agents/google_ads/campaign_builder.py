"""Builds a full Google Ads campaign structure from the Creator agent's JSON output.

Called by executor.py when a create_campaign action is approved and executed.
"""

import logging
from typing import Any

from google_ads.client import AdsClient

logger = logging.getLogger(__name__)


def build_campaign_from_structure(
    ads_client: AdsClient,
    customer_id: str,
    structure: dict[str, Any],
) -> dict[str, Any]:
    """Create a campaign, ad groups, keywords, and ads in Google Ads.

    Args:
        ads_client: Authenticated AdsClient instance.
        customer_id: The Google Ads customer ID (no dashes).
        structure: Campaign structure dict from the Creator agent.
                   Schema: { campaign_name, campaign_settings, ad_groups: [...] }

    Returns:
        Dict with created resource names: { campaign, ad_groups, keywords, ads }
    """
    settings = structure["campaign_settings"]
    campaign_resource = _create_campaign(ads_client, customer_id, structure["campaign_name"], settings)
    logger.info("Created campaign: %s", campaign_resource)

    created_ad_groups: list[dict[str, Any]] = []
    for ag_spec in structure.get("ad_groups", []):
        ag_resource = _create_ad_group(
            ads_client, customer_id, campaign_resource, ag_spec
        )
        keyword_resources = _create_keywords(
            ads_client, customer_id, ag_resource, ag_spec.get("keywords", [])
        )
        ad_resources = _create_ads(
            ads_client,
            customer_id,
            ag_resource,
            ag_spec.get("ads", []),
            settings.get("final_url", ""),
        )
        created_ad_groups.append(
            {
                "ad_group": ag_resource,
                "keywords": keyword_resources,
                "ads": ad_resources,
            }
        )

    return {
        "campaign": campaign_resource,
        "ad_groups": created_ad_groups,
    }


def _create_campaign(
    ads_client: AdsClient,
    customer_id: str,
    name: str,
    settings: dict[str, Any],
) -> str:
    """Create a Search campaign and its budget. Returns the campaign resource name."""
    budget_service = ads_client.get_service("CampaignBudgetService")
    budget_op = ads_client.get_type("CampaignBudgetOperation")
    budget = budget_op.create
    budget.name = f"{name} Budget"
    budget.amount_micros = int(settings["budget_daily_micros"])
    budget.delivery_method = (
        ads_client.enums.BudgetDeliveryMethodEnum.BudgetDeliveryMethod.STANDARD
    )

    budget_response = budget_service.mutate_campaign_budgets(
        customer_id=customer_id, operations=[budget_op]
    )
    budget_resource = budget_response.results[0].resource_name

    campaign_service = ads_client.get_service("CampaignService")
    campaign_op = ads_client.get_type("CampaignOperation")
    campaign = campaign_op.create
    campaign.name = name
    campaign.advertising_channel_type = (
        ads_client.enums.AdvertisingChannelTypeEnum.AdvertisingChannelType.SEARCH
    )
    campaign.status = ads_client.enums.CampaignStatusEnum.CampaignStatus.PAUSED
    campaign.campaign_budget = budget_resource

    bidding = settings.get("bidding_strategy", "MANUAL_CPC")
    if bidding == "TARGET_CPA" and "target_cpa_micros" in settings:
        campaign.target_cpa.target_cpa_micros = int(settings["target_cpa_micros"])
    elif bidding == "TARGET_ROAS" and "target_roas" in settings:
        campaign.target_roas.target_roas = float(settings["target_roas"])
    elif bidding == "MAXIMIZE_CONVERSIONS":
        campaign.maximize_conversions.CopyFrom(ads_client.get_type("MaximizeConversions"))
    else:
        campaign.manual_cpc.enhanced_cpc_enabled = False

    network = campaign.network_settings
    network.target_google_search = settings.get("network_search", True)
    network.target_search_network = settings.get("network_search", True)
    network.target_content_network = settings.get("network_display", False)

    response = campaign_service.mutate_campaigns(
        customer_id=customer_id, operations=[campaign_op]
    )
    return response.results[0].resource_name


def _create_ad_group(
    ads_client: AdsClient,
    customer_id: str,
    campaign_resource: str,
    ag_spec: dict[str, Any],
) -> str:
    """Create one ad group. Returns the ad group resource name."""
    service = ads_client.get_service("AdGroupService")
    op = ads_client.get_type("AdGroupOperation")
    ag = op.create
    ag.name = ag_spec["name"]
    ag.campaign = campaign_resource
    ag.status = ads_client.enums.AdGroupStatusEnum.AdGroupStatus.ENABLED
    ag.cpc_bid_micros = int(ag_spec.get("default_cpc_bid_micros", 1_000_000))

    response = service.mutate_ad_groups(customer_id=customer_id, operations=[op])
    resource = response.results[0].resource_name
    logger.debug("Created ad group: %s", resource)
    return resource


def _create_keywords(
    ads_client: AdsClient,
    customer_id: str,
    ag_resource: str,
    keywords: list[dict[str, Any]],
) -> list[str]:
    """Add keywords to an ad group. Returns list of resource names."""
    if not keywords:
        return []

    service = ads_client.get_service("AdGroupCriterionService")
    operations = []
    for kw in keywords:
        op = ads_client.get_type("AdGroupCriterionOperation")
        criterion = op.create
        criterion.ad_group = ag_resource
        criterion.keyword.text = kw["text"]
        criterion.keyword.match_type = (
            ads_client.enums.KeywordMatchTypeEnum.KeywordMatchType[
                kw.get("match_type", "BROAD")
            ]
        )
        operations.append(op)

    response = service.mutate_ad_group_criteria(
        customer_id=customer_id, operations=operations
    )
    return [r.resource_name for r in response.results]


def _create_ads(
    ads_client: AdsClient,
    customer_id: str,
    ag_resource: str,
    ads: list[dict[str, Any]],
    default_url: str,
) -> list[str]:
    """Create responsive search ads in an ad group. Returns list of resource names."""
    if not ads:
        return []

    service = ads_client.get_service("AdGroupAdService")
    operations = []
    for ad_spec in ads:
        op = ads_client.get_type("AdGroupAdOperation")
        ag_ad = op.create
        ag_ad.ad_group = ag_resource
        ag_ad.status = ads_client.enums.AdGroupAdStatusEnum.AdGroupAdStatus.ENABLED

        rsa = ag_ad.ad.responsive_search_ad
        final_url = ad_spec.get("final_url") or default_url
        ag_ad.ad.final_urls.append(final_url)

        for field in ("headline_1", "headline_2", "headline_3"):
            if ad_spec.get(field):
                asset = ads_client.get_type("AdTextAsset")
                asset.text = ad_spec[field]
                rsa.headlines.append(asset)

        for field in ("description_1", "description_2"):
            if ad_spec.get(field):
                asset = ads_client.get_type("AdTextAsset")
                asset.text = ad_spec[field]
                rsa.descriptions.append(asset)

        operations.append(op)

    response = service.mutate_ad_group_ads(
        customer_id=customer_id, operations=operations
    )
    return [r.resource_name for r in response.results]
