"""
Tests for the Shopify platform client and ShopifyBuilderAgent.

Covers:
  - Rate limiting: _throttle() must enforce 500 ms between requests
  - Product validation: R0 price must be blocked
  - Authentication: invalid token raises ShopifyAuthError
  - MockShopifyClient call recording
  - R0 price blocking the store_review gate (xfail — requires full integration)
"""

import pytest
import time
from unittest.mock import patch, MagicMock
from tests.factories import (
    make_client,
    make_project,
    make_agent_task,
    make_generated_content,
    make_credentials,
)
from backend.platforms.shopify.client import (
    ShopifyAuthError,
    ShopifyAPIError,
    ShopifyServerError,
    ShopifyPlanError,
)
from backend.db.models import ApprovalGate


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------


class TestRateLimiting:
    def test_throttle_enforces_minimum_interval(self):
        """ShopifyClient._throttle() must wait ~500 ms when called in rapid succession."""
        from backend.platforms.shopify.client import ShopifyClient

        client = ShopifyClient.__new__(ShopifyClient)
        client._min_interval = 0.5
        # Set _last_request_time to "just now" so that _throttle must sleep
        client._last_request_time = time.time()

        start = time.time()
        client._throttle()
        elapsed = time.time() - start

        # Must have waited close to 0.5 s (allow 50 ms tolerance on either side)
        assert elapsed >= 0.4

    def test_throttle_no_wait_when_interval_elapsed(self):
        """_throttle() must not sleep when the minimum interval has already elapsed."""
        from backend.platforms.shopify.client import ShopifyClient

        client = ShopifyClient.__new__(ShopifyClient)
        client._min_interval = 0.5
        # Set _last_request_time far in the past so no wait is required
        client._last_request_time = time.time() - 1.0

        start = time.time()
        client._throttle()
        elapsed = time.time() - start

        # Should complete in well under 100 ms
        assert elapsed < 0.1

    def test_throttle_updates_last_request_time(self):
        """_throttle() must update _last_request_time after execution."""
        from backend.platforms.shopify.client import ShopifyClient

        client = ShopifyClient.__new__(ShopifyClient)
        client._min_interval = 0.0
        client._last_request_time = 0.0

        before = time.time()
        client._throttle()
        after = time.time()

        assert before <= client._last_request_time <= after


# ---------------------------------------------------------------------------
# Product validation — R0 price
# ---------------------------------------------------------------------------


class TestProductValidation:
    def test_r0_price_blocked(self):
        """MockShopifyClient.create_product must raise on price='0'."""
        from tests.mocks.mock_shopify import MockShopifyClient

        client = MockShopifyClient()
        with pytest.raises((ValueError, Exception)):
            client.create_product("Test Product", "Description", "0")

    def test_r0_price_float_zero_blocked(self):
        """Price 0.00 (as string) must also be rejected."""
        from tests.mocks.mock_shopify import MockShopifyClient

        client = MockShopifyClient()
        with pytest.raises((ValueError, Exception)):
            client.create_product("Test Product", "Description", "0.00")

    def test_valid_price_accepted(self):
        """A non-zero price must be accepted and return a product dict with an id."""
        from tests.mocks.mock_shopify import MockShopifyClient

        client = MockShopifyClient()
        result = client.create_product("Test Product", "Description", "299.99")
        assert result is not None
        assert result["id"] is not None

    def test_valid_price_integer_string_accepted(self):
        """Price '100' (integer string) must be accepted."""
        from tests.mocks.mock_shopify import MockShopifyClient

        client = MockShopifyClient()
        result = client.create_product("Dental Kit", "Kit description", "100")
        assert result["title"] == "Dental Kit"

    def test_create_product_records_call(self):
        """create_product must record the call in MockShopifyClient.calls."""
        from tests.mocks.mock_shopify import MockShopifyClient

        client = MockShopifyClient()
        client.create_product("Widget", "A widget", "49.99")
        assert any(c[0] == "create_product" for c in client.calls)

    def test_create_product_response_has_status_active(self):
        """Successful create_product must return status='active'."""
        from tests.mocks.mock_shopify import MockShopifyClient

        client = MockShopifyClient()
        result = client.create_product("Widget", "A widget", "49.99")
        assert result["status"] == "active"

    def test_create_product_response_has_variants_with_price(self):
        """create_product response must contain a variants list with the correct price."""
        from tests.mocks.mock_shopify import MockShopifyClient

        client = MockShopifyClient()
        result = client.create_product("Widget", "A widget", "149.00")
        assert result["variants"][0]["price"] == "149.00"


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


class TestShopifyAuthentication:
    def test_invalid_token_raises_auth_error(self):
        """MockShopifyClient with auth_fail=True must raise ShopifyAuthError on get_shop_info."""
        from tests.mocks.mock_shopify import MockShopifyClient

        client = MockShopifyClient(auth_fail=True)
        with pytest.raises(ShopifyAuthError):
            client.get_shop_info()

    def test_valid_token_returns_shop_info(self):
        """A successful get_shop_info call must return a dict with 'name' and 'domain'."""
        from tests.mocks.mock_shopify import MockShopifyClient

        client = MockShopifyClient()
        info = client.get_shop_info()
        assert "name" in info
        assert "domain" in info

    def test_get_shop_info_records_call(self):
        """get_shop_info must appear in MockShopifyClient.calls."""
        from tests.mocks.mock_shopify import MockShopifyClient

        client = MockShopifyClient()
        client.get_shop_info()
        assert any(c[0] == "get_shop_info" for c in client.calls)


