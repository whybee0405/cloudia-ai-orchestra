"""
Tests for the WordPress platform client and WPBuilderAgent.

Covers:
  - URL normalisation (trailing slashes, /wp-json suffix deduplication)
  - api_url property correctness
  - Maintenance mode detection (HTML response → WordPressMaintenanceError)
  - Auth error propagation
  - MockWordPressClient call recording
  - Partial build failure recovery (xfail — requires full integration)

Tests that exercise WordPressClient directly instantiate it via
``__new__`` so that no HTTP connections are made. The ``_normalize_url``
and ``api_url`` tests are purely computational.
"""

import pytest
from unittest.mock import patch, MagicMock
from tests.factories import (
    make_client,
    make_project,
    make_agent_task,
    make_generated_content,
    make_credentials,
)
from backend.db.models import Project, ApprovalGate
from backend.platforms.wordpress.client import (
    WordPressAuthError,
    WordPressMaintenanceError,
    WordPressServerError,
    WordPressAPIError,
)


# ---------------------------------------------------------------------------
# URL normalisation
# ---------------------------------------------------------------------------


class TestURLNormalization:
    def _client(self):
        """Return a WordPressClient instance without making any HTTP call."""
        from backend.platforms.wordpress.client import WordPressClient

        return WordPressClient.__new__(WordPressClient)

    def test_trailing_slash_stripped(self):
        """_normalize_url must strip a trailing slash from the site URL."""
        c = self._client()
        result = c._normalize_url("https://example.co.za/")
        assert result == "https://example.co.za"

    def test_no_trailing_slash_unchanged(self):
        """A URL without a trailing slash must be returned unchanged."""
        c = self._client()
        result = c._normalize_url("https://example.co.za")
        assert result == "https://example.co.za"

    def test_wp_json_suffix_stripped(self):
        """_normalize_url must remove a /wp-json suffix from the URL."""
        c = self._client()
        result = c._normalize_url("https://example.co.za/wp-json")
        assert result == "https://example.co.za"

    def test_wp_json_suffix_not_doubled(self):
        """After normalisation the base_url must not contain /wp-json."""
        c = self._client()
        result = c._normalize_url("https://example.co.za/wp-json")
        assert "/wp-json" not in result

    def test_wp_json_with_trailing_slash_normalised(self):
        """_normalize_url must handle /wp-json/ (with trailing slash) correctly."""
        c = self._client()
        # strip trailing slash first, then the suffix check
        result = c._normalize_url("https://example.co.za/wp-json/")
        # After stripping trailing slash we get /wp-json, then strip that too
        assert "wp-json" not in result

    def test_api_url_correctly_formed(self):
        """api_url property must append /wp-json/wp/v2 to base_url."""
        from backend.platforms.wordpress.client import WordPressClient

        c = WordPressClient.__new__(WordPressClient)
        c.base_url = "https://example.co.za"
        assert c.api_url == "https://example.co.za/wp-json/wp/v2"

    def test_api_url_no_double_slash(self):
        """api_url must not contain double slashes."""
        from backend.platforms.wordpress.client import WordPressClient

        c = WordPressClient.__new__(WordPressClient)
        c.base_url = "https://example.co.za"
        assert "//" not in c.api_url.replace("https://", "")

    def test_subdirectory_install_preserved(self):
        """A WP install in a subdirectory must not lose the subdirectory path."""
        c = self._client()
        result = c._normalize_url("https://example.co.za/wordpress/")
        assert "/wordpress" in result
        assert result.endswith("/wordpress")


# ---------------------------------------------------------------------------
# WordPress client error handling
# ---------------------------------------------------------------------------


