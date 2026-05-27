"""
Shopify QA agent for the CloudIA agent system.

Validates the built Shopify store before the store_review gate is created.
CRITICAL failures block the gate and notify the operator.
"""

import httpx
import structlog
from sqlalchemy import select

from backend.agents.base import BaseAgent
from backend.db.models import ApprovalGate, Client, PlatformCredential, Project
from backend.db.session import get_db
from backend.notifications.email import notify_task_failed
from backend.platforms.shopify.client import ShopifyClient, ShopifyAPIError

log = structlog.get_logger()


class ShopifyQAAgent(BaseAgent):
    """QA agent for Shopify stores."""

    agent_name = "shopify_qa_agent"

    def run(self) -> dict:
        checks = []
        critical_failures = []
        high_warnings = []
        medium_warnings = []

        with get_db() as db:
            project = db.get(Project, self.project_id)
            if not project:
                raise ValueError(f"Project {self.project_id} not found")
            client = db.get(Client, project.client_id)

            cred = db.execute(
                select(PlatformCredential).where(
                    PlatformCredential.client_id == project.client_id,
                    PlatformCredential.platform == "shopify",
                    PlatformCredential.is_active.is_(True),
                )
            ).scalar_one_or_none()

            if not cred:
                raise ValueError("No active Shopify credentials for QA")

            store_url = project.site_url or cred.site_url
            shop_client = ShopifyClient(
                shop_url=cred.site_url,
                access_token=cred.access_token,
                api_version=cred.api_version or "2024-01",
            )

            try:
                # 1. Products check
                products = shop_client.get_products()

                # CRITICAL: R0 price
                zero_price_products = []
                no_image_products = []
                no_description_products = []

                for product in products:
                    variants = product.get("variants", [])
                    for variant in variants:
                        price = variant.get("price", "0")
                        try:
                            if float(price) == 0.0:
                                zero_price_products.append(product.get("title", "Unknown"))
                        except (ValueError, TypeError):
                            zero_price_products.append(product.get("title", "Unknown"))

                    if not product.get("images"):
                        no_image_products.append(product.get("title", "Unknown"))

                    body = product.get("body_html", "")
                    if not body or len(body.strip()) < 10:
                        no_description_products.append(product.get("title", "Unknown"))

                if zero_price_products:
                    checks.append({
                        "name": "no_zero_price_products",
                        "severity": "CRITICAL",
                        "passed": False,
                        "detail": f"Products with R0 price: {', '.join(zero_price_products)}",
                    })
                    critical_failures.append("no_zero_price_products")
                else:
                    checks.append({"name": "no_zero_price_products", "severity": "CRITICAL", "passed": True})

                if no_image_products:
                    checks.append({
                        "name": "products_have_images",
                        "severity": "HIGH",
                        "passed": False,
                        "detail": f"Products missing images: {', '.join(no_image_products)}",
                    })
                    high_warnings.append("products_have_images")
                else:
                    checks.append({"name": "products_have_images", "severity": "HIGH", "passed": True})

                if no_description_products:
                    checks.append({
                        "name": "products_have_descriptions",
                        "severity": "HIGH",
                        "passed": False,
                        "detail": f"Products missing descriptions: {', '.join(no_description_products)}",
                    })
                    high_warnings.append("products_have_descriptions")
                else:
                    checks.append({"name": "products_have_descriptions", "severity": "HIGH", "passed": True})

                # 2. Collections check
                collections = shop_client.get_collections()
                empty_collections = []
                for col in collections:
                    # Collections without product count are medium warning (new store may have none yet)
                    count = col.get("products_count", 0)
                    if count == 0:
                        empty_collections.append(col.get("title", "Unknown"))

                if empty_collections:
                    checks.append({
                        "name": "collections_have_products",
                        "severity": "MEDIUM",
                        "passed": False,
                        "detail": f"Empty collections: {', '.join(empty_collections)}",
                    })
                    medium_warnings.append("collections_have_products")
                else:
                    checks.append({"name": "collections_have_products", "severity": "MEDIUM", "passed": True})

                # 3. Pages HTTP check
                pages = shop_client.get_pages()
                failed_pages = []
                if store_url:
                    async_client = httpx.Client(timeout=15.0, follow_redirects=True)
                    try:
                        for page in pages:
                            handle = page.get("handle", "")
                            url = f"{store_url}/pages/{handle}"
                            try:
                                resp = async_client.get(url)
                                if resp.status_code >= 400:
                                    failed_pages.append(f"{handle} ({resp.status_code})")
                            except httpx.RequestError as e:
                                failed_pages.append(f"{handle} (connection error)")
                    finally:
                        async_client.close()

                if failed_pages:
                    checks.append({
                        "name": "all_pages_accessible",
                        "severity": "CRITICAL",
                        "passed": False,
                        "detail": f"Pages returning errors: {', '.join(failed_pages)}",
                    })
                    critical_failures.append("all_pages_accessible")
                else:
                    checks.append({"name": "all_pages_accessible", "severity": "CRITICAL", "passed": True})

                # 4. Navigation check
                shop_info = shop_client.get_shop_info()

                # 5. Currency check
                currency = shop_info.get("currency", "")
                if not currency:
                    checks.append({
                        "name": "currency_set",
                        "severity": "HIGH",
                        "passed": False,
                        "detail": "Store currency not set",
                    })
                    high_warnings.append("currency_set")
                else:
                    checks.append({"name": "currency_set", "severity": "HIGH", "passed": True})
                    if currency != "ZAR":
                        checks.append({
                            "name": "currency_is_zar",
                            "severity": "MEDIUM",
                            "passed": False,
                            "detail": f"Currency is {currency}, expected ZAR for South African store",
                        })
                        medium_warnings.append("currency_is_zar")

                # 6. Checkout accessible
                if store_url:
                    try:
                        checkout_resp = httpx.get(f"{store_url}/checkout", timeout=10.0, follow_redirects=True)
                        checkout_ok = checkout_resp.status_code < 500
                    except httpx.RequestError:
                        checkout_ok = False

                    checks.append({
                        "name": "checkout_accessible",
                        "severity": "CRITICAL" if not checkout_ok else "CRITICAL",
                        "passed": checkout_ok,
                        "detail": None if checkout_ok else "Checkout page not accessible",
                    })
                    if not checkout_ok:
                        critical_failures.append("checkout_accessible")

                # Build final report
                passed = len(critical_failures) == 0
                qa_report = {
                    "checks": checks,
                    "critical_failures": critical_failures,
                    "high_warnings": high_warnings,
                    "medium_warnings": medium_warnings,
                    "passed": passed,
                    "products_checked": len(products),
                    "pages_checked": len(pages),
                }

                # Create or block store_review gate
                if passed:
                    notes = None
                    if high_warnings or medium_warnings:
                        notes = f"Warnings: {', '.join(high_warnings + medium_warnings)}"
                    gate = ApprovalGate(
                        project_id=self.project_id,
                        gate_name="store_review",
                        pipeline_order=10,
                        status="pending",
                        notes=notes,
                    )
                    db.add(gate)
                    project.status = "awaiting_site_review"
                    db.commit()
                    db.refresh(gate)
                    self.log.info("store_review_gate_created", gate_id=gate.id, warnings_count=len(high_warnings))
                else:
                    project.status = "failed"
                    db.commit()
                    self.log.error("qa_critical_failures", failures=critical_failures)
                    notify_task_failed(
                        project_id=self.project_id,
                        agent_name=self.agent_name,
                        error=f"QA CRITICAL failures: {', '.join(critical_failures)}",
                    )

                return {"qa_report": qa_report, "_tokens_used": 0, "_cost_usd": 0.0}

            finally:
                shop_client.close()
