# V12 test instructions

1. Replace `job_scraper.py`, `companies.csv`, `requirements.txt`, `README.md`, and `SETUP.md` in the test repository.
2. Keep the existing `.github/workflows/scrape.yml`.
3. Keep `seen_links.csv` -- do not delete it.
4. Keep the existing `*-Construction-Jobs.md` history.
5. Run the workflow manually once.
6. Capture the complete `SOURCE HEALTH` block and warnings.

A source is counted WORKING only when its configured adapter completes successfully. New-job count is incremental because `seen_links.csv` is retained.