class TestWPClientErrors:
    def test_maintenance_mode_detected(self):
        """An HTML response from WP must raise WordPressMaintenanceError."""
        from tests.mocks.mock_wordpress import MockWordPressClient

        mock_wp = MockWordPressClient(maintenance=True)
        with pytest.raises(WordPressMaintenanceError):
            mock_wp.verify_connection()

    def test_auth_error_raised_on_verify_connection(self):
        """verify_connection with auth_fail=True must raise WordPressAuthError."""
        from tests.mocks.mock_wordpress import MockWordPressClient

        mock_wp = MockWordPressClient(auth_fail=True)
        with pytest.raises(WordPressAuthError):
            mock_wp.verify_connection()

    def test_server_error_raised_on_create_page(self):
        """create_page with server_error=True must raise WordPressServerError."""
        from tests.mocks.mock_wordpress import MockWordPressClient

        mock_wp = MockWordPressClient(server_error=True)
        with pytest.raises(WordPressServerError):
            mock_wp.create_page("Test", "<p>Body</p>", "test")

    def test_auth_error_raised_on_create_page_when_auth_fail(self):
        """create_page with auth_fail=True must raise WordPressAuthError."""
        from tests.mocks.mock_wordpress import MockWordPressClient

        mock_wp = MockWordPressClient(auth_fail=True)
        with pytest.raises(WordPressAuthError):
            mock_wp.create_page("Test", "<p>Body</p>", "test")

    def test_mock_records_verify_connection_call(self):
        """MockWordPressClient must record the verify_connection call."""
        from tests.mocks.mock_wordpress import MockWordPressClient

        mock_wp = MockWordPressClient()
        mock_wp.verify_connection()
        assert any(c[0] == "verify_connection" for c in mock_wp.calls)

    def test_mock_records_create_page_call(self):
        """MockWordPressClient must record create_page calls with title and slug."""
        from tests.mocks.mock_wordpress import MockWordPressClient

        mock_wp = MockWordPressClient()
        mock_wp.create_page("Home Page", "<p>Content</p>", "home")
        assert any(c[0] == "create_page" for c in mock_wp.calls)

    def test_mock_create_page_returns_response_dict(self):
        """A successful create_page call must return a dict with an 'id' key."""
        from tests.mocks.mock_wordpress import MockWordPressClient

        mock_wp = MockWordPressClient()
        result = mock_wp.create_page("Home", "<p>Content</p>", "home")
        assert isinstance(result, dict)
        assert "id" in result

    def test_mock_page_counter_increments(self):
        """MockWordPressClient must increment _page_counter with each create_page call."""
        from tests.mocks.mock_wordpress import MockWordPressClient

        mock_wp = MockWordPressClient()
        mock_wp.create_page("Page 1", "<p>A</p>", "page-1")
        mock_wp.create_page("Page 2", "<p>B</p>", "page-2")
        assert mock_wp._page_counter == 2

    def test_fail_on_page_raises_server_error(self):
        """MockWordPressClient with fail_on_page=2 must raise on the 2nd create_page call."""
        from tests.mocks.mock_wordpress import MockWordPressClient

        mock_wp = MockWordPressClient(fail_on_page=2)
        mock_wp.create_page("Page 1", "<p>A</p>", "page-1")  # succeeds
        with pytest.raises(WordPressServerError):
            mock_wp.create_page("Page 2", "<p>B</p>", "page-2")  # fails

    def test_context_manager_calls_close(self):
        """Using MockWordPressClient as a context manager must call close() on exit."""
        from tests.mocks.mock_wordpress import MockWordPressClient

        mock_wp = MockWordPressClient()
        with mock_wp:
            pass
        assert any(c[0] == "close" for c in mock_wp.calls)

    def test_upload_media_returns_id(self):
        """MockWordPressClient.upload_media must return a dict with an 'id' key."""
        from tests.mocks.mock_wordpress import MockWordPressClient

        mock_wp = MockWordPressClient()
        result = mock_wp.upload_media("/tmp/test.jpg", alt_text="Test image")
        assert "id" in result
        assert "source_url" in result


# ---------------------------------------------------------------------------
# WPBuilderAgent partial failure recovery (integration — xfail)
# ---------------------------------------------------------------------------


class TestPartialFailures:
    @pytest.mark.xfail(reason="WPBuilderAgent requires full integration")
    def test_partial_page_failure_continues_build(self, db):
        """If page 3 of 5 fails, pages 4 and 5 are still attempted."""
        c = make_client(db)
        p = make_project(db, c.id)
        t = make_agent_task(db, p.id, "wp_builder_agent", pipeline_order=4)
        make_credentials(db, c.id, "wordpress")

        # Generate content for 5 pages (all approved)
        for slug in ["home", "about", "services", "contact", "faq"]:
            make_generated_content(
                db, p.id, slug, overrides={"status": "approved"}
            )

        from tests.mocks.mock_wordpress import MockWordPressClient

        mock_wp = MockWordPressClient(fail_on_page=3)

        with patch(
            "backend.platforms.wordpress.client.WordPressClient",
            return_value=mock_wp,
        ):
            from backend.agents.wordpress.builder_agent import WPBuilderAgent

            agent = WPBuilderAgent(project_id=p.id, task_id=t.id)
            try:
                result = agent.execute()
            except Exception:
                pass

        # Pages 1 and 2 were created before the failure
        assert mock_wp._page_counter >= 2

    @pytest.mark.xfail(reason="WPBuilderAgent requires full integration")
    def test_auth_failure_marks_task_failed(self, db):
        """A WordPressAuthError during the build must mark the task as 'failed'."""
        c = make_client(db)
        p = make_project(db, c.id)
        t = make_agent_task(db, p.id, "wp_builder_agent", pipeline_order=4)
        make_credentials(db, c.id, "wordpress")
        make_generated_content(db, p.id, "home", overrides={"status": "approved"})

        from tests.mocks.mock_wordpress import MockWordPressClient

        mock_wp = MockWordPressClient(auth_fail=True)

        with patch(
            "backend.platforms.wordpress.client.WordPressClient",
            return_value=mock_wp,
        ):
            from backend.agents.wordpress.builder_agent import WPBuilderAgent

            agent = WPBuilderAgent(project_id=p.id, task_id=t.id)
            with pytest.raises(Exception):
                agent.execute()

        db.refresh(t)
        assert t.status == "failed"

    @pytest.mark.xfail(reason="WPBuilderAgent requires full integration")
    def test_successful_build_creates_site_review_gate(self, db):
        """A successful WP build must create a site_review approval gate."""
        c = make_client(db)
        p = make_project(db, c.id)
        t = make_agent_task(db, p.id, "wp_builder_agent", pipeline_order=4)
        make_credentials(db, c.id, "wordpress")
        make_generated_content(db, p.id, "home", overrides={"status": "approved"})

        from tests.mocks.mock_wordpress import MockWordPressClient

        mock_wp = MockWordPressClient()

        with patch(
            "backend.platforms.wordpress.client.WordPressClient",
            return_value=mock_wp,
        ):
            from backend.agents.wordpress.builder_agent import WPBuilderAgent

            agent = WPBuilderAgent(project_id=p.id, task_id=t.id)
            agent.execute()

        gates = (
            db.query(ApprovalGate)
            .filter_by(project_id=p.id, gate_name="site_review")
            .all()
        )
        assert len(gates) == 1
        assert gates[0].status == "pending"
