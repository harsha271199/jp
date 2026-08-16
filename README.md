# Construction Job Scraper V17

Stabilization release based on V16.

Key changes:
- Excludes internships/co-ops from the 0-2 YOE full-time feed.
- Tightens semiconductor/technology/data-center matching: construction context must be present in the job title, reducing generic engineering false positives (especially Western Digital).
- Fixes iCIMS job-detail discovery for Gilbane/Walbridge-style URLs.
- Loosens Jobvite detail discovery for McCarthy.
- Adds verified Walbridge iCIMS source and current W.E. O'Neil / Boldt career sources.
- Preserves V16 Clayco real Crelate links, stale-post filtering, US-only filtering, source health, dedupe, and existing adapters.

Keep `seen_links.csv` and the existing jobs markdown file when upgrading.
