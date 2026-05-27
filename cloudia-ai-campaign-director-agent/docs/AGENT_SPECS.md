# Agent Specifications

All agents extend `BaseAgent` and follow this contract:
- `__init__(db: Session)` — database session injected
- `run(*args) -> dict` — executes the agent, returns output summary
- Writes an `AgentTask` row (start → complete/fail)
- Tracks token usage and cost via `_track_tokens()`

---

## DirectorAgent
**File:** `backend/agents/director.py`  
**Pipeline order:** 10  
**Input:** `campaign_id: int`

**Validates:**
- All platforms in `campaign.platforms` have an active `PlatformAccount`
- Campaign brief is not empty
- `end_date > start_date`
- `posts_per_week > 0`

**On success:** Calls Claude to determine content mix, sets `campaign.status = "planning"`, queues `PlannerAgent`.

**Fails if:** Any platform missing an account, brief empty, date/week validation fails.

---

## PlannerAgent
**File:** `backend/agents/planner.py`  
**Pipeline order:** 20  
**Input:** `campaign_id: int`

**Behaviour:**
- Calls Claude with full campaign context to generate a calendar JSON
- Validates each item: platform in SUPPORTED_PLATFORMS, content_type in PLATFORM_SPECS
- Deduplicates slots: same platform within 3-hour window → shift to next window
- Creates `ContentCalendar` rows
- Creates `ApprovalGate(gate_name="calendar_review")`
- Sets `campaign.status = "calendar_review"`

**Fails if:** Claude returns malformed JSON after MAX_RETRIES.

---

## CopywriterAgent
**File:** `backend/agents/text/copywriter.py`  
**Pipeline order:** 30  
**Input:** `calendar_id: int`

**Behaviour:**
- Builds platform-specific prompt with tone, char limit, required hashtags
- Calls Claude, validates output: char limit, forbidden words, competitor names, required hashtags
- Retries up to `MAX_RETRIES = 2` if validation fails
- Saves caption + hashtags to `ContentAsset.platform_versions`

**Fails if:** Validation fails after all retries.

---

## ImageGeneratorAgent
**File:** `backend/agents/image/generator.py`  
**Pipeline order:** 31  
**Input:** `calendar_id: int`

**Behaviour:**
- Tries DALL-E 3 first; falls back to Replicate Flux on `BadRequestError` or `RateLimitError`
- Stores generated image to MinIO under `{client_id}/campaigns/{campaign_id}/raw/images/`
- Falls back to Unsplash stock if generation fails; then Pexels; then fails task

---

## VideoScriptAgent
**File:** `backend/agents/video/script.py`  
**Pipeline order:** 31  
**Input:** `calendar_id: int`

**Behaviour:**
- Calls Claude to produce a structured JSON script: `{scenes: [{duration_sec, visual, voiceover, text_overlay}]}`
- Validates: sum of scene durations = total_duration_sec
- Stores script JSON to `ContentAsset`
- Queues `VoiceoverAgent` and `BRollAgent` in parallel via Celery chord

---

## VoiceoverAgent
**File:** `backend/agents/video/voiceover.py`  
**Pipeline order:** 32  
**Input:** `asset_id: int`

**Behaviour:**
- Reads script from `ContentAsset`
- Calls ElevenLabs TTS per scene using `brand_guidelines.voice_id`
- Concatenates audio, stores to MinIO
- Validates audio duration within ±0.5s of target

**Fails if:** ElevenLabs API key invalid or voice_id not found. No silent fallback.

---

## BRollAgent
**File:** `backend/agents/video/broll.py`  
**Pipeline order:** 32  
**Input:** `asset_id: int`

**Behaviour:**
- Queries Pexels Video API per scene's `visual` field
- Downloads and trims clips to scene duration via ffmpeg
- Falls back to solid colour background if no clip found

---

## VideoAssemblerAgent
**File:** `backend/agents/video/assembler.py`  
**Pipeline order:** 33  
**Input:** `asset_id: int`

