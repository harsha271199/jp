# Construction Job Scraper V4

Strict US construction/civil job scraper for entry-level through 0–2 YOE.

V4 keeps the full company list, but removes false positives from corporate service pages, rejects manager/lead/senior roles (while keeping Assistant Project Manager), and requires construction context for ambiguous titles such as Field Engineer, Scheduler, Civil Engineer, Project Controls, and Estimator.

Supported ATS sources: Greenhouse, Lever, Ashby, Workday. Public career pages are used only to discover one of these ATS systems; arbitrary website links are never emitted as jobs.
