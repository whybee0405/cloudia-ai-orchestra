IMAGE_PROMPT_GENERATION = """
Write a DALL-E 3 prompt for a {content_type} image for the client in the context.
Topic: {topic}
Style guidance from brand guidelines: {image_style_notes}
Brand primary colour: {primary_colour}

The prompt must:
- Describe a photorealistic or appropriate artistic style
- Include the brand aesthetic
- NOT include any text overlays (text will be added separately)
- NOT include competitor brand names or logos
- Be safe for work, professional quality

Return JSON:
{{
  "prompt": "the full DALL-E 3 prompt",
  "style_notes": "brief note on style chosen"
}}
"""
