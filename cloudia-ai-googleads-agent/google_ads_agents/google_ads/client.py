"""GoogleAdsClient wrapper. All API calls go through here — never directly from agents."""

import logging
from typing import Any

from google.ads.googleads.client import GoogleAdsClient as _GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

import config

logger = logging.getLogger(__name__)


class AdsClient:
    """Thin wrapper around the official Google Ads Python client.

    Centralises authentication and provides a consistent interface for running
    GAQL queries and mutating resources.
    """

    def __init__(self) -> None:
        credentials = {
            "developer_token": config.GOOGLE_ADS_DEVELOPER_TOKEN,
            "client_id": config.GOOGLE_ADS_CLIENT_ID,
            "client_secret": config.GOOGLE_ADS_CLIENT_SECRET,
            "refresh_token": config.GOOGLE_ADS_REFRESH_TOKEN,
            "login_customer_id": config.GOOGLE_ADS_LOGIN_CUSTOMER_ID,
            "use_proto_plus": True,
        }
        self._client = _GoogleAdsClient.load_from_dict(credentials)
        logger.info("GoogleAdsClient initialised (MCC: %s)", config.GOOGLE_ADS_LOGIN_CUSTOMER_ID)

    def run_query(self, customer_id: str, query: str) -> list[Any]:
        """Execute a GAQL query and return all rows as a list.

        Args:
            customer_id: The Google Ads customer ID (without dashes).
            query: A GAQL query string from google_ads/queries.py.

        Returns:
            List of GoogleAdsRow proto-plus objects.

        Raises:
            GoogleAdsException: On API error with full error details logged.
        """
        service = self._client.get_service("GoogleAdsService")
        try:
            response = service.search_stream(customer_id=customer_id, query=query)
            rows: list[Any] = []
            for batch in response:
                rows.extend(batch.results)
            logger.debug(
                "Query returned %d rows for customer %s", len(rows), customer_id
            )
            return rows
        except GoogleAdsException as exc:
            for error in exc.failure.errors:
                logger.error(
                    "Google Ads API error [%s]: %s",
                    error.error_code,
                    error.message,
                )
            raise

    def get_service(self, service_name: str) -> Any:
        """Return a named Google Ads service client for mutation operations."""
        return self._client.get_service(service_name)

    def get_type(self, type_name: str) -> Any:
        """Return a named Google Ads proto-plus type for building requests."""
        return self._client.get_type(type_name)

    @property
    def enums(self) -> Any:
        """Access Google Ads enum types."""
        return self._client.enums
