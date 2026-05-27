"""
Tests for the ContentAgent and GeneratedContent model.

GeneratedContent stores content as individual named columns (title, h1,
body_content, cta_text, meta_title, meta_description, schema_markup, status).
All field assertions access columns directly.
"""

import pytest
from unittest.mock import patch
from tests.factories import (
    make_client,
    make_project,
    make_agent_task,
    make_generated_content,
)
from backend.db.models import GeneratedContent, ApprovalGate, ContentStatus


# ---------------------------------------------------------------------------
# GeneratedContent model — field validation and storage
# ---------------------------------------------------------------------------


class TestContentValidation:
    def test_meta_title_max_60_chars_stored(self, db):
        """meta_title column can store exactly 60 characters."""
        c = make_client(db)
        p = make_project(db, c.id)
        content = make_generated_content(
            db, p.id, "home", overrides={"meta_title": "A" * 60}
        )
        assert len(content.meta_title) == 60

    def test_generated_content_default_fields_stored(self, db):
        """Factory defaults must produce a valid GeneratedContent record."""
        c = make_client(db)
        p = make_project(db, c.id)
        content = make_generated_content(db, p.id, "about")
        assert content.page_slug == "about"
        assert content.content_type == "page"
        assert content.body_content is not None
        assert len(content.body_content) > 0

    def test_factory_content_has_all_expected_fields(self, db):
        """Factory content must populate all standard content fields."""
        c = make_client(db)
        p = make_project(db, c.id)
        content = make_generated_content(db, p.id, "home")
        assert content.title is not None
        assert content.h1 is not None
        assert content.body_content is not None
        assert content.cta_text is not None
        assert content.meta_title is not None
        assert content.meta_description is not None

    def test_content_status_defaults_to_draft(self, db):
        """Freshly created GeneratedContent must default to status='draft'."""
        c = make_client(db)
        p = make_project(db, c.id)
        content = make_generated_content(db, p.id, "services")
        assert content.status == ContentStatus.DRAFT

    def test_content_status_transitions_to_approved(self, db):
        """status can be set to 'approved' and persisted."""
        c = make_client(db)
        p = make_project(db, c.id)
        content = make_generated_content(db, p.id, "services")
        content.status = ContentStatus.APPROVED
        db.commit()
        db.refresh(content)
        assert content.status == ContentStatus.APPROVED

    def test_no_lorem_ipsum_in_factory_content(self, db):
        """Factory body content must not contain placeholder text."""
        c = make_client(db)
        p = make_project(db, c.id)
        content = make_generated_content(db, p.id, "home")
        all_text = " ".join(filter(None, [
            content.title, content.h1, content.body_content,
            content.cta_text, content.meta_title, content.meta_description,
        ]))
        assert "lorem ipsum" not in all_text.lower()
        assert "placeholder" not in all_text.lower()
        assert "TODO" not in all_text

    def test_body_content_min_length(self, db):
        """The body_content field must be at least 100 characters."""
        c = make_client(db)
        p = make_project(db, c.id)
        content = make_generated_content(db, p.id, "home")
        assert len(content.body_content or "") > 100

    def test_meta_description_under_160_chars(self, db):
        """Factory meta_description must be within the 160-character SEO limit."""
        c = make_client(db)
        p = make_project(db, c.id)
        content = make_generated_content(db, p.id, "home")
        assert len(content.meta_description or "") <= 160

    def test_meta_title_under_60_chars(self, db):
        """Factory meta_title must be within the 60-character SEO limit."""
        c = make_client(db)
        p = make_project(db, c.id)
        content = make_generated_content(db, p.id, "home")
        assert len(content.meta_title or "") <= 60


# ---------------------------------------------------------------------------
# GeneratedContent model — cascade and multi-page behaviour
# ---------------------------------------------------------------------------


