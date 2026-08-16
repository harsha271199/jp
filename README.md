# Construction Job Scraper V5

US construction/civil job scraper focused on entry-level / 0-2 years experience.

V5 uses a safer source strategy:
- Direct Greenhouse, Lever, Ashby and Workday adapters.
- SmartRecruiters adapter.
- Generic career sites are accepted only when they expose structured `JobPosting` JSON-LD or a supported ATS.
- Ordinary service/marketing pages are never emitted as jobs.
- Workday requests include same-origin browser headers and full job-description retrieval for candidate construction titles.
- Strict construction-context and seniority filtering remains enabled.

Some proprietary/blocked career sites can still warn instead of being scraped. A warning is preferable to inventing a job from a non-job page.
