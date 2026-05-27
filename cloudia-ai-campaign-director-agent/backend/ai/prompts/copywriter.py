COPYWRITER_PROMPT = """
Write a {platform} {content_type} caption for the client described in the context.
Topic: {topic}
Max characters: {max_chars}
Required hashtags (must include all): {required_hashtags}
Campaign hashtags (must include all): {campaign_hashtags}
Max hashtags: {max_hashtags}
Include a clear CTA related to campaign goal: {goal}

Return JSON:
{{
  "caption": "...",
  "hashtags": ["#tag1", "#tag2"],
  "first_comment": "hashtag overflow for Instagram if needed",
  "cta": "the CTA phrase used"
}}
"""
