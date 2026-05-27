PERFORMANCE_SUMMARY_PROMPT = """
Analyse the following post analytics data for client {client_name}.
Campaign: {campaign_name}

Analytics snapshot ({snapshot_type}):
{analytics_data}

Campaign average engagement rate: {campaign_avg_rate}

Return JSON:
{{
  "performance": "overperforming|average|underperforming",
  "insight": "one sentence about why",
  "recommendation": "one actionable suggestion for future content"
}}
"""

STOCK_SEARCH_QUERY_PROMPT = """
Generate 3 different Unsplash/Pexels search query variations for a stock photo.
Topic: {topic}
Client industry: {industry}
South African context if applicable.

Return JSON array of 3 strings:
["query1", "query2", "query3"]
"""