**Behaviour:**
- Waits for voiceover + b-roll to complete (Celery chord)
- Pre-flight: verifies all input files exist in MinIO
- Calls `ffmpeg_ops.assemble()` to compose final video
- Prepends brand intro, appends brand outro if configured
- Adds background music at 15% volume
- Recompresses if output exceeds platform size limit

---

## CaptionAgent
**File:** `backend/agents/video/captions.py`  
**Pipeline order:** 34  
**Input:** `asset_id: int`

**Behaviour:**
- Downloads voiceover from MinIO, runs OpenAI Whisper transcription
- Generates `.srt` file with non-overlapping timestamps
- Fallback: generates static SRT from script text if Whisper fails

---

## VideoEditorAgent
**File:** `backend/agents/editing/video_editor.py`  
**Pipeline order:** 35  
**Input:** `asset_id: int`

**Behaviour:**
- Burns subtitles into video via ffmpeg
- Applies colour grade LUT if configured
- Exports per-platform versions at correct resolution + aspect ratio

---

## ImageEditorAgent
**File:** `backend/agents/editing/image_editor.py`  
**Pipeline order:** 35  
**Input:** `asset_id: int`

**Behaviour:**
- Overlays logo on image (position from brand guidelines)
- Applies brand colour overlay if requested
- Adds text watermark if configured

---

## GraphicDesignAgent
**File:** `backend/agents/editing/graphic_design.py`  
**Pipeline order:** 35  
**Input:** `asset_id: int`

**Behaviour:**
- Calls Canva API to create branded template if `CANVA_API_KEY` is set
- Falls back to `ImageEditorAgent` if Canva unavailable

---

## BrandConsistencyAgent
**File:** `backend/agents/editing/brand_consistency.py`  
**Pipeline order:** 38  
**Input:** `asset_id: int`

**Severity tiers:**
| Severity | Result |
|----------|--------|
| CRITICAL | `brand_check_failed`, task fails |
| HIGH | `brand_check_failed`, task fails |
| MEDIUM/LOW | `approved_for_review` with warnings |

**Checks:**
- Forbidden words in caption → HIGH
- Competitor names in caption or voiceover script → CRITICAL
- Caption over char limit → HIGH
- Missing required hashtags → HIGH
- Logo absent when `required_elements.logo_on_all_images = true` → HIGH
- CTA absent → MEDIUM
- Tone mismatch → LOW/HIGH depending on severity

---

## FormatterAgent
**File:** `backend/agents/publishing/formatter.py`  
**Pipeline order:** 40  
**Input:** `asset_id: int`

**Behaviour:**
- Reads `PLATFORM_SPECS` for target dimensions
- Resizes/crops images via Pillow
- Transcodes videos via ffmpeg
- Stores platform-specific versions to MinIO
- Updates `ContentAsset.platform_versions`

---

## SchedulerAgent
**File:** `backend/agents/publishing/scheduler.py`  
**Pipeline order:** 45  
**Input:** `calendar_id: int`

**Behaviour:**
- Resolves optimal posting time (SAST) per platform
- Creates `ScheduledPost` with `scheduled_for` in UTC
- Queues `publish_post` Celery task with ETA
- Rejects past scheduling times with `AgentError`

---

## PublisherAgent
**File:** `backend/agents/publishing/publisher.py`  
**Pipeline order:** 50  
**Input:** `scheduled_post_id: int`

**Pre-flight checks (in order):**
1. `account.client_id == campaign.client_id` → `SecurityError` if mismatch
2. `account.is_active` → fail if inactive
3. `account.token_expires_at` not in past → fail if expired

**Post-publish:** Creates `PublishedPost`, queues analytics at 24h/72h/7d.

---

## AnalyticsAgent
**File:** `backend/agents/publishing/analytics.py`  
**Pipeline order:** 60  
**Input:** `published_post_id: int, snapshot_type: str`

**Behaviour:**
- Fetches platform-specific metrics
- Calculates `engagement_rate = (likes + comments + shares) / reach`
- `reach = 0` → `engagement_rate = None` (no crash)
- Flags underperformers: `engagement_rate < 0.005` at 7d snapshot
- Stores `PostAnalytics` row
