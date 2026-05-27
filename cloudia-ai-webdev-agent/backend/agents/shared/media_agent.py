"""
Media sourcing agent for the CloudIA agent system.

Sources images from Unsplash for each page, resizes them with Pillow,
stores them locally, and writes ProjectMedia records with full attribution.
"""

import io
import os
import time
from pathlib import Path
from typing import Any

import httpx
import structlog
from sqlalchemy import select

from backend.agents.base import BaseAgent
from backend.ai.claude import call_claude_json
from backend.ai.context_builder import build_project_context
from backend.ai.prompts.media import (
    MEDIA_SYSTEM_PROMPT,
    MEDIA_QUERY_PROMPT_TEMPLATE,
    MEDIA_ALT_TEXT_PROMPT_TEMPLATE,
)
from backend.config import settings
from backend.db.models import (
    Client,
    GeneratedContent,
    Project,
    ProjectMedia,
)
from backend.db.session import get_db

log = structlog.get_logger()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

UNSPLASH_API_BASE = "https://api.unsplash.com"
MAX_IMAGE_WIDTH = 1920
RATE_LIMIT_DELAY = 1.5  # seconds between Unsplash API calls
MEDIA_BASE_DIR = Path("media")


def _get_media_dir(project_id: int) -> Path:
    path = MEDIA_BASE_DIR / f"project_{project_id}"
    path.mkdir(parents=True, exist_ok=True)
    return path


