"""
Unit and integration tests for the ApprovalGate model and its behaviour
within the CloudIA pipeline.

Covers:
  - Default field values on creation
  - Foreign key enforcement (project_id must reference a real project)
  - Cascade delete when the parent project is removed
  - Pipeline ordering constraints between content_review and site_review
  - Status transition mechanics (the DB layer is permissive; the app layer enforces order)
"""

import pytest
from tests.factories import (
    make_client,
    make_project,
    make_approval_gate,
    make_agent_task,
)
from backend.db.models import ApprovalGate, Project


# ---------------------------------------------------------------------------
# Model defaults and constraints
# ---------------------------------------------------------------------------


class TestApprovalGateModel:
    def test_gate_created_with_pending_status(self, db):
        """A freshly created ApprovalGate must default to 'pending'."""
        c = make_client(db)
        p = make_project(db, c.id)
        gate = make_approval_gate(db, p.id, "content_review")
        assert gate.status == "pending"
        assert gate.reviewed_at is None
        assert gate.reviewed_by is None

    def test_gate_has_correct_gate_name(self, db):
        """gate_name must be stored exactly as provided."""
        c = make_client(db)
        p = make_project(db, c.id)
        gate = make_approval_gate(db, p.id, "site_review")
        assert gate.gate_name == "site_review"

    def test_gate_has_correct_project_id(self, db):
        """project_id on the gate must match the parent project."""
        c = make_client(db)
        p = make_project(db, c.id)
        gate = make_approval_gate(db, p.id, "content_review")
        assert gate.project_id == p.id

    def test_gate_created_at_is_set(self, db):
        """created_at must be populated automatically on creation."""
        c = make_client(db)
        p = make_project(db, c.id)
        gate = make_approval_gate(db, p.id, "content_review")
        assert gate.created_at is not None

    def test_gate_notes_defaults_to_none(self, db):
        """notes must default to None when not set."""
        c = make_client(db)
        p = make_project(db, c.id)
        gate = make_approval_gate(db, p.id, "content_review")
        assert gate.notes is None

    def test_gate_foreign_key_enforced(self, db):
        """Inserting a gate with a non-existent project_id must raise an error."""
        gate = ApprovalGate(
            project_id=99999,
            gate_name="content_review",
            status="pending",
        )
        db.add(gate)
        with pytest.raises(Exception):
            db.commit()
        db.rollback()

    def test_cascade_delete_on_project_delete(self, db):
        """Deleting a project must cascade-delete all its approval gates."""
        c = make_client(db)
        p = make_project(db, c.id)
        gate = make_approval_gate(db, p.id, "content_review")
        gate_id = gate.id
        db.delete(p)
        db.commit()
        assert db.get(ApprovalGate, gate_id) is None

    def test_multiple_gates_cascade_on_project_delete(self, db):
        """All gates for a project must be removed when the project is deleted."""
        c = make_client(db)
        p = make_project(db, c.id)
        g1 = make_approval_gate(db, p.id, "content_review", pipeline_order=1)
        g2 = make_approval_gate(db, p.id, "site_review", pipeline_order=2)
        g1_id, g2_id = g1.id, g2.id
        db.delete(p)
        db.commit()
        assert db.get(ApprovalGate, g1_id) is None
        assert db.get(ApprovalGate, g2_id) is None

    def test_gate_override_status_on_creation(self, db):
        """make_approval_gate with a status override must persist the provided status."""
        c = make_client(db)
        p = make_project(db, c.id)
        gate = make_approval_gate(
            db, p.id, "content_review", overrides={"status": "approved"}
        )
        assert gate.status == "approved"


# ---------------------------------------------------------------------------
# Pipeline ordering
# ---------------------------------------------------------------------------


