"""
Tests for SEO-related functionality in the CloudIA agent system.

Covers:
  - meta_title / meta_description boundary validation (model layer)
  - Schema markup stored as valid JSON in GeneratedContent.schema_markup
  - Sitemap XML structure and deduplication
  - SEO mock response fixture correctness

All tests operate on the DB model layer or pure Python logic.
No external HTTP calls are made.
"""

import json
import xml.etree.ElementTree as ET

import pytest

from tests.factories import make_client, make_project, make_generated_content
from tests.mocks.mock_claude import SEO_RESPONSE


# ---------------------------------------------------------------------------
# Meta field boundary validation
# ---------------------------------------------------------------------------


class TestMetaValidation:
    def test_meta_title_60_chars_boundary(self, db):
        """60 chars is the exact limit — must be stored without truncation."""
        c = make_client(db)
        p = make_project(db, c.id)
        sixty_char_title = "A" * 60
        content = make_generated_content(
            db,
            p.id,
            "home",
            overrides={
                "meta_title": sixty_char_title,
                "status": "approved",
            },
        )
        assert len(content.meta_title) == 60

    def test_meta_description_160_chars_boundary(self, db):
        """160 chars is the exact limit — must be stored without truncation."""
        c = make_client(db)
        p = make_project(db, c.id)
        one_sixty = "B" * 160
        content = make_generated_content(
            db,
            p.id,
            "home",
            overrides={
                "meta_description": one_sixty,
                "status": "approved",
            },
        )
        assert len(content.meta_description) == 160

    def test_meta_title_under_60_chars(self, db):
        """A meta_title well within the limit must be stored unmodified."""
        c = make_client(db)
        p = make_project(db, c.id)
        title = "Sandton Dental Studio"
        content = make_generated_content(
            db,
            p.id,
            "home",
            overrides={"meta_title": title},
        )
        assert content.meta_title == title

    def test_meta_description_under_160_chars(self, db):
        """A meta_description well within the limit must be stored unmodified."""
        c = make_client(db)
        p = make_project(db, c.id)
        desc = "Expert dental care in Sandton. Book today."
        content = make_generated_content(
            db,
            p.id,
            "home",
            overrides={"meta_description": desc},
        )
        assert content.meta_description == desc

    def test_factory_default_meta_title_within_limit(self, db):
        """Factory-generated meta_title must be within the 60-character SEO limit."""
        c = make_client(db)
        p = make_project(db, c.id)
        content = make_generated_content(db, p.id, "home")
        assert len(content.meta_title or "") <= 60

    def test_factory_default_meta_description_within_limit(self, db):
        """Factory-generated meta_description must be within the 160-character SEO limit."""
        c = make_client(db)
        p = make_project(db, c.id)
        content = make_generated_content(db, p.id, "home")
        assert len(content.meta_description or "") <= 160


# ---------------------------------------------------------------------------
# Schema markup
# ---------------------------------------------------------------------------


class TestSchemaMarkup:
    def test_schema_markup_is_valid_json_when_stored(self, db):
        """Schema markup stored in schema_markup column must round-trip cleanly."""
        c = make_client(db)
        p = make_project(db, c.id)
        schema = {
            "@context": "https://schema.org",
            "@type": "LocalBusiness",
            "name": "Sandton Dental Studio",
            "address": {
                "@type": "PostalAddress",
                "addressLocality": "Johannesburg",
                "addressCountry": "ZA",
            },
        }
        content = make_generated_content(
            db,
            p.id,
            "home",
            overrides={"schema_markup": schema, "status": "approved"},
        )
        assert isinstance(content.schema_markup, dict)
        assert content.schema_markup["@type"] == "LocalBusiness"

    def test_schema_markup_serialises_to_valid_json(self, db):
        """Schema markup retrieved from the DB must serialise and deserialise cleanly."""
        c = make_client(db)
        p = make_project(db, c.id)
        schema = {
            "@context": "https://schema.org",
            "@type": "Dentist",
            "name": "Sandton Dental Studio",
        }
        content = make_generated_content(
            db, p.id, "home", overrides={"schema_markup": schema}
        )
        json_str = json.dumps(content.schema_markup)
        parsed = json.loads(json_str)
        assert parsed["@context"] == "https://schema.org"

    def test_schema_type_local_business(self, db):
        """LocalBusiness schema type must be preserved after storage."""
        c = make_client(db)
        p = make_project(db, c.id)
        schema = {"@context": "https://schema.org", "@type": "LocalBusiness"}
        content = make_generated_content(
            db, p.id, "home", overrides={"schema_markup": schema}
        )
        assert content.schema_markup["@type"] == "LocalBusiness"

    def test_schema_type_dentist(self, db):
        """Dentist schema type must be preserved after storage."""
        c = make_client(db)
        p = make_project(db, c.id)
        schema = {"@context": "https://schema.org", "@type": "Dentist"}
        content = make_generated_content(
            db, p.id, "home", overrides={"schema_markup": schema}
        )
        assert content.schema_markup["@type"] == "Dentist"

    def test_seo_mock_response_schema_is_valid(self):
        """SEO_RESPONSE fixture must contain a valid schema dict."""
        schema = SEO_RESPONSE["schema"]
        assert isinstance(schema, dict)
        assert "@context" in schema
        assert "@type" in schema
        json_str = json.dumps(schema)
        parsed = json.loads(json_str)
        assert parsed["@context"] == "https://schema.org"

    def test_seo_mock_response_meta_title_within_limit(self):
        """SEO_RESPONSE fixture meta_title must not exceed 60 characters."""
        assert len(SEO_RESPONSE["meta_title"]) <= 60

    def test_seo_mock_response_meta_description_within_limit(self):
        """SEO_RESPONSE fixture meta_description must not exceed 160 characters."""
        assert len(SEO_RESPONSE["meta_description"]) <= 160


