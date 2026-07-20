# AGENTS.md

This file is the working guide for future coding agents operating in this repository.

It is intentionally specific. When something is confirmed from the current codebase, it is written as a fact. When something is unclear, missing, or appears stale, it is called out instead of being guessed.

If you are an agent working in this repo, follow this document before making changes.

## 1. Project Identity

- Project name: `JNTUA Attendance App`
- Primary purpose: a Flask web app that logs into the JNTUA attendance portal, scrapes subject-wise attendance data, computes attendance status, and renders the result to students.
- Primary deployment target: Vercel serverless Python runtime via `index.py`
- Primary backend language: Python
- Frontend approach: server-rendered HTML templates with compact CSS, plus a small Tailwind CSS build for some pages

## 2. Current Repository Layout

Confirmed project files:

- `index.py`
- `attendance_scraper.py`
- `README.md`
- `requirements.txt`
- `package.json`
- `package-lock.json`
- `tailwind.config.js`
- `vercel.json`
- `templates/`
- `static/`

Confirmed template files:

- `templates/index.html`
- `templates/result.html`
- `templates/error.html`
- `templates/contact.html`
- `templates/contributors.html`
- `templates/list_of_holidays.html`
- `templates/icon.png`

Confirmed static files:

- `static/css/output.css`
- `static/src/input.css`

Historical or removed files should not be reintroduced unless there is a deliberate reason.

## 3. Source Of Truth

When facts conflict, use this priority order:

1. Current Python and template code
2. Deployment/config files
3. This `AGENTS.md`
4. `README.md`



## 4. Active Application Entry Points

### 4.1 Flask App
- Main app file: `index.py`
- Flask app object: `app = Flask(__name__)`
- Local run mode: `app.run(port=5001, debug=True)`
- Vercel handler hook:
  - `def handler(environ, start_response): return app(environ, start_response)`

### 4.2 Scraper Module
- Scraper file: `attendance_scraper.py`
- Portal base URL:
  - `https://jntuaceastudents.classattendance.in/`

## 5. Confirmed Active Routes

At the time this file was updated, the active Flask routes were:

- `/`
  - GET: render the Android app announcement/download page
  - POST: retain the legacy portal-login flow (no longer exposed by the landing page UI)
- `/downloads/JNTUA-Attendance-Application.apk`
  - GET: download the official Android APK
- `/dashboard`
  - Scrapes attendance and renders the result dashboard
- `/contact`
  - GET: contact form
  - POST: submit issue report via email or log file fallback
- `/contributors`
  - Contributors page with contributors github,linkedin,email details
- `/loh`
  - Holiday page
- `/api/reactions`
  - GET: return global reaction counts plus the current device selection
- `/api/react`
  - POST: update a device reaction and persist the global counts in SQLite
- `/robots.txt`
- `/sitemap.xml`
- `/icon.png`

## 6. High-Level Request Flow

### 6.1 Login Flow
1. User submits username and password on `/`
2. `student_login()` in `attendance_scraper.py` performs portal login
3. On success, Flask session stores `session["user"] = username`
4. In-memory `ACTIVE_SESSIONS[username]` stores the authenticated `requests.Session`
5. User is redirected to `/dashboard`

### 6.2 Dashboard Flow
1. `/dashboard` reads `session["user"]`
2. Looks up the authenticated portal session from `ACTIVE_SESSIONS`
3. Calls:
   - `get_student_details()`
   - `get_subjects()`
   - `fetch_attendance()`
4. Computes:
   - total days
   - present count
   - overall attendance percentage
   - per-subject `Can Skip`
   - per-subject `Need to Attend`
5. Renders `templates/result.html`

### 6.3 Browser Detail Flow
1. The dashboard renders per-subject detail rows into the page payload
2. Frontend JavaScript stores the subject drill-down data in browser storage (`sessionStorage`)
3. Clicking a subject opens the modal using browser-side data
4. There is no longer a separate server-side attendance detail cache for the modal flow

Do not reintroduce a server-side attendance cache unless the architecture changes intentionally.

## 7. Confirmed Backend State Model

One in-memory global dict is currently used:
- `ACTIVE_SESSIONS = {}`

Implications:
- State is process-local
- State is not durable across restarts
- State may be unreliable in multi-instance or serverless environments

The old `ATTENDANCE_CACHE`/token lookup path has been removed from the current design. Keep it that way unless there is a clear reason to reintroduce shared storage.

## 8. Scraper Details

