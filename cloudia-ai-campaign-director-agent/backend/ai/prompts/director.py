DIRECTOR_VALIDATE_PROMPT = """
Given the campaign brief below, analyse it and return a JSON object:
{
  "is_valid": bool,
  "missing_fields": ["field1", ...],
  "suggested_content_mix": {
    "image_post": int,
    "reel": int,
    "story": int,
    "article": int,
    "ad": int
  },
  "reasoning": "brief explanation"
}
"""