# ---------------------------------------------------------------------------
# Sitemap
# ---------------------------------------------------------------------------


class TestSitemapXMLValidity:
    _SITEMAP_XML = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.co.za/</loc></url>
  <url><loc>https://example.co.za/about/</loc></url>
  <url><loc>https://example.co.za/services/</loc></url>
</urlset>"""

    def test_sitemap_xml_parses_without_error(self):
        """A well-formed sitemap XML string must parse without raising ET.ParseError."""
        root = ET.fromstring(self._SITEMAP_XML)
        assert root is not None

    def test_sitemap_xml_has_correct_url_count(self):
        """The sample sitemap must contain exactly 3 <url> elements."""
        root = ET.fromstring(self._SITEMAP_XML)
        ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
        urls = root.findall(f"{{{ns}}}url")
        assert len(urls) == 3

    def test_sitemap_xml_loc_elements_present(self):
        """Each <url> element must have a <loc> child."""
        root = ET.fromstring(self._SITEMAP_XML)
        ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
        for url in root.findall(f"{{{ns}}}url"):
            loc = url.find(f"{{{ns}}}loc")
            assert loc is not None
            assert loc.text.startswith("https://")

    def test_sitemap_xml_root_tag_is_urlset(self):
        """Root tag must be 'urlset' (possibly namespace-qualified)."""
        root = ET.fromstring(self._SITEMAP_XML)
        assert "urlset" in root.tag

    def test_sitemap_deduplicates_urls(self):
        """Duplicate URLs in a list must be deduplicated while preserving order."""
        urls = [
            "https://example.co.za/",
            "https://example.co.za/about/",
            "https://example.co.za/",  # duplicate
            "https://example.co.za/services/",
        ]
        deduplicated = list(dict.fromkeys(urls))
        assert len(deduplicated) == 3
        assert deduplicated.count("https://example.co.za/") == 1

    def test_sitemap_deduplication_preserves_order(self):
        """After deduplication, the original order of first-occurrence URLs is preserved."""
        urls = [
            "https://example.co.za/",
            "https://example.co.za/about/",
            "https://example.co.za/",
        ]
        deduplicated = list(dict.fromkeys(urls))
        assert deduplicated[0] == "https://example.co.za/"
        assert deduplicated[1] == "https://example.co.za/about/"

    def test_seo_response_sitemap_urls_are_unique(self):
        """SEO_RESPONSE fixture sitemap_urls must not contain duplicates."""
        urls = SEO_RESPONSE["sitemap_urls"]
        assert len(urls) == len(set(urls))

    def test_seo_response_sitemap_urls_start_with_https(self):
        """All SEO_RESPONSE sitemap URLs must use HTTPS."""
        for url in SEO_RESPONSE["sitemap_urls"]:
            assert url.startswith("https://"), f"Non-HTTPS URL found: {url}"

    def test_seo_response_sitemap_urls_have_content(self):
        """SEO_RESPONSE must contain at least one sitemap URL."""
        assert len(SEO_RESPONSE["sitemap_urls"]) > 0


# ---------------------------------------------------------------------------
# SEO field quality — factory content checks
# ---------------------------------------------------------------------------


class TestSEOFieldQuality:
    def test_no_keyword_stuffing_in_meta_title(self, db):
        """Factory meta_title must not repeat the same word more than 3 times."""
        c = make_client(db)
        p = make_project(db, c.id)
        content = make_generated_content(db, p.id, "home")
        meta_title = content.meta_title or ""
        words = meta_title.lower().split()
        for word in words:
            count = words.count(word)
            assert count <= 3, f"Word '{word}' repeated {count} times in meta_title"

    def test_meta_title_not_empty(self, db):
        """Factory meta_title must be non-empty."""
        c = make_client(db)
        p = make_project(db, c.id)
        content = make_generated_content(db, p.id, "home")
        assert (content.meta_title or "").strip() != ""

    def test_meta_description_not_empty(self, db):
        """Factory meta_description must be non-empty."""
        c = make_client(db)
        p = make_project(db, c.id)
        content = make_generated_content(db, p.id, "home")
        assert (content.meta_description or "").strip() != ""
