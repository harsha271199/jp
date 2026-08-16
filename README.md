# Construction Job Scraper V16

US construction/civil entry-level and 0-2 YOE job scraper.

V16 keeps the V15 working-source base and improves HAR-backed adapters and result quality:
- Fixes Clayco/Crelate apply URLs and removes stale Crelate records older than 180 days.
- Adds HAR-derived ASML Sitecore Discover adapter.
- Fixes Samsung Semiconductor search response parsing.
- Uses the verified public Jibe `/api/jobs` feed for Brasfield & Gorrie and Skanska USA.
- Adds stricter construction-context checks for semiconductor/data-center/technology employers to reduce false positives.
- Uses W.E. O'Neil's current Pinpoint careers portal as the source URL.
- Preserves source health reporting, browser-only classification, deduplication, US filtering, and explicit >2 YOE rejection.

Keep `seen_links.csv` and the existing Construction Jobs markdown file when upgrading.