### 8.1 Authentication Strategy
`student_login()` currently:
- creates a `requests.Session`
- fetches the portal landing page
- completes the Hostinger CDN SHA-256 browser challenge when it is presented
- parses the login form with BeautifulSoup
- extracts obfuscated JavaScript array values for the integrity token
- falls back to hardcoded token defaults if extraction fails
- posts credentials to the same base URL
- validates success by checking whether the final URL contains `studenthome.php`

### 8.2 Student Metadata Parsing
`get_student_details()` currently:
- loads `studenthome.php`
- extracts “My Details” content from card/list markup
- also extracts hidden fields from the `studentsubjects.php` form

### 8.3 Subject Discovery
`get_subjects()` currently:
- submits a POST to `studentsubjects.php`
- extracts form payloads for each subject from forms targeting `studentsubatt.php`

### 8.4 Attendance Fetching
`fetch_attendance()` currently:
- uses `ThreadPoolExecutor`
- calls `fetch_single_attendance()` for each subject
- returns a lightweight dataframe-like wrapper with a `to_dict("records")` interface

## 9. Confirmed Frontend Pages

- `templates/index.html`
  - login page
  - public landing page
  - this page retains Google Search Console and Google Analytics tags by design
- `templates/result.html`
  - authenticated dashboard
  - should remain `noindex` because it is personalized
  - uses browser-side subject drill-down data
- `templates/contact.html`
  - support form
- `templates/contributors.html`
  - public contributors page
- `templates/list_of_holidays.html`
  - public holiday page
- `templates/error.html`
  - error display page, should remain `noindex`

## 10. Email And Issue Reporting

The contact flow currently uses:
- `Flask-Mail`
- SMTP environment variables
- optional screenshot upload

If adding or changing upload behavior:
- validate the file extension
- validate the file size
- verify it is a real image
- never trust the browser `accept` attribute alone
- attach or store the upload only after validation

## 11. Security And Configuration Notes

- CSRF protection is enabled in the app
- Secure cookies should remain enabled in production
- `SECRET_KEY` must be set from the environment in production
- `python-dotenv` is a development convenience only
- do not rely on `.env` in Vercel production
- if rate limiting is re-enabled for production use, use a shared backend such as Redis rather than in-memory storage

## 12. Python Dependencies

Confirmed notable dependencies:
- Flask
- requests
- BeautifulSoup4
- Flask-Mail
- Flask-WTF
- Flask-Limiter[Redis] may use in future development
- python-dotenv may be used for local development only

If dependencies change, update `requirements.txt` and any setup instructions.

## 13. Frontend Build Tooling

- Tailwind source: `static/src/input.css`
- Tailwind output: `static/css/output.css`
- `package.json` provides:
  - `npm run build-css`
  - `npm run watch-css`

Before release, ensure `static/css/output.css` is regenerated after Tailwind source changes.

## 14. Deployment

- Deployment target: Vercel
- `vercel.json` routes all requests to `index.py`
- Vercel is stateless, so keep memory-based state small and disposable
- Do not assume a persistent filesystem on Vercel
- Keep public pages SEO-friendly, but keep personalized pages out of search indexing

## 15. Validation Checklist For Agents

Before finalizing changes, check:
- templates render without Jinja syntax errors
- public pages have appropriate title/description/canonical metadata
- private pages are marked noindex
- CSRF token handling still works
- Tailwind CSS is rebuilt if source changed
- no `.env` or secret files were added to git
- no stale references to removed routes or caches remain
- `index.html` still preserves Google Search Console / Analytics tags if the maintainer wants them kept

## 16. Working Rules For Future Agents

- Prefer minimal, local changes over wide rewrites.
- Do not reintroduce removed dead routes or stale references.
- Do not add browser storage for secrets or portal sessions.
- Do not store raw portal credentials anywhere.
- Keep code readable and traceable.
- When in doubt about private versus public pages, choose `noindex` for the private page.
- If you add structured data, make sure it matches the visible content.

## 17. Known Historical Cleanup Already Done

Previously removed or corrected items included:
- stale dead-link pages in the dashboard
- unrelated real-estate content contamination
- older attendance-detail cache/token design in the dashboard flow

Do not restore those patterns unless explicitly requested.

## 18. Questions That Still Need Maintainer Confirmation

- Whether rate limiting should be enabled in production later
- Whether the current in-memory `ACTIVE_SESSIONS` model should be replaced with Redis or another shared store
- Whether the site should continue to retain Google Analytics / Search Console tags on the landing page

## 19. Maintenance Rule For This File

Update this file whenever:
- routes change
- session/cache behavior changes
- SEO/public/private page behavior changes
- deployment assumptions change
- state model changes
