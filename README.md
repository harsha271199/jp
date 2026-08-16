# Construction Job Scraper V14

HAR-verified source build. See `HAR_VERIFIED_SOURCES.md`.

# Construction Job Scraper V13

Targets US construction/civil roles suitable for entry-level / roughly 0-2 YOE.

V13 keeps the working V12 sources and adds:
- corrected Oracle Candidate Experience mappings for Texas Instruments, Digital Realty, Mortenson, and Sundt;
- explicit `BROWSER_ONLY` status for verified sources that block GitHub Actions HTTP requests (no bypass attempts);
- source-health metrics based on **current** matching jobs, independent of `seen_links.csv`;
- separate current-job and new-job counts.

Keep `seen_links.csv` during normal runs.
