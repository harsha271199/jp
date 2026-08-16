# V8 test

1. Replace the repository files with the V8 files.
2. Keep your existing `.github/workflows/scrape.yml` if it already runs `python job_scraper.py`.
3. Do not delete `seen_links.csv` for normal operation. For a deliberate one-time full baseline test only, deleting it will make all current matches appear new.
4. Run the workflow manually.
5. Review the SOURCE HEALTH summary and `source_health.csv`.
