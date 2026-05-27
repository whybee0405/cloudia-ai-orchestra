# Database Schema

PostgreSQL 15. All migrations managed by Alembic.

## Table Dependency Order (creation order)

```
clients
  └─ campaigns (client_id FK RESTRICT)
       └─ content_assets (campaign_id FK CASCADE)
            └─ asset_versions (asset_id FK CASCADE)
       └─ content_calendar (campaign_id FK CASCADE, asset_id FK RESTRICT)
            └─ scheduled_posts (calendar_id FK RESTRICT)
                 └─ published_posts (scheduled_post_id FK RESTRICT)
                      └─ post_analytics (published_post_id FK CASCADE)
       └─ agent_tasks (campaign_id FK CASCADE, calendar_id FK CASCADE)
       └─ approval_gates (campaign_id FK CASCADE)
  └─ brand_guidelines (client_id FK CASCADE, UNIQUE client_id)
  └─ platform_accounts (client_id FK RESTRICT)
```

---

## clients

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK |
| name | String(200) | NOT NULL |
| industry | String(100) | |
| business_type | String(100) | |
| target_audience | Text | |
| usp | Text | unique selling proposition |
| tone_of_voice | String(100) | |
| brand_colours | JSON | `{"primary": "#hex", "secondary": "#hex"}` |
| city | String(100) | |
| country | String(100) | default "South Africa" |
| is_active | Boolean | default True |
| created_at | DateTime(tz) | server_default now() |

---

## campaigns

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK |
| client_id | Integer | FK → clients.id RESTRICT |
| name | String(200) | NOT NULL |
| goal | String(100) | lead_gen / brand_awareness / sales / engagement |
| brief | JSON | full campaign brief |
| platforms | JSON | list of platform strings |
| duration_days | Integer | |
| start_date | Date | |
| end_date | Date | |
| posts_per_week | Integer | |
| content_mix | JSON | `{"image_post": 2, "reel": 1}` |
| target_audience | Text | |
| campaign_hashtags | JSON | list of hashtag strings |
| operator_notes | Text | |
| status | String(50) | planned/creating/calendar_review/approved/scheduled/active/paused/completed/failed |
| progress | Integer | 0–100 |
| created_at | DateTime(tz) | |
| updated_at | DateTime(tz) | |

---

## content_calendar

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK |
| campaign_id | Integer | FK → campaigns.id CASCADE |
| client_id | Integer | FK → clients.id RESTRICT |
| asset_id | Integer | FK → content_assets.id RESTRICT, nullable |
| platform | String(50) | instagram/facebook/tiktok/etc |
| content_type | String(50) | image_post/reel/story/video/tweet/article/broadcast |
| scheduled_for | DateTime(tz) | UTC |
| status | String(50) | planned/generating/brand_review/approved/scheduled/published/failed |
| caption | Text | |
| hashtags | JSON | |
| notes | Text | |

---

## content_assets

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK |
| campaign_id | Integer | FK → campaigns.id CASCADE |
| client_id | Integer | FK → clients.id RESTRICT |
| calendar_item_id | Integer | FK → content_calendar.id, nullable |
| asset_type | String(50) | image/video/text/audio |
| storage_path | Text | MinIO object path |
| platform_versions | JSON | `{"instagram": {"path": "...", "width": 1080}}` |
| text_content | Text | caption or script text |
| generation_prompt | Text | prompt used for AI generation |
| status | String(50) | draft/generating/brand_check_failed/approved_for_review/approved/rejected |
| created_at | DateTime(tz) | |

---

## asset_versions

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK |
| asset_id | Integer | FK → content_assets.id CASCADE |
| version_number | Integer | |
| storage_path | Text | |
| notes | Text | |
| created_at | DateTime(tz) | |

---

