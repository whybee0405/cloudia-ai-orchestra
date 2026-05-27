SEO_ARTICLE_PROMPT = """
Write a full SEO-optimised blog article for the client described in the context.
Target keyword: {keyword}
Target word count: {word_count}
Include:
- Engaging headline (H1, under 60 chars)
- Meta description (under 160 chars)
- Excerpt for social promotion (under 280 chars)
- Full article body with H2/H3 subheadings
- Natural keyword placement throughout

Return JSON:
{{
  "headline": "...",
  "meta_title": "...",
  "meta_description": "...",
  "excerpt": "...",
  "body": "full article markdown"
}}
"""
