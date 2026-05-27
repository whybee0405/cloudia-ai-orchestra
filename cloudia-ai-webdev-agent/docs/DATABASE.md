# Database Schema

PostgreSQL 15. ORM: SQLAlchemy 2.0. Migrations: Alembic.

## Tables

### clients
Primary profile for each agency client.

| Column | Type | Notes |
|---|---|---|
| id | SERIAL PK | |
| name | VARCHAR(255) | Required |
| industry | VARCHAR(100) | e.g. "dental", "retail", "restaurant" |
| business_type | VARCHAR(50) | "ecommerce", "local_service", "restaurant" |
| target_audience | TEXT | |
| usp | TEXT | Unique selling proposition |
| tone_of_voice | VARCHAR(50) | "professional", "friendly", "luxury", "bold" |
| brand_colours | JSON | `{"primary": "#hex", "secondary": "#hex", "accent": "#hex"}` |
| brand_fonts | JSON | `{"heading": "Playfair Display", "body": "Inter"}` |
| logo_url | TEXT | |
| contact_email | VARCHAR(255) | |
| contact_phone | VARCHAR(50) | |
| address | TEXT | |
| city | VARCHAR(100) | |
| country | VARCHAR(100) | Default: "South Africa" |
| website_url | TEXT | Existing site if any |
| social_links | JSON | `{"facebook": "...", "instagram": "..."}` |
| created_at | TIMESTAMP | Default: NOW() |
| notes | TEXT | Operator notes |

### projects
One project per website build attempt. A client can have multiple projects (e.g., rebuilt after launch).

| Column | Type | Notes |
|---|---|---|
| id | SERIAL PK | |
| client_id | INTEGER FK → clients(id) | CASCADE delete restricted at app level |
| platform | VARCHAR(20) | "wordpress" or "shopify" |
| status | VARCHAR(30) | See status lifecycle below |
| brief | JSON | Full raw brief from GUI form |
| pipeline_plan | JSON | Director's output: platform, page_list, structure |
| site_url | TEXT | Live URL once built |
| admin_url | TEXT | WP admin or Shopify admin URL |
| credentials | JSON | Encrypted reference — actual credentials in platform_credentials |
| estimated_pages | INTEGER | From Director |
| actual_pages | INTEGER | Actual count after build |
| created_at | TIMESTAMP | |
| completed_at | TIMESTAMP | |
| operator_notes | TEXT | |

**Status lifecycle:** `planned → running → awaiting_content_review → awaiting_site_review → completed`
Also: `needs_input` (ambiguous platform), `failed`, `cancelled`

### agent_tasks
One row per agent per project. Pipeline execution record.

| Column | Type | Notes |
|---|---|---|
| id | SERIAL PK | |
| project_id | INTEGER FK → projects(id) | Cascade delete |
| agent_name | VARCHAR(100) | "content_agent", "wp_builder_agent", etc. |
| pipeline_order | INTEGER | Execution order within pipeline |
| status | VARCHAR(20) | pending → running → completed/failed |
| input_data | JSON | What the agent received |
| output_data | JSON | What the agent returned (including qa_report) |
| tokens_used | INTEGER | Claude tokens consumed |
| cost_usd | NUMERIC(8,6) | Claude cost in USD |
| started_at | TIMESTAMP | |
| completed_at | TIMESTAMP | |
| error | TEXT | Error message if failed |
| retry_count | INTEGER | Default 0 |
| celery_task_id | VARCHAR(255) | Celery task UUID |

### approval_gates
Human-in-the-loop checkpoints.

| Column | Type | Notes |
|---|---|---|
| id | SERIAL PK | |
| project_id | INTEGER FK → projects(id) | Cascade delete |
| gate_name | VARCHAR(100) | "content_review", "site_review", "store_review" |
| pipeline_order | INTEGER | Position in pipeline |
| status | VARCHAR(20) | pending → approved / rejected / revision_requested |
| notes | TEXT | Operator feedback (required on rejection) |
| created_at | TIMESTAMP | |
| reviewed_at | TIMESTAMP | |
| reviewed_by | VARCHAR(100) | Operator identifier |

### generated_content
All AI-generated copy. Approved before publishing to platform.

| Column | Type | Notes |
|---|---|---|
| id | SERIAL PK | |
| project_id | INTEGER FK → projects(id) | Cascade delete |
| page_slug | VARCHAR(255) | "home", "about", "services", "contact" |
| content_type | VARCHAR(50) | "page", "product", "post", "collection" |
| title | VARCHAR(255) | Page title |
| h1 | VARCHAR(255) | Must differ from title |
| body_content | TEXT | Min 100 chars |
| cta_text | VARCHAR(100) | Button/link text |
| meta_title | VARCHAR(60) | Max 60 chars — enforced |
| meta_description | VARCHAR(160) | Max 160 chars — enforced |
| schema_markup | JSON | SEO schema, injected by SEO agent |
| status | VARCHAR(20) | draft → approved → published |
| revision_notes | TEXT | Operator feedback |
| platform_id | VARCHAR(100) | WP post ID or Shopify resource ID after publishing |

### project_media
Images sourced from Unsplash/Pexels.

| Column | Type | Notes |
|---|---|---|
| id | SERIAL PK | |
| project_id | INTEGER FK → projects(id) | Cascade delete |
| page_slug | VARCHAR(255) | Which page this image is for |
| image_purpose | VARCHAR(100) | "hero", "featured", "product", "gallery" |
| source | VARCHAR(50) | "unsplash", "pexels", "client_upload" |
| source_id | VARCHAR(255) | Unsplash photo ID (for deduplication) |
| source_url | TEXT | Original URL |
| local_path | TEXT | Downloaded file path |
| optimised_path | TEXT | After Pillow resize |
| alt_text | TEXT | AI-generated |
| attribution | TEXT | "Photo by [Name] on Unsplash" — required |
| platform_media_id | VARCHAR(100) | ID after uploading to WP/Shopify |

### platform_credentials
Client platform access. Encrypted at rest.

| Column | Type | Notes |
|---|---|---|
| id | SERIAL PK | |
| client_id | INTEGER FK → clients(id) | |
| platform | VARCHAR(20) | "wordpress" or "shopify" |
| site_url | TEXT | Base URL of the site |
| api_url | TEXT | Override API URL if non-standard |
| _access_token_encrypted | TEXT | Shopify access token — Fernet encrypted |
| _app_password_encrypted | TEXT | WP app password — Fernet encrypted |
| shop_name | VARCHAR(255) | Shopify store name |
| api_version | VARCHAR(20) | Shopify API version |
| is_active | BOOLEAN | Default TRUE |
| created_at | TIMESTAMP | |
| last_verified_at | TIMESTAMP | Last successful connection test |

## Cascade Rules

- Delete Project → cascade delete: agent_tasks, approval_gates, generated_content, project_media
- Delete Client → RESTRICT (do not cascade — must cancel all projects first)

## Running Migrations

```bash
# Inside Docker:
docker compose exec api alembic upgrade head

# Create new migration after model change:
docker compose exec api alembic revision --autogenerate -m "description"
```
