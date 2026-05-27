CALENDAR_GENERATION_PROMPT = """
Given the campaign context below, generate a content calendar as a JSON array.
Each item represents one post:
{
  "week": int,
  "day_offset": int,
  "platform": "instagram|facebook|whatsapp|google_business|linkedin|tiktok|twitter|youtube",
  "content_type": "image_post|reel|story|carousel|short_video|long_video|article|ad|whatsapp_broadcast",
  "topic": "what this post is about",
  "hour": int
}
Return the full array. Distribute posts evenly across the campaign duration.
Respect the platform optimal posting times.
Do not schedule two posts on the same platform within 3 hours of each other.
"""