class MediaAgent(BaseAgent):
    """Sources and processes images from Unsplash for each approved page."""

    agent_name = "media_agent"

    def run(self) -> dict:
        """
        1. Load project + approved content
        2. Check Unsplash API key
        3. Generate search queries via Claude
        4. Fetch + download images
        5. Resize with Pillow
        6. Write ProjectMedia records
        7. Return summary
        """
        # ------------------------------------------------------------------
        # Check API key
        # ------------------------------------------------------------------
        unsplash_key = settings.unsplash_access_key
        if not unsplash_key:
            self.log.warning(
                "media_agent_no_unsplash_key",
                message="Unsplash API key not configured — skipping media sourcing",
            )
            return {
                "images_sourced": 0,
                "images_failed": 0,
                "skipped": True,
                "reason": "Unsplash API key not configured",
                "_tokens_used": 0,
                "_cost_usd": 0.0,
            }

        # ------------------------------------------------------------------
        # Load project + client + approved content
        # ------------------------------------------------------------------
        with get_db() as db:
            project = db.get(Project, self.project_id)
            if project is None:
                raise RuntimeError(f"Project {self.project_id} not found")

            client = db.get(Client, project.client_id)
            if client is None:
                raise RuntimeError(f"Client {project.client_id} not found")

            approved_content = db.execute(
                select(GeneratedContent).where(
                    GeneratedContent.project_id == self.project_id,
                    GeneratedContent.status == "approved",
                )
            ).scalars().all()

            db.expunge(project)
            db.expunge(client)
            content_list = []
            for c in approved_content:
                db.expunge(c)
                content_list.append(c)

        if not content_list:
            self.log.warning("media_agent_no_approved_content")
            return {
                "images_sourced": 0,
                "images_failed": 0,
                "skipped": True,
                "reason": "No approved content found for this project",
                "_tokens_used": 0,
                "_cost_usd": 0.0,
            }

        self.log.info("media_agent_start", pages=len(content_list))
        context = build_project_context(client, project)

        total_tokens = 0
        total_cost = 0.0
        images_sourced = 0
        images_failed = 0

        media_dir = _get_media_dir(self.project_id)

        with httpx.Client(timeout=30.0) as http:
            for content in content_list:
                page_slug = content.page_slug

                # ----------------------------------------------------------
                # Skip if already have media for this page
                # ----------------------------------------------------------
                if self._has_existing_media(page_slug):
                    self.log.info("media_agent_skip_existing", page=page_slug)
                    continue

                # ----------------------------------------------------------
                # Generate search query via Claude
                # ----------------------------------------------------------
                content_summary = (
                    f"Title: {content.title or ''}\n"
                    f"H1: {content.h1 or ''}\n"
                    f"Body preview: {(content.body_content or '')[:300]}"
                )

                query_prompt = (
                    f"{context}\n\n"
                    + MEDIA_QUERY_PROMPT_TEMPLATE.format(
                        page_slug=page_slug,
                        page_title=content.title or page_slug,
                        content_summary=content_summary,
                    )
                )

                try:
                    queries_data, tokens, cost = call_claude_json(
                        prompt=query_prompt,
                        system=MEDIA_SYSTEM_PROMPT,
                        max_tokens=512,
                    )
                    total_tokens += tokens
                    total_cost += cost
                except Exception as exc:
                    self.log.error(
                        "media_query_generation_failed",
                        page=page_slug,
                        error=str(exc),
                    )
                    images_failed += 1
                    continue

                queries = queries_data.get("queries", [])
                if not queries:
                    self.log.warning("media_no_queries_generated", page=page_slug)
                    continue

                # ----------------------------------------------------------
                # Fetch image from Unsplash
                # ----------------------------------------------------------
                photo = self._fetch_unsplash_photo(
                    http=http,
                    primary_query=queries[0].get("primary_query", page_slug),
                    fallback_query=queries[0].get("fallback_query", "business professional"),
                    api_key=unsplash_key,
                )

                time.sleep(RATE_LIMIT_DELAY)  # rate limit compliance

                if photo is None:
                    self.log.warning("media_no_photo_found", page=page_slug)
                    # Write placeholder record
                    self._write_placeholder_media(page_slug, page_slug)
                    images_failed += 1
                    continue

                # ----------------------------------------------------------
                # Deduplicate by source_id
                # ----------------------------------------------------------
                photo_id = photo.get("id", "")
                if self._media_source_id_exists(photo_id):
                    self.log.info("media_deduplicate", photo_id=photo_id, page=page_slug)
                    continue

                # ----------------------------------------------------------
                # Download image
                # ----------------------------------------------------------
                image_url = photo.get("urls", {}).get("full") or photo.get("urls", {}).get("regular")
                if not image_url:
                    images_failed += 1
                    continue

                try:
                    image_data = self._download_image(http, image_url)
                except Exception as exc:
                    self.log.error(
                        "media_download_failed",
                        page=page_slug,
                        error=str(exc),
                    )
                    images_failed += 1
                    continue

                time.sleep(RATE_LIMIT_DELAY)

                # ----------------------------------------------------------
                # Resize with Pillow
                # ----------------------------------------------------------
                local_path, optimised_path = self._resize_and_save(
                    image_data=image_data,
                    media_dir=media_dir,
                    filename_base=f"{page_slug}_{photo_id}",
                )

                # ----------------------------------------------------------
                # Generate alt text via Claude
                # ----------------------------------------------------------
                alt_text = page_slug.replace("-", " ").title()
                try:
                    alt_prompt = (
                        f"{context}\n\n"
                        + MEDIA_ALT_TEXT_PROMPT_TEMPLATE.format(
                            image_url=photo.get("urls", {}).get("small", ""),
                            description=photo.get("description") or photo.get("alt_description") or "",
                            page_slug=page_slug,
                            section="hero",
                        )
                    )
                    alt_data, alt_tokens, alt_cost = call_claude_json(
                        prompt=alt_prompt,
                        system=MEDIA_SYSTEM_PROMPT,
                        max_tokens=128,
                    )
                    alt_text = alt_data.get("alt_text", alt_text)[:125]
                    total_tokens += alt_tokens
                    total_cost += alt_cost
                except Exception as exc:
                    self.log.warning("alt_text_generation_failed", error=str(exc))

                # ----------------------------------------------------------
                # Write ProjectMedia record
                # ----------------------------------------------------------
                photographer = photo.get("user", {})
                attribution = (
                    f"Photo by {photographer.get('name', 'Unknown')} "
                    f"on Unsplash — {photographer.get('links', {}).get('html', 'https://unsplash.com')}"
                )

                self._write_project_media(
                    page_slug=page_slug,
                    photo_id=photo_id,
                    source_url=image_url,
                    local_path=str(local_path),
                    optimised_path=str(optimised_path),
                    alt_text=alt_text,
                    attribution=attribution,
                )

                images_sourced += 1
                self.log.info("media_image_saved", page=page_slug, photo_id=photo_id)

        self.log.info(
            "media_agent_complete",
            sourced=images_sourced,
            failed=images_failed,
        )

        return {
            "images_sourced": images_sourced,
            "images_failed": images_failed,
            "skipped": False,
            "_tokens_used": total_tokens,
            "_cost_usd": total_cost,
        }

    # ------------------------------------------------------------------
    # Unsplash helpers
    # ------------------------------------------------------------------

    def _fetch_unsplash_photo(
        self,
        http: httpx.Client,
        primary_query: str,
        fallback_query: str,
        api_key: str,
    ) -> dict | None:
        """Try primary query, then fallback. Returns first photo dict or None."""
        for query in (primary_query, fallback_query):
            try:
                response = http.get(
                    f"{UNSPLASH_API_BASE}/search/photos",
                    params={
                        "query": query,
                        "per_page": 3,
                        "client_id": api_key,
                        "orientation": "landscape",
                    },
                    headers={"Accept-Version": "v1"},
                )

                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    self.log.warning(
                        "unsplash_rate_limited",
                        retry_after=retry_after,
                        query=query,
                    )
                    time.sleep(min(retry_after, 60))
                    continue

                response.raise_for_status()
                results = response.json().get("results", [])
                if results:
                    return results[0]

            except httpx.HTTPStatusError as exc:
                self.log.error(
                    "unsplash_http_error",
                    query=query,
                    status=exc.response.status_code,
                )
            except Exception as exc:
                self.log.error("unsplash_request_failed", query=query, error=str(exc))

            time.sleep(RATE_LIMIT_DELAY)

        return None

    def _download_image(self, http: httpx.Client, url: str) -> bytes:
        """Download image bytes from URL."""
        response = http.get(url, follow_redirects=True)
        response.raise_for_status()
        return response.content

    def _resize_and_save(
        self,
        image_data: bytes,
        media_dir: Path,
        filename_base: str,
    ) -> tuple[Path, Path]:
        """Resize image to max MAX_IMAGE_WIDTH px wide, save original + optimised."""
        try:
            from PIL import Image

            img = Image.open(io.BytesIO(image_data))
            orig_path = media_dir / f"{filename_base}_orig.jpg"

            # Save original
            img.save(str(orig_path), "JPEG", quality=95)

            # Resize if needed
            if img.width > MAX_IMAGE_WIDTH:
                ratio = MAX_IMAGE_WIDTH / img.width
                new_height = int(img.height * ratio)
                img = img.resize((MAX_IMAGE_WIDTH, new_height), Image.LANCZOS)

            # Convert to RGB if needed (e.g. PNG with transparency)
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")

            opt_path = media_dir / f"{filename_base}.jpg"
            img.save(str(opt_path), "JPEG", quality=85, optimize=True)

            return orig_path, opt_path

        except ImportError:
            # Pillow not installed — save raw bytes
            self.log.warning("pillow_not_installed_saving_raw")
            raw_path = media_dir / f"{filename_base}_raw.jpg"
            raw_path.write_bytes(image_data)
            return raw_path, raw_path

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    def _has_existing_media(self, page_slug: str) -> bool:
        with get_db() as db:
            existing = db.execute(
                select(ProjectMedia).where(
                    ProjectMedia.project_id == self.project_id,
                    ProjectMedia.page_slug == page_slug,
                )
            ).scalar_one_or_none()
            return existing is not None

    def _media_source_id_exists(self, source_id: str) -> bool:
        with get_db() as db:
            existing = db.execute(
                select(ProjectMedia).where(
                    ProjectMedia.project_id == self.project_id,
                    ProjectMedia.source_id == source_id,
                )
            ).scalar_one_or_none()
            return existing is not None

    def _write_placeholder_media(self, page_slug: str, query: str) -> None:
        with get_db() as db:
            record = ProjectMedia(
                project_id=self.project_id,
                page_slug=page_slug,
                source="unsplash",
                source_id=f"placeholder_{page_slug}",
                source_url="",
                local_path="",
                optimised_path="",
                alt_text=f"Image for {page_slug}",
                attribution="No image available",
                is_placeholder=True,
            )
            db.add(record)
            db.commit()

    def _write_project_media(
        self,
        page_slug: str,
        photo_id: str,
        source_url: str,
        local_path: str,
        optimised_path: str,
        alt_text: str,
        attribution: str,
    ) -> int:
        with get_db() as db:
            record = ProjectMedia(
                project_id=self.project_id,
                page_slug=page_slug,
                source="unsplash",
                source_id=photo_id,
                source_url=source_url,
                local_path=local_path,
                optimised_path=optimised_path,
                alt_text=alt_text,
                attribution=attribution,
                is_placeholder=False,
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            return record.id