class TestContentModelCascade:
    def test_content_cascade_delete_on_project_delete(self, db):
        """Deleting a project must remove all its GeneratedContent records."""
        c = make_client(db)
        p = make_project(db, c.id)
        content = make_generated_content(db, p.id, "home")
        content_id = content.id
        db.delete(p)
        db.commit()
        assert db.get(GeneratedContent, content_id) is None

    def test_multiple_content_pieces_per_project(self, db):
        """A project can hold multiple GeneratedContent records with different page_slug values."""
        c = make_client(db)
        p = make_project(db, c.id)
        slugs = ["home", "about", "services", "contact"]
        for slug in slugs:
            make_generated_content(db, p.id, slug)
        db.refresh(p)
        stored_slugs = {item.page_slug for item in p.generated_content}
        for slug in slugs:
            assert slug in stored_slugs

    def test_content_project_id_matches_parent(self, db):
        """GeneratedContent.project_id must equal the ID of the parent project."""
        c = make_client(db)
        p = make_project(db, c.id)
        content = make_generated_content(db, p.id, "home")
        assert content.project_id == p.id

    def test_revision_notes_stored(self, db):
        """revision_notes can be set and persisted."""
        c = make_client(db)
        p = make_project(db, c.id)
        content = make_generated_content(db, p.id, "home")
        content.revision_notes = "Please make the tone more friendly."
        db.commit()
        db.refresh(content)
        assert content.revision_notes == "Please make the tone more friendly."

    def test_schema_markup_stored_as_json(self, db):
        """schema_markup (JSON column) must persist a schema dict correctly."""
        c = make_client(db)
        p = make_project(db, c.id)
        schema = {
            "@context": "https://schema.org",
            "@type": "LocalBusiness",
            "name": "Sandton Dental Studio",
        }
        content = make_generated_content(db, p.id, "home", overrides={"schema_markup": schema})
        db.commit()
        db.refresh(content)
        assert content.schema_markup["@type"] == "LocalBusiness"
        assert content.schema_markup["@context"] == "https://schema.org"


# ---------------------------------------------------------------------------
# ContentAgent integration (xfail — requires live Claude mock + Celery)
# ---------------------------------------------------------------------------


class TestContentAgentIntegration:
    @pytest.mark.xfail(
        reason="ContentAgent requires live Claude mock wiring — integration test"
    )
    def test_content_agent_creates_gate(self, db):
        """After the content agent runs, a content_review gate must be created."""
        c = make_client(db)
        p = make_project(
            db,
            c.id,
            overrides={
                "pipeline_plan": {
                    "page_list": ["home", "about"],
                    "platform": "wordpress",
                }
            },
        )
        t = make_agent_task(db, p.id, "content_agent", pipeline_order=1)

        mock_response = {
            "home": {
                "title": "Test Home",
                "h1": "Welcome",
                "body_content": (
                    "Body content that is long enough to pass the minimum length "
                    "validation of 100 characters for the home page."
                ),
                "cta_text": "Contact Us",
                "meta_title": "Test Home — Business",
                "meta_description": "A valid meta description under 160 chars.",
            },
            "about": {
                "title": "About Us",
                "h1": "Our Story",
                "body_content": (
                    "About body content that is long enough to pass the minimum "
                    "length validation of 100 characters for the about page."
                ),
                "cta_text": "Learn More",
                "meta_title": "About Us — Business",
                "meta_description": "About us description under 160 chars.",
            },
        }

        with patch(
            "backend.ai.claude.call_claude_json",
            return_value=(mock_response, 200, 0.002),
        ):
            from backend.agents.shared.content_agent import ContentAgent

            agent = ContentAgent(project_id=p.id, task_id=t.id)
            result = agent.execute()

        gates = (
            db.query(ApprovalGate)
            .filter_by(project_id=p.id, gate_name="content_review")
            .all()
        )
        assert len(gates) == 1
        assert gates[0].status == "pending"

    @pytest.mark.xfail(
        reason="ContentAgent requires live Claude mock wiring — integration test"
    )
    def test_content_agent_creates_generated_content_records(self, db):
        """Content agent must persist one GeneratedContent record per page in the plan."""
        c = make_client(db)
        p = make_project(
            db,
            c.id,
            overrides={
                "pipeline_plan": {
                    "page_list": ["home", "about"],
                    "platform": "wordpress",
                }
            },
        )
        t = make_agent_task(db, p.id, "content_agent", pipeline_order=1)

        mock_response = {
            "home": {
                "title": "Home",
                "h1": "Welcome",
                "body_content": "Home body content long enough to satisfy the minimum 100 character length requirement.",
                "cta_text": "Call Now",
                "meta_title": "Home",
                "meta_description": "Home meta description.",
            },
            "about": {
                "title": "About",
                "h1": "About Us",
                "body_content": "About body content long enough to satisfy the minimum 100 character length requirement.",
                "cta_text": "Learn More",
                "meta_title": "About",
                "meta_description": "About meta description.",
            },
        }

        with patch(
            "backend.ai.claude.call_claude_json",
            return_value=(mock_response, 200, 0.002),
        ):
            from backend.agents.shared.content_agent import ContentAgent

            agent = ContentAgent(project_id=p.id, task_id=t.id)
            agent.execute()

        records = (
            db.query(GeneratedContent).filter_by(project_id=p.id).all()
        )
        assert len(records) == 2
        slugs = {r.page_slug for r in records}
        assert "home" in slugs
        assert "about" in slugs