# ---------------------------------------------------------------------------
# Rate limit simulation
# ---------------------------------------------------------------------------


class TestRateLimitSimulation:
    def test_rate_limited_mock_raises_api_error_on_first_call(self):
        """MockShopifyClient with rate_limited=True must raise ShopifyAPIError on first create."""
        from tests.mocks.mock_shopify import MockShopifyClient

        client = MockShopifyClient(rate_limited=True)
        with pytest.raises(ShopifyAPIError):
            client.create_product("Widget", "Desc", "99.99")

    def test_rate_limited_mock_succeeds_on_second_call(self):
        """After the first rate-limit error, a second call must succeed."""
        from tests.mocks.mock_shopify import MockShopifyClient

        client = MockShopifyClient(rate_limited=True)
        try:
            client.create_product("Widget", "Desc", "99.99")
        except ShopifyAPIError:
            pass
        # Second call should succeed
        result = client.create_product("Widget", "Desc", "99.99")
        assert result is not None


# ---------------------------------------------------------------------------
# Plan error
# ---------------------------------------------------------------------------


class TestPlanError:
    def test_plan_error_raised_on_create_menu(self):
        """MockShopifyClient with plan_error=True must raise ShopifyPlanError on create_menu."""
        from tests.mocks.mock_shopify import MockShopifyClient

        client = MockShopifyClient(plan_error=True)
        with pytest.raises(ShopifyPlanError):
            client.create_menu("Main Navigation", "main-menu")


# ---------------------------------------------------------------------------
# Collection and page helpers
# ---------------------------------------------------------------------------


class TestCollectionAndPageHelpers:
    def test_create_collection_returns_dict_with_id(self):
        """create_collection must return a dict with 'id' and 'title'."""
        from tests.mocks.mock_shopify import MockShopifyClient

        client = MockShopifyClient()
        result = client.create_collection("All Products", "Browse our full range")
        assert "id" in result
        assert result["title"] == "All Products"

    def test_create_page_returns_dict_with_handle(self):
        """create_page must return a dict with 'id' and 'handle'."""
        from tests.mocks.mock_shopify import MockShopifyClient

        client = MockShopifyClient()
        result = client.create_page("About Us", "<p>About body</p>", "about-us")
        assert "id" in result
        assert result["handle"] == "about-us"

    def test_context_manager_calls_close(self):
        """Using MockShopifyClient as a context manager must call close() on exit."""
        from tests.mocks.mock_shopify import MockShopifyClient

        client = MockShopifyClient()
        with client:
            pass
        assert any(c[0] == "close" for c in client.calls)


# ---------------------------------------------------------------------------
# ShopifyBuilderAgent integration (xfail — requires full integration)
# ---------------------------------------------------------------------------


class TestShopifyBuilderIntegration:
    @pytest.mark.xfail(
        reason="ShopifyBuilderAgent requires full integration"
    )
    def test_r0_price_blocks_store_review_gate(self, db):
        """Builder must not create a store_review gate if any product has R0 price."""
        c = make_client(db)
        p = make_project(
            db,
            c.id,
            platform="shopify",
            overrides={
                "pipeline_plan": {
                    "collections": [{"name": "All Products", "description": ""}],
                    "products": [
                        {
                            "title": "Broken Product",
                            "price": "0",
                            "description": "Test product",
                        }
                    ],
                }
            },
        )
        t = make_agent_task(db, p.id, "shopify_builder_agent", 4)
        make_credentials(db, c.id, "shopify")

        from tests.mocks.mock_shopify import MockShopifyClient

        mock_shopify = MockShopifyClient()

        with patch(
            "backend.platforms.shopify.client.ShopifyClient",
            return_value=mock_shopify,
        ):
            from backend.agents.shopify.builder_agent import ShopifyBuilderAgent

            agent = ShopifyBuilderAgent(project_id=p.id, task_id=t.id)
            with pytest.raises(Exception):
                agent.execute()

        gates = (
            db.query(ApprovalGate)
            .filter_by(project_id=p.id, gate_name="store_review")
            .all()
        )
        assert len(gates) == 0

    @pytest.mark.xfail(reason="ShopifyBuilderAgent requires full integration")
    def test_successful_build_creates_store_review_gate(self, db):
        """A successful Shopify build must create a store_review approval gate."""
        c = make_client(db)
        p = make_project(
            db,
            c.id,
            platform="shopify",
            overrides={
                "pipeline_plan": {
                    "collections": [{"name": "All Products", "description": ""}],
                    "products": [
                        {
                            "title": "Premium Widget",
                            "price": "299.99",
                            "description": "A premium widget.",
                        }
                    ],
                }
            },
        )
        t = make_agent_task(db, p.id, "shopify_builder_agent", 4)
        make_credentials(db, c.id, "shopify")

        from tests.mocks.mock_shopify import MockShopifyClient

        mock_shopify = MockShopifyClient()

        with patch(
            "backend.platforms.shopify.client.ShopifyClient",
            return_value=mock_shopify,
        ):
            from backend.agents.shopify.builder_agent import ShopifyBuilderAgent

            agent = ShopifyBuilderAgent(project_id=p.id, task_id=t.id)
            agent.execute()

        gates = (
            db.query(ApprovalGate)
            .filter_by(project_id=p.id, gate_name="store_review")
            .all()
        )
        assert len(gates) == 1
        assert gates[0].status == "pending"
