AD_COPY_PROMPT = """
Write 3 distinct ad copy variants for {platform} for the client in the context.
Campaign goal: {goal}
Target audience: {target_audience}
Headline character limit: {headline_limit}
Body copy character limit: {body_limit}

Each variant must be meaningfully different (different angle, hook, or CTA).

Return JSON array of 3 objects:
[
  {{
    "variant": 1,
    "headline": "...",
    "body": "...",
    "cta_button": "Shop Now|Learn More|Get Quote|Book Now"
  }},
  ...
]
"""
