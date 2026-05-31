"""Generates 3 ICP persona archetypes from brand DNA using Claude."""
from app.agents.claude_client import ClaudeClient

_SYSTEM = """You are an ICP (Ideal Customer Profile) strategist. Given a business's brand DNA, return ONLY valid JSON — an array of exactly 3 distinct persona archetypes:
[
  {
    "persona_name": "Short descriptive name (e.g. 'The Busy Professional')",
    "age_min": 25,
    "age_max": 40,
    "gender_skew": "Any|Female-skewed|Male-skewed",
    "income_bracket": "e.g. R20k–R40k/month",
    "location_type": "Urban|Suburban|Rural",
    "interests": ["interest1", "interest2", "interest3"],
    "values": ["value1", "value2"],
    "pain_points": ["pain1", "pain2", "pain3"],
    "goals": ["goal1", "goal2"],
    "preferred_channels": ["Instagram", "LinkedIn"],
    "seo_keywords": ["keyword1", "keyword2", "keyword3"],
    "vocabulary": ["word1", "word2"]
  }
]
Make the 3 personas genuinely distinct — different demographics, motivations, and channels."""


def suggest_personas(
    client_name: str,
    industry: str | None,
    tagline: str | None,
    tone: str | None,
    usps: list[str],
    key_messages: list[str],
) -> list[dict]:
    prompt = f"""Business: {client_name}
Industry: {industry or "Not specified"}
Tagline: {tagline or "Not set"}
Tone: {tone or "Not set"}
USPs: {", ".join(usps) if usps else "Not set"}
Key Messages: {", ".join(key_messages) if key_messages else "Not set"}

Generate 3 distinct ICP persona archetypes for this business."""

    return ClaudeClient().call_json(_SYSTEM, prompt, max_tokens=1500)
