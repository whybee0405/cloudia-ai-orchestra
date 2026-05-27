"""
Integration tests for the CloudIA FastAPI routes.

Covers: authentication, project CRUD, content routes, approval routes,
credential encryption, and basic database integrity constraints.

All tests use the ``client`` and ``db`` fixtures from conftest.py, which
provide a FastAPI TestClient backed by an isolated in-memory SQLite database
that is rolled back after each test.
"""

import pytest
from sqlalchemy import text
from tests.factories import (
    make_client,
    make_project,
    make_agent_task,
    make_approval_gate,
    make_generated_content,
    make_credentials,
)
from backend.db.models import Project, AgentTask, ApprovalGate, GeneratedContent


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


class TestAuthentication:
    def test_routes_require_api_key(self, client):
        """Protected routes must return 401 when no API key is provided."""
        assert client.get("/api/projects").status_code == 401
        assert client.get("/api/approvals").status_code == 401
        assert client.get("/api/settings").status_code == 401
        assert client.post("/api/projects", json={}).status_code == 401

    def test_wrong_api_key_rejected(self, client):
        """A request with an incorrect API key must be rejected with 401."""
        assert (
            client.get("/api/projects", headers={"X-API-Key": "wrong"}).status_code
            == 401
        )

    def test_health_no_auth(self, client):
        """The /health endpoint must be accessible without authentication."""
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Project list and detail
# ---------------------------------------------------------------------------


