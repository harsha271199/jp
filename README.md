# Construction Job Scraper V11

Consolidated construction job scraper targeting US entry-level / 0-2 YOE roles.

V11 keeps the previously working ATS adapters and adds conservative adapters for verified source families discovered during browser research:

- Eightfold (Micron, Applied Materials, Lam Research, GlobalFoundries)
- NLX/jobsyn (AECOM, Fluor, Burns & McDonnell, Walsh)
- Oracle HCM Candidate Experience (Mortenson, Sundt)
- Dayforce (Balfour Beatty US)

Existing Greenhouse, Lever, Ashby, Workday, SmartRecruiters, SuccessFactors and company-specific adapters remain.

The scraper does not treat ordinary marketing/service pages as job postings.

## Test
Keep your existing `seen_links.csv` and existing jobs Markdown file. Run the GitHub Actions workflow normally, then compare the SOURCE HEALTH block to your previous baseline.
