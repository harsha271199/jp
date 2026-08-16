# Setup

1. Upload all files to the repository root.
2. Keep `.github/workflows/scrape.yml` at that exact path.
3. For one clean test, it is okay if `seen_links.csv` does not exist.
4. Run Actions -> Construction Job Scraper -> Run workflow.
5. After the clean test, keep `seen_links.csv` permanently.
6. Review `source_health.csv` for exact WORKING/FAILED company counts.
7. Telegram secrets are optional: `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`.
