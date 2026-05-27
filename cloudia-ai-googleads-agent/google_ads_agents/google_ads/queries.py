"""All GAQL query strings. Use named constants only — never inline GAQL."""

CAMPAIGN_PERFORMANCE_7D = """
SELECT
  campaign.id, campaign.name, campaign.status,
  campaign_budget.amount_micros,
  metrics.impressions, metrics.clicks,
  metrics.cost_micros, metrics.conversions,
  metrics.ctr, metrics.average_cpc,
  metrics.cost_per_conversion, metrics.conversions_from_interactions_rate,
  metrics.search_impression_share
FROM campaign
WHERE segments.date DURING LAST_7_DAYS
  AND campaign.status != 'REMOVED'
ORDER BY metrics.cost_micros DESC
"""

CAMPAIGN_PERFORMANCE_30D = """
SELECT
  campaign.id, campaign.name,
  metrics.impressions, metrics.clicks,
  metrics.cost_micros, metrics.conversions,
  metrics.ctr, metrics.average_cpc,
  metrics.cost_per_conversion, metrics.roas
FROM campaign
WHERE segments.date DURING LAST_30_DAYS
  AND campaign.status != 'REMOVED'
"""

ADGROUP_BIDS = """
SELECT
  ad_group.id, ad_group.name, ad_group.status,
  ad_group.cpc_bid_micros,
  campaign.id, campaign.name,
  metrics.impressions, metrics.clicks,
  metrics.ctr, metrics.conversions,
  metrics.average_cpc
FROM ad_group
WHERE segments.date DURING LAST_7_DAYS
  AND ad_group.status != 'REMOVED'
"""

SEARCH_TERMS_30D = """
SELECT
  search_term_view.search_term,
  search_term_view.status,
  campaign.name, ad_group.name,
  metrics.impressions, metrics.clicks,
  metrics.conversions, metrics.cost_micros,
  metrics.ctr, metrics.average_cpc
FROM search_term_view
WHERE segments.date DURING LAST_30_DAYS
  AND metrics.impressions > 10
ORDER BY metrics.clicks DESC
"""

KEYWORD_PERFORMANCE_30D = """
SELECT
  ad_group_criterion.keyword.text,
  ad_group_criterion.keyword.match_type,
  ad_group_criterion.quality_info.quality_score,
  ad_group_criterion.status,
  campaign.name, ad_group.name,
  metrics.impressions, metrics.clicks,
  metrics.ctr, metrics.average_cpc,
  metrics.conversions, metrics.cost_per_conversion
FROM keyword_view
WHERE segments.date DURING LAST_30_DAYS
  AND ad_group_criterion.status != 'REMOVED'
ORDER BY metrics.cost_micros DESC
"""

CAMPAIGN_BUDGETS = """
SELECT
  campaign.id, campaign.name,
  campaign_budget.id, campaign_budget.name,
  campaign_budget.amount_micros,
  campaign_budget.delivery_method
FROM campaign
WHERE campaign.status != 'REMOVED'
"""

AD_DISAPPROVALS = """
SELECT
  ad_group_ad.ad.id,
  ad_group_ad.policy_summary.approval_status,
  ad_group_ad.policy_summary.review_status,
  campaign.name, ad_group.name
FROM ad_group_ad
WHERE ad_group_ad.policy_summary.approval_status = 'DISAPPROVED'
  AND campaign.status != 'REMOVED'
"""
