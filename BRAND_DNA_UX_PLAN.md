# Brand DNA UX Overhaul — Progress Tracker

> Temporary working doc. Delete once all chunks are shipped.
> Last updated: 2026-05-31

## Goal
Make Brand DNA setup fast, guided, and AI-powered so users can go from zero to a complete brand profile in under 3 minutes — while still yielding a rich, useful output for all downstream agents.

## Dropped
- **#7 Social/Google profile import** — platform risk, maintenance cost, website scraping covers the same need

---

## Chunks

| # | Name | Status | Est. |
|---|------|--------|------|
| 1 | AI-first primary flow | ✅ done | 1 day |
| 2 | MVP required vs optional fields | ✅ done | 0.5 days |
| 3 | Website scraping as primary population | ✅ done | 2 days |
| 4 | Flat single-page confirmation | ✅ done | 2 days |
| 5 | Confidence badges on AI-generated fields | ✅ done | 0.5 days |
| 6 | Persona archetypes | ✅ done | 2 days |
| 7 | Live preview panel | ✅ done | 4 days |

**Total estimate: ~12 days**

---

## Chunk Detail

### Chunk 1 — AI-first primary flow
**Goal:** Make AI generation the hero, not the hidden panel. User describes their business → everything is pre-filled → wizard becomes review, not data entry.

Tasks:
- [ ] Replace Step0Templates with a split screen: left = business basics form, right = "Describe your business" AI prompt (both visible at once)
- [ ] Auto-advance to flat review page (Chunk 4) once generation completes
- [ ] Make the template gallery a secondary "Start manually" path, not the primary screen
- [ ] Add animated generation loading state with rotating messages ("Crafting your voice...", "Choosing your colours...")

---

### Chunk 2 — MVP required vs optional fields
**Goal:** Users can get to a working Brand DNA in one pass through only 8 essential fields. Everything else is labelled "optional — enhance later" and collapsed by default.

**Required fields (minimum viable Brand DNA):**
1. Business name
2. Industry
3. Tone
4. Primary colour
5. Tagline
6. 2–3 USPs
7. 1 persona
8. Logo (optional but high-value)

Tasks:
- [ ] Mark required fields with a subtle indicator
- [ ] Collapse optional sections by default in the review page
- [ ] Add a "completeness" score/ring on the client profile card (0–100%)
- [ ] Add "Enhance Brand DNA" nudge on the client profile when score < 70%

---

### Chunk 3 — Website scraping as primary population
**Goal:** If a URL is provided, scrape + enrich immediately and use the result to pre-populate the AI generation prompt — so the generate call has real brand signals, not just a blank description.

Tasks:
- [ ] Backend: extend enrichment agent to return structured extraction (name, description, tagline hints, tone signals, colour hints from CSS/images) in addition to suggestions
- [ ] Backend: new `POST /api/clients/{id}/scrape` endpoint that runs scrape + returns raw brand signals
- [ ] Frontend: show "Scanning your website..." loading state right after URL is entered (debounced 1.5s)
- [ ] Frontend: feed scraped signals into the AI generation prompt automatically
- [ ] Frontend: show a "We found these signals from your site" summary before generating

---

### Chunk 4 — Flat single-page confirmation
**Goal:** After AI generation, replace the 6-step wizard with a single scrollable page. Sections are collapsed by default (showing a 1-line summary). User expands any section they want to edit.

Tasks:
- [ ] Build `BrandDNAReviewPage` component — full-page, sections: Business / Voice / Visual / Messaging / Personas
- [ ] Each section: collapsed = shows key values as chips/pills; expanded = shows the edit fields inline
- [ ] "Looks good ✓" button per section marks it confirmed (ties into confidence badges in Chunk 5)
- [ ] "Save & Finish" button at the bottom persists everything
- [ ] Wire router so the wizard redirects here after generation, and it's also accessible from the client profile as "Edit Brand DNA"

---

### Chunk 5 — Confidence badges on AI-generated fields
**Goal:** Make it visually obvious which values were AI-generated vs manually entered. Guide the user to review AI outputs without overwhelming them.

Tasks:
- [ ] Add `source: 'ai' | 'manual' | 'scraped'` metadata to WizardData and persist to DB (BrandDNA model)
- [ ] Render a small "AI" pill badge on generated field values in the review page
- [ ] Clicking a badge opens an inline edit with a "Confirm" / "Edit" choice
- [ ] Confirmed fields show a green checkmark; unconfirmed AI fields show amber

---

### Chunk 6 — Persona archetypes
**Goal:** Replace the blank persona form with 3 AI-suggested persona cards derived from the brand DNA already collected. User picks one (or all) and edits lightly.

Tasks:
- [ ] Backend: new `POST /api/clients/{id}/personas/suggest` endpoint — takes existing brand DNA + industry, returns 3 persona archetypes as JSON
- [ ] Frontend: show persona suggestion cards before the manual form
- [ ] Each card: name, age range, 3 pain points, 3 goals, top channels — all editable inline
- [ ] "Add this persona" button per card; "Create custom persona" fallback

---

### Chunk 7 — Live preview panel
**Goal:** As the user fills in / confirms brand DNA fields, show a real-time side panel with 3 sample content pieces rendered in their brand style.

**Preview types:**
- Social caption (tone + personality traits)
- Ad headline (USPs + tagline)
- Email subject line (language style + key messages)

Tasks:
- [ ] Build `BrandPreviewPanel` component — fixed right-side panel (desktop), bottom sheet (mobile)
- [ ] Debounced re-render (500ms) on field changes
- [ ] Render sample content using current brand values (client-side template strings, no API call)
- [ ] Show brand colours as swatches, font names as styled text samples
- [ ] "Copy" button on each sample content piece
- [ ] Collapse/expand toggle so it doesn't crowd the form

---

## Architecture notes
- Chunks 1–2 are pure frontend, no backend changes needed
- Chunk 3 requires backend work first (scrape endpoint), then frontend
- Chunk 4 is the central UX refactor — everything else builds on top of it
- Chunks 5, 6, 7 can be parallelised after Chunk 4 is done

## Recommended build order
1 → 2 → 3 → 4 → 5 → 6 → 7
(Each chunk is usable/shippable on its own)

---

## ✅ COMPLETED — 2026-05-31
All 7 chunks shipped. See git history for file-level detail.
