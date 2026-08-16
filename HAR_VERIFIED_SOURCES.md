# HAR-verified sources in V14

These mappings were derived from browser HAR exports supplied during testing. No cookies, JWTs, CSRF tokens, or other session credentials are stored.

- QTS Data Centers — Phenom public search HTML
- Digital Realty — Oracle HCM Candidate Experience REST
- JLL — Workday CXS
- Vantage Data Centers — Workday CXS
- Texas Instruments — Oracle HCM Candidate Experience REST
- Turner Construction — Cornerstone/CSOD public job-search API
- Sundt Construction — Oracle HCM Candidate Experience REST
- Mortenson — public careers search (Coveo-backed; conservative HTML/JSON-LD fallback)
- JE Dunn — SuccessFactors/RMK public recruiting/search
- Brasfield & Gorrie — Jibe `/api/jobs`
- Skanska USA — Jibe `/api/jobs`
- Bechtel — Phenom public search HTML
- Hensel Phelps — SuccessFactors recruiting API / RMK fallback
- GlobalFoundries — Eightfold careers source
- ASML — Sitecore-backed public careers source (kept conservative in this build)
- TSMC — Avature-style public search HTML
- CBRE — Avature-style public search HTML
- Exyte — Phenom public search HTML
- Samsung Semiconductor — public InsightFinder JSON API
- DPR Construction — official current-positions page with strict job-page validation

V14 intentionally does not replay browser cookies or tokens. If a public endpoint blocks GitHub Actions, the source is reported as failed rather than bypassed.
