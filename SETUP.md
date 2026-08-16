# Upgrade from V2
1. Replace the repository files with the V3 files.
2. For the first clean test only, delete `seen_links.csv` if your repo has one.
3. Commit to `main`.
4. Actions -> Construction Job Scraper -> Run workflow -> main.
5. Open `scrape` -> `Run python job_scraper.py`.
6. Send the complete output if any source warnings remain.

Individual blocked career sites are logged as warnings and do not stop the other companies.