## brand_guidelines

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK |
| client_id | Integer | FK → clients.id CASCADE, UNIQUE |
| logo_path | Text | MinIO path to logo file |
| primary_colour | String(20) | hex |
| secondary_colour | String(20) | hex |
| font_name | String(100) | |
| tone_keywords | JSON | list of tone descriptors |
| forbidden_words | JSON | list of banned words |
| competitor_names | JSON | list of competitor brand names |
| required_elements | JSON | `{"logo_on_all_images": true}` |
| copy_style_notes | Text | |
| cta_text | String(200) | default call-to-action |
| voice_id | String(100) | ElevenLabs voice ID |
| intro_video_path | Text | MinIO path |
| outro_video_path | Text | MinIO path |
| music_path | Text | MinIO path |
| colour_grade_lut_path | Text | MinIO path |
| watermark_text | String(200) | |
| created_at | DateTime(tz) | |
| updated_at | DateTime(tz) | |

---

## platform_accounts

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK |
| client_id | Integer | FK → clients.id RESTRICT |
| platform | String(50) | instagram/facebook/etc |
| account_id | String(200) | platform's own ID (page ID, org ID) |
| account_name | String(200) | display name |
| access_token | Text | Fernet-encrypted |
| refresh_token | Text | Fernet-encrypted, nullable |
| token_expires_at | DateTime(tz) | nullable |
| is_active | Boolean | default True |
| last_verified_at | DateTime(tz) | |
| | | UNIQUE(client_id, platform, account_id) |

---

## scheduled_posts

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK |
| calendar_id | Integer | FK → content_calendar.id RESTRICT |
| asset_id | Integer | FK → content_assets.id RESTRICT |
| platform_account_id | Integer | FK → platform_accounts.id RESTRICT |
| scheduled_for | DateTime(tz) | UTC |
| caption | Text | |
| hashtags | JSON | |
| status | String(50) | queued/published/failed/cancelled |
| celery_task_id | String(200) | for revocation |
| created_at | DateTime(tz) | |

---

## published_posts

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK |
| scheduled_post_id | Integer | FK → scheduled_posts.id RESTRICT |
| platform | String(50) | |
| platform_post_id | String(200) | platform's own post ID |
| post_url | Text | |
| published_at | DateTime(tz) | |

---

## post_analytics

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK |
| published_post_id | Integer | FK → published_posts.id CASCADE |
| snapshot_type | String(10) | 24h/72h/7d |
| pulled_at | DateTime(tz) | |
| impressions | Integer | |
| reach | Integer | |
| likes | Integer | |
| comments | Integer | |
| shares | Integer | |
| saves | Integer | |
| clicks | Integer | |
| video_views | Integer | |
| engagement_rate | Numeric(8,4) | (likes+comments+shares)/reach |
| platform_raw | JSON | raw platform response |

---

## agent_tasks

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK |
| campaign_id | Integer | FK → campaigns.id CASCADE |
| calendar_id | Integer | FK → content_calendar.id CASCADE, nullable |
| agent_name | String(100) | |
| pipeline_order | Integer | 0–99, used for progress bar |
| status | String(50) | pending/running/completed/failed/revoked |
| input_data | JSON | |
| output_data | JSON | |
| error | Text | |
| tokens_used | Integer | |
| cost_usd | Numeric(10,6) | |
| celery_task_id | String(200) | |
| started_at | DateTime(tz) | |
| completed_at | DateTime(tz) | |

---

## approval_gates

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK |
| campaign_id | Integer | FK → campaigns.id CASCADE |
| gate_name | String(100) | calendar_review/content_batch_review |
| status | String(50) | pending/approved/rejected |
| operator_notes | Text | |
| reviewed_at | DateTime(tz) | |
| created_at | DateTime(tz) | |

---

## Cascade Summary

| Parent deleted | Child action |
|----------------|-------------|
| campaigns | content_calendar → CASCADE |
| campaigns | content_assets → CASCADE |
| campaigns | agent_tasks → CASCADE |
| campaigns | approval_gates → CASCADE |
| content_assets | asset_versions → CASCADE |
| published_posts | post_analytics → CASCADE |
| clients | campaigns → RESTRICT (must delete campaigns first) |
| platform_accounts | scheduled_posts → RESTRICT |
