# Construction Job Scraper V7

US entry-level / 0-2 YOE construction job scraper.

Supports Greenhouse, Lever, Ashby, Workday, SmartRecruiters and structured JobPosting pages. V7 preserves the V6 filtering and adds exact source-health reporting.

After every run, GitHub Actions prints:
- total unique companies
- successfully queried companies
- working companies with matching jobs
- working companies with zero new matches
- failed/unsupported companies
- source success rate

It also writes `source_health.csv` so failed company sources can be fixed systematically.

`seen_links.csv` is recreated automatically after a clean run. Keep it after testing so future runs report only new jobs.
