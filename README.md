# Construction Job Scraper V10

Stable V7/V9 filtering plus a conservative `verified_listing` adapter for official construction career portals.

Key safety rule: ordinary marketing/service pages are never emitted as jobs. A result must come from a supported ATS, JobPosting JSON-LD, or a verified job-detail URL with job-application evidence.

V10 also disables the unsafe DPR HTML-card adapter that previously produced a false `Preconstruction` service-page result.