class TestProjectsList:
    def test_get_projects_returns_list(self, client, db, api_headers):
        """GET /api/projects returns a JSON list with at least one project."""
        c = make_client(db)
        make_project(db, c.id)
        r = client.get("/api/projects", headers=api_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        assert len(r.json()) >= 1

    def test_cancelled_projects_excluded(self, client, db, api_headers):
        """Cancelled projects must not appear in the default project list."""
        c = make_client(db)
        p = make_project(db, c.id, overrides={"status": "cancelled"})
        r = client.get("/api/projects", headers=api_headers)
        ids = [proj["id"] for proj in r.json()]
        assert p.id not in ids

    def test_get_project_includes_tasks_and_gates(self, client, db, api_headers):
        """GET /api/projects/{id} must include non-empty tasks and gates arrays."""
        c = make_client(db)
        p = make_project(db, c.id)
        make_agent_task(db, p.id, "content_agent", 1)
        make_approval_gate(db, p.id, "content_review", 1)
        r = client.get(f"/api/projects/{p.id}", headers=api_headers)
        assert r.status_code == 200
        data = r.json()
        assert "tasks" in data
        assert "gates" in data
        assert len(data["tasks"]) == 1
        assert len(data["gates"]) == 1

    def test_get_nonexistent_project_returns_404(self, client, api_headers):
        """GET /api/projects/{id} for a missing project must return 404."""
        r = client.get("/api/projects/99999", headers=api_headers)
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Project delete (soft cancel)
# ---------------------------------------------------------------------------


class TestProjectDelete:
    def test_delete_sets_cancelled_status(self, client, db, api_headers):
        """DELETE /api/projects/{id} must set the project status to 'cancelled'."""
        c = make_client(db)
        p = make_project(db, c.id)
        r = client.delete(f"/api/projects/{p.id}", headers=api_headers)
        assert r.status_code == 200
        db.refresh(p)
        assert p.status == "cancelled"

    def test_delete_does_not_remove_from_db(self, client, db, api_headers):
        """A cancelled project must still be retrievable from the database."""
        c = make_client(db)
        p = make_project(db, c.id)
        client.delete(f"/api/projects/{p.id}", headers=api_headers)
        assert db.get(Project, p.id) is not None

    def test_delete_cascades_tasks(self, client, db, api_headers):
        """Hard-deleting a project via ORM must cascade-delete child tasks."""
        c = make_client(db)
        p = make_project(db, c.id)
        t = make_agent_task(db, p.id, "content_agent")
        task_id = t.id
        # Use ORM delete (not the API's soft-cancel) to test the DB cascade
        db.delete(p)
        db.commit()
        assert db.get(AgentTask, task_id) is None

    def test_delete_cascades_gates(self, client, db, api_headers):
        """Hard-deleting a project via ORM must cascade-delete child gates."""
        c = make_client(db)
        p = make_project(db, c.id)
        g = make_approval_gate(db, p.id, "content_review")
        gate_id = g.id
        db.delete(p)
        db.commit()
        assert db.get(ApprovalGate, gate_id) is None

    def test_delete_nonexistent_project_returns_404(self, client, api_headers):
        """DELETE /api/projects/{id} for a missing project must return 404."""
        r = client.delete("/api/projects/99999", headers=api_headers)
        assert r.status_code == 404

    def test_delete_already_cancelled_is_idempotent(self, client, db, api_headers):
        """Deleting a project that is already cancelled must return 200."""
        c = make_client(db)
        p = make_project(db, c.id, overrides={"status": "cancelled"})
        r = client.delete(f"/api/projects/{p.id}", headers=api_headers)
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Content routes
# ---------------------------------------------------------------------------


class TestContentRoutes:
    def test_patch_content_valid_data(self, client, db, api_headers):
        """PATCH /api/content/{id} with a valid title must return 200."""
        c = make_client(db)
        p = make_project(db, c.id)
        content = make_generated_content(db, p.id, "home")
        r = client.patch(
            f"/api/content/{content.id}",
            json={"title": "Updated Title"},
            headers=api_headers,
        )
        assert r.status_code == 200
        assert r.json()["title"] == "Updated Title"

    def test_patch_meta_title_over_60_rejected(self, client, db, api_headers):
        """PATCH /api/content/{id} with meta_title > 60 chars must return 422."""
        c = make_client(db)
        p = make_project(db, c.id)
        content = make_generated_content(db, p.id, "home")
        r = client.patch(
            f"/api/content/{content.id}",
            json={"meta_title": "A" * 61},
            headers=api_headers,
        )
        assert r.status_code == 422

    def test_patch_meta_description_over_160_rejected(self, client, db, api_headers):
        """PATCH /api/content/{id} with meta_description > 160 chars must return 422."""
        c = make_client(db)
        p = make_project(db, c.id)
        content = make_generated_content(db, p.id, "home")
        r = client.patch(
            f"/api/content/{content.id}",
            json={"meta_description": "A" * 161},
            headers=api_headers,
        )
        assert r.status_code == 422

    def test_patch_meta_title_exactly_60_accepted(self, client, db, api_headers):
        """PATCH /api/content/{id} with meta_title == 60 chars must return 200."""
        c = make_client(db)
        p = make_project(db, c.id)
        content = make_generated_content(db, p.id, "home")
        r = client.patch(
            f"/api/content/{content.id}",
            json={"meta_title": "A" * 60},
            headers=api_headers,
        )
        assert r.status_code == 200

    def test_patch_meta_description_exactly_160_accepted(self, client, db, api_headers):
        """PATCH /api/content/{id} with meta_description == 160 chars must return 200."""
        c = make_client(db)
        p = make_project(db, c.id)
        content = make_generated_content(db, p.id, "home")
        r = client.patch(
            f"/api/content/{content.id}",
            json={"meta_description": "B" * 160},
            headers=api_headers,
        )
        assert r.status_code == 200

    def test_patch_resets_approved_gate_to_pending(self, client, db, api_headers):
        """Editing content must reset an already-approved content_review gate to pending."""
        c = make_client(db)
        p = make_project(db, c.id)
        content = make_generated_content(db, p.id, "home")
        gate = make_approval_gate(
            db, p.id, "content_review", overrides={"status": "approved"}
        )
        r = client.patch(
            f"/api/content/{content.id}",
            json={"title": "Changed"},
            headers=api_headers,
        )
        assert r.status_code == 200
        db.refresh(gate)
        assert gate.status == "pending"

    def test_patch_does_not_reset_non_content_review_gate(self, client, db, api_headers):
        """Editing content must not reset a site_review gate."""
        c = make_client(db)
        p = make_project(db, c.id)
        content = make_generated_content(db, p.id, "home")
        gate = make_approval_gate(
            db, p.id, "site_review", overrides={"status": "approved"}
        )
        r = client.patch(
            f"/api/content/{content.id}",
            json={"title": "Changed"},
            headers=api_headers,
        )
        assert r.status_code == 200
        db.refresh(gate)
        # site_review gate should remain approved
        assert gate.status == "approved"

    def test_approve_content_piece(self, client, db, api_headers):
        """POST /api/content/{id}/approve must mark the piece as approved."""
        c = make_client(db)
        p = make_project(db, c.id)
        content = make_generated_content(db, p.id, "home")
        r = client.post(f"/api/content/{content.id}/approve", headers=api_headers)
        assert r.status_code == 200
        db.refresh(content)
        assert content.status == "approved"

    def test_approve_content_piece_response_status(self, client, db, api_headers):
        """POST /api/content/{id}/approve response body must show status 'approved'."""
        c = make_client(db)
        p = make_project(db, c.id)
        content = make_generated_content(db, p.id, "home")
        r = client.post(f"/api/content/{content.id}/approve", headers=api_headers)
        assert r.status_code == 200
        assert r.json()["status"] == "approved"

    def test_bulk_approve_content(self, client, db, api_headers):
        """POST /api/content/project/{id}/approve-all must approve all draft pieces."""
        c = make_client(db)
        p = make_project(db, c.id)
        c1 = make_generated_content(db, p.id, "home")
        c2 = make_generated_content(db, p.id, "about")
        r = client.post(
            f"/api/content/project/{p.id}/approve-all", headers=api_headers
        )
        assert r.status_code == 200
        db.refresh(c1)
        db.refresh(c2)
        assert c1.status == "approved"
        assert c2.status == "approved"

    def test_bulk_approve_returns_count(self, client, db, api_headers):
        """Bulk approve response must include the number of pieces approved."""
        c = make_client(db)
        p = make_project(db, c.id)
        make_generated_content(db, p.id, "home")
        make_generated_content(db, p.id, "about")
        r = client.post(
            f"/api/content/project/{p.id}/approve-all", headers=api_headers
        )
        assert r.status_code == 200
        data = r.json()
        assert data.get("approved_count") == 2

    def test_get_content_for_project(self, client, db, api_headers):
        """GET /api/content/project/{id} must list all content pieces for the project."""
        c = make_client(db)
        p = make_project(db, c.id)
        make_generated_content(db, p.id, "home")
        make_generated_content(db, p.id, "about")
        r = client.get(f"/api/content/project/{p.id}", headers=api_headers)
        assert r.status_code == 200
        assert len(r.json()) == 2


# ---------------------------------------------------------------------------
# Approval routes
# ---------------------------------------------------------------------------


class TestApprovalRoutes:
    def test_list_approvals_returns_pending_only(self, client, db, api_headers):
        """GET /api/approvals must return only pending gates, not approved ones."""
        c = make_client(db)
        p = make_project(db, c.id)
        pending = make_approval_gate(
            db, p.id, "content_review", overrides={"status": "pending"}
        )
        approved = make_approval_gate(
            db, p.id, "site_review", overrides={"status": "approved"}
        )
        r = client.get("/api/approvals", headers=api_headers)
        assert r.status_code == 200
        ids = [g["id"] for g in r.json()]
        assert pending.id in ids
        assert approved.id not in ids

    def test_approve_gate(self, client, db, api_headers):
        """POST /api/approvals/{id}/approve must set status to approved."""
        c = make_client(db)
        p = make_project(db, c.id)
        gate = make_approval_gate(db, p.id, "content_review")
        r = client.post(
            f"/api/approvals/{gate.id}/approve",
            json={"reviewed_by": "test_operator"},
            headers=api_headers,
        )
        assert r.status_code == 200
        db.refresh(gate)
        assert gate.status == "approved"
        assert gate.reviewed_by == "test_operator"
        assert gate.reviewed_at is not None

    def test_approve_gate_idempotent(self, client, db, api_headers):
        """Approving a gate twice must return 200 both times without error."""
        c = make_client(db)
        p = make_project(db, c.id)
        gate = make_approval_gate(db, p.id, "content_review")
        r1 = client.post(
            f"/api/approvals/{gate.id}/approve",
            json={"reviewed_by": "op"},
            headers=api_headers,
        )
        r2 = client.post(
            f"/api/approvals/{gate.id}/approve",
            json={"reviewed_by": "op"},
            headers=api_headers,
        )
        assert r1.status_code == 200
        assert r2.status_code == 200

    def test_reject_requires_notes(self, client, db, api_headers):
        """POST /api/approvals/{id}/reject with empty notes must return 422."""
        c = make_client(db)
        p = make_project(db, c.id)
        gate = make_approval_gate(db, p.id, "content_review")
        r = client.post(
            f"/api/approvals/{gate.id}/reject",
            json={"notes": "", "reviewed_by": "op"},
            headers=api_headers,
        )
        assert r.status_code == 422

    def test_reject_with_notes_succeeds(self, client, db, api_headers):
        """POST /api/approvals/{id}/reject with notes must set status to rejected."""
        c = make_client(db)
        p = make_project(db, c.id)
        gate = make_approval_gate(db, p.id, "content_review")
        r = client.post(
            f"/api/approvals/{gate.id}/reject",
            json={"notes": "Content needs revision", "reviewed_by": "op"},
            headers=api_headers,
        )
        assert r.status_code == 200
        db.refresh(gate)
        assert gate.status == "rejected"
        assert gate.notes == "Content needs revision"

    def test_approve_nonexistent_gate_404(self, client, api_headers):
        """POST /api/approvals/99999/approve must return 404."""
        r = client.post(
            "/api/approvals/99999/approve",
            json={"reviewed_by": "op"},
            headers=api_headers,
        )
        assert r.status_code == 404

    def test_approve_gate_on_cancelled_project_fails(self, client, db, api_headers):
        """Approving a gate on a cancelled project must return 400 or 422."""
        c = make_client(db)
        p = make_project(db, c.id, overrides={"status": "cancelled"})
        gate = make_approval_gate(db, p.id, "content_review")
        r = client.post(
            f"/api/approvals/{gate.id}/approve",
            json={"reviewed_by": "op"},
            headers=api_headers,
        )
        assert r.status_code in (400, 422)

    def test_reject_nonexistent_gate_404(self, client, api_headers):
        """POST /api/approvals/99999/reject must return 404."""
        r = client.post(
            "/api/approvals/99999/reject",
            json={"notes": "Some notes", "reviewed_by": "op"},
            headers=api_headers,
        )
        assert r.status_code == 404

    def test_rejected_gate_cannot_be_approved(self, client, db, api_headers):
        """A rejected gate must not be re-approved — must return 400."""
        c = make_client(db)
        p = make_project(db, c.id)
        gate = make_approval_gate(
            db, p.id, "content_review", overrides={"status": "rejected"}
        )
        r = client.post(
            f"/api/approvals/{gate.id}/approve",
            json={"reviewed_by": "op"},
            headers=api_headers,
        )
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# Database integrity
# ---------------------------------------------------------------------------


class TestDatabaseIntegrity:
    def test_create_project_with_nonexistent_client_returns_error(
        self, client, db, api_headers
    ):
        """POST /api/projects with a non-existent client_id must return 404."""
        r = client.post(
            "/api/projects",
            json={"client_id": 99999, "brief": {"what_does_business_do": "Test"}},
            headers=api_headers,
        )
        assert r.status_code in (400, 404, 422)

    def test_delete_project_cascades_tasks_and_gates(self, client, db, api_headers):
        """Hard-deleting a project via ORM removes all child tasks and gates."""
        c = make_client(db)
        p = make_project(db, c.id)
        t = make_agent_task(db, p.id, "content_agent")
        g = make_approval_gate(db, p.id, "content_review")
        task_id = t.id
        gate_id = g.id
        db.delete(p)
        db.commit()
        assert db.get(AgentTask, task_id) is None
        assert db.get(ApprovalGate, gate_id) is None


# ---------------------------------------------------------------------------
# Credential encryption
# ---------------------------------------------------------------------------


class TestCredentialEncryption:
    def test_access_token_not_stored_plaintext(self, db):
        """The Shopify access token must not be stored as plaintext in the DB column."""
        c = make_client(db)
        cred = make_credentials(db, c.id, "shopify")
        result = db.execute(
            text(
                "SELECT access_token_encrypted FROM platform_credentials WHERE id = :id"
            ),
            {"id": cred.id},
        ).scalar()
        assert result is not None
        assert result != "shpat_test_access_token_123"

    def test_decrypted_access_token_matches_original(self, db):
        """The decrypted access_token property must match the value that was stored."""
        c = make_client(db)
        cred = make_credentials(db, c.id, "shopify")
        assert cred.access_token == "shpat_test_access_token_123"

    def test_wp_app_password_roundtrip(self, db):
        """The decrypted app_password property must match the value that was stored."""
        c = make_client(db)
        cred = make_credentials(db, c.id, "wordpress")
        assert cred.app_password == "test_app_password_123"

    def test_app_password_not_stored_plaintext(self, db):
        """The WordPress app password must not be stored as plaintext in the DB column."""
        c = make_client(db)
        cred = make_credentials(db, c.id, "wordpress")
        result = db.execute(
            text(
                "SELECT app_password_encrypted FROM platform_credentials WHERE id = :id"
            ),
            {"id": cred.id},
        ).scalar()
        assert result is not None
        assert result != "test_app_password_123"

    def test_null_access_token_returns_none(self, db):
        """A credential with no access token set must return None from the property."""
        from backend.db.models import PlatformCredential

        c = make_client(db)
        cred = PlatformCredential(
            client_id=c.id,
            platform="shopify",
            site_url="https://test.myshopify.com",
        )
        db.add(cred)
        db.commit()
        db.refresh(cred)
        assert cred.access_token is None
