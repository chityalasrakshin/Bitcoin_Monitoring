---
name: chainsentry-frontend
description: Use whenever building or modifying any UI for ChainSentry (the Bitcoin forensics investigation dashboard). Covers visual design direction, avoiding generic AI-generated UI tells, and component conventions.
---

# ChainSentry Frontend Standards

This is a professional investigator's tool (like a SOC/forensics workstation), not a
marketing site or generic SaaS dashboard. Design accordingly.

## Avoid these defaults — they are the most common AI-generated tells:
- Cream/off-white background with a terracotta or orange accent
- Identical rounded cards everywhere with the same soft grey drop-shadow
- ALL-CAPS tracked-out labels above every section ("OVERVIEW", "METRICS")
- Meta text joined with middle dots (A · B · C) or spaced em-dashes ("Word — fragment")
- A "→" appended to every button/link label
- Gradient washes used purely as decoration
- Numbered 01/02/03 markers on content that isn't actually a sequence
- Fade-and-slide-up entrance animation on every card on scroll

## Design direction for ChainSentry specifically
- Dense, data-forward, dark-mode-first (investigators stare at this for hours) —
  near-black base (#0A0B0D–#111318), not tinted pure black.
- One accent color used sparingly for risk/alert states only (e.g. a controlled red
  for high-risk, amber for medium) — color must carry investigative meaning, never decoration.
- Typography: one workhorse sans (UI text/labels) + one monospace (addresses, TXIDs,
  hex values, amounts) — the monospace is functional here, not a stylistic label choice.
- Real information density: tables and graph panels earn their space; don't pad with
  whitespace to look "clean" — the users are professionals, not visitors to a landing page.
- Motion only on user action (expanding a node, confirming a tag) — never ambient/on-load.
- Every screen needs a real empty state written in the product's voice ("No alerts yet.
  Upload a dataset to begin.") not a generic illustration.

## Component conventions
- All shadcn/ui primitives customized to the above palette — never left at defaults.
- Cytoscape.js graph canvas is the visual centerpiece; UI chrome around it stays quiet.
- Status/risk indicated by color + icon + text label together, never color alone.
- Buttons describe the exact action ("Escalate case", not "Submit").
