VIDEO_SCRIPT_PROMPT = """
Write a complete video script for a {content_type} for the client in the context.
Topic: {topic}
Target duration: {target_seconds} seconds
Platform: {platform}

Return JSON:
{{
  "title": "...",
  "hook": "first 3 seconds — what grabs attention",
  "scenes": [
    {{
      "scene_number": 1,
      "duration_sec": 5,
      "visual": "describe what is shown on screen",
      "voiceover": "exact text spoken",
      "text_overlay": "optional on-screen text"
    }}
  ],
  "cta": "final call to action",
  "total_duration_sec": int
}}
Sum of scene duration_sec must equal total_duration_sec.
"""
