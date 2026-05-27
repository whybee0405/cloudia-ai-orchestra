BRAND_TONE_CHECK_PROMPT = """
Analyse the following text for tone compliance.
Expected tone keywords: {tone_keywords}
Forbidden words: {forbidden_words}
Competitor names (must not appear): {competitor_names}

Text to check:
{text}

Return JSON:
{{
  "passed": bool,
  "issues": [
    {{
      "field": "caption|headline|body",
      "issue": "description of problem",
      "severity": "CRITICAL|HIGH|MEDIUM|LOW"
    }}
  ]
}}
If no issues: return {{"passed": true, "issues": []}}
"""
