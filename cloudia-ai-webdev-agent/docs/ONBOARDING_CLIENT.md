# Client Onboarding Guide

This document explains what information you need from a client before starting a project in the CloudIA agent system.

## What You Need Before Creating a Project

### For ALL clients (WordPress and Shopify)

**Business information:**
- Business name (exact trading name)
- Industry (e.g., "dental", "retail", "restaurant", "legal services")
- Business type: "ecommerce" | "local_service" | "restaurant" | "professional"
- City and country (affects local SEO content)
- Contact email and phone number
- Physical address (for LocalBusiness schema markup)
- Existing website URL (if any — agents will NOT copy content from it, but avoid obvious overlaps)

**Brand:**
- Primary colour (hex code) — e.g., #1A3C5E
- Secondary colour (hex code)
- Accent colour (hex code) — often white or a highlight
- Heading font preference (or "professional", "modern", "elegant" — agent will choose)
- Body font preference
- Logo file (PNG or SVG preferred, transparent background)

**Content brief (4 questions — collect in writing):**
1. What does the business do? (Be specific — services offered, products sold)
2. Who is the target customer? (Age, location, problem they're solving)
3. What makes them different? (USP — one or two sentences, in their words)
4. What should website visitors do? (CTA goal — "book appointment", "request quote", "shop now")

**Tone of voice:**
- Professional / Corporate
- Friendly / Approachable
- Luxury / Premium
- Bold / Direct

### For WordPress sites additionally:

**Hosting credentials:**
- WordPress site URL (the site must already be installed and accessible)
- WordPress admin username
- WordPress Application Password (not the admin login password)

**To generate an Application Password:**
1. Log into WordPress admin
2. Go to Users → Your Profile
3. Scroll to "Application Passwords"
4. Enter "CloudIA Agent" as the name
5. Click "Add New Application Password"
6. Copy the generated password — it shows ONCE

**Pages needed** (confirm with client):
- Home (always)
- About Us
- Services (list the specific services)
- Contact
- Blog (optional)
- Gallery (optional)
- Team / Staff (optional)
- FAQ (optional)

### For Shopify sites additionally:

**Shopify credentials:**
- Store URL (e.g., `your-store.myshopify.com`)
- Private app access token OR Custom app token with scopes: `read_products write_products read_themes write_themes read_content write_content read_navigation write_navigation`

**Store structure:**
- Product list (name, description, price in ZAR, any variants like size/colour)
- Collection names (how products are grouped)
- Currency (default: ZAR)

## Creating the Project in CloudIA

1. Go to `/new` in the operator dashboard
2. Step 1: Select existing client or create new
3. Step 2: Platform (or Auto-detect)
4. Step 3: Paste in the 4 brief answers
5. Step 4: Select required pages
6. Step 5: Enter brand colours and fonts, upload logo
7. Step 6: Enter platform credentials
8. Step 7: Review and launch

## What Happens After Launch

1. **Director agent** analyzes the brief (30s–2min)
2. **Content agent** generates all copy (~2–5 min depending on page count)
3. **You receive a notification** — review content in `/projects/:id/content`
4. **Edit and approve** content (your most important job — check for accuracy)
5. Approve all content → agents build the site automatically (~5–10 min)
6. Site review notification → inspect built site
7. Approve → project marked complete

## Common Issues

**"Platform: needs_input"** — The brief was too ambiguous for auto-detection. Open the project, manually set the platform, and re-trigger.

**Content gate stuck** — One or more pages may have failed validation (meta too long, empty content). Check the content review page for red-marked pieces. Click "Regenerate" on failed pieces.

**WordPress REST API error** — Confirm the Application Password was generated correctly. Test with:
```
curl -u "admin:xxxx xxxx xxxx xxxx xxxx xxxx" https://yoursite.co.za/wp-json/wp/v2/posts
```
Should return JSON, not 401.

**Shopify 401 error** — Token may have expired or been revoked. Generate a new token in Shopify admin and update in Settings → Credentials.