class TestApprovalGateOrdering:
    def test_content_review_pipeline_order_before_site_review(self, db):
        """content_review gate must be assigned a lower pipeline_order than site_review."""
        c = make_client(db)
        p = make_project(db, c.id)
        content_gate = make_approval_gate(
            db, p.id, "content_review", pipeline_order=1
        )
        site_gate = make_approval_gate(
            db, p.id, "site_review", pipeline_order=2
        )
        assert content_gate.pipeline_order < site_gate.pipeline_order

    def test_gate_status_transitions_approved(self, db):
        """Gate status can be changed to 'approved' and persisted."""
        c = make_client(db)
        p = make_project(db, c.id)
        gate = make_approval_gate(db, p.id, "content_review")

        gate.status = "approved"
        db.commit()
        db.refresh(gate)
        assert gate.status == "approved"

    def test_gate_status_transition_back_to_pending(self, db):
        """Gate status can be reset to 'pending' at the DB layer (app layer enforces business rules)."""
        c = make_client(db)
        p = make_project(db, c.id)
        gate = make_approval_gate(
            db, p.id, "content_review", overrides={"status": "approved"}
        )
        gate.status = "pending"
        db.commit()
        db.refresh(gate)
        # The DB column accepts any status value — the application layer enforces ordering
        assert gate.status == "pending"

    def test_gate_status_transition_to_rejected(self, db):
        """Gate status can be set to 'rejected' and persisted."""
        c = make_client(db)
        p = make_project(db, c.id)
        gate = make_approval_gate(db, p.id, "content_review")
        gate.status = "rejected"
        gate.notes = "The logo colours are incorrect."
        gate.reviewed_by = "test_operator"
        db.commit()
        db.refresh(gate)
        assert gate.status == "rejected"
        assert gate.notes == "The logo colours are incorrect."

    def test_reviewed_by_and_reviewed_at_stored(self, db):
        """reviewed_by and reviewed_at must be persisted when set."""
        import datetime

        c = make_client(db)
        p = make_project(db, c.id)
        gate = make_approval_gate(db, p.id, "content_review")
        now = datetime.datetime.utcnow()
        gate.reviewed_by = "admin@cloudia.ai"
        gate.reviewed_at = now
        gate.status = "approved"
        db.commit()
        db.refresh(gate)
        assert gate.reviewed_by == "admin@cloudia.ai"
        assert gate.reviewed_at is not None


# ---------------------------------------------------------------------------
# Multiple gates per project
# ---------------------------------------------------------------------------


class TestMultipleGatesPerProject:
    def test_project_can_have_multiple_gates(self, db):
        """A project may have both a content_review and a site_review gate."""
        c = make_client(db)
        p = make_project(db, c.id)
        g1 = make_approval_gate(db, p.id, "content_review", pipeline_order=1)
        g2 = make_approval_gate(db, p.id, "site_review", pipeline_order=2)
        db.refresh(p)
        gate_ids = {g.id for g in p.approval_gates}
        assert g1.id in gate_ids
        assert g2.id in gate_ids

    def test_gates_are_independent_per_project(self, db):
        """Gates for one project must not appear on a different project."""
        c = make_client(db)
        p1 = make_project(db, c.id)
        p2 = make_project(
            db,
            c.id,
            overrides={
                "brief": {
                    "what_does_business_do": "Second project",
                },
            },
        )
        gate1 = make_approval_gate(db, p1.id, "content_review")
        gate2 = make_approval_gate(db, p2.id, "content_review")
        assert gate1.project_id == p1.id
        assert gate2.project_id == p2.id
        assert gate1.id != gate2.id

    def test_agent_task_linked_to_same_project_as_gate(self, db):
        """Both gates and tasks for a project share the same project_id."""
        c = make_client(db)
        p = make_project(db, c.id)
        gate = make_approval_gate(db, p.id, "content_review", pipeline_order=2)
        task = make_agent_task(db, p.id, "content_agent", pipeline_order=1)
        assert gate.project_id == p.id
        assert task.project_id == p.id
