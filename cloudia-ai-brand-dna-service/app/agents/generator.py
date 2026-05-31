from app.agents.claude_client import ClaudeClient

_SYSTEM = """You are a brand strategist. Given a business description, return ONLY a JSON object with these exact keys:
{
  "tagline": "short punchy tagline (max 10 words)",
  "tone": "one of: formal, casual, playful, authoritative, warm",
  "language_style": "2-3 sentence description of how the brand writes",
  "personality_traits": ["trait1", "trait2", "trait3"],
  "visual_style": "one of: minimalist, bold, editorial, dark-tech, luxury, warm, playful, corporate",
  "primary_color": "#rrggbb hex",
  "accent_color": "#rrggbb hex",
  "heading_font": "one of: Inter, Montserrat, Poppins, Playfair Display, Lora, Raleway, DM Sans, Nunito",
  "body_font": "one of: Inter, Montserrat, Poppins, Playfair Display, Lora, Raleway, DM Sans, Nunito",
  "usps": ["usp1", "usp2", "usp3"],
  "pain_points_addressed": ["pain1", "pain2", "pain3"],
  "key_messages": ["message1", "message2", "message3"],
  "differentiators": ["differentiator1", "differentiator2"]
}
Return ONLY the JSON, no explanation."""


def generate_brand_dna(prompt: str) -> dict:
    return ClaudeClient().call_json(_SYSTEM, prompt, max_tokens=1200)
