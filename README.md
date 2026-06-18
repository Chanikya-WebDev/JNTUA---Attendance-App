# JNTUA Student Attendance Checking App

> A Flask-based attendance dashboard for JNTUA students that logs into the official portal, scrapes subject-wise attendance, and renders a clean summary view with skip/attend calculations.

**Live:** [jntua-attendance-app.vercel.app](https://jntua-attendance-app.vercel.app)

---

## Table of Contents
- [About](#about)
- [Features](#features)
- [System Design](#system-design)
- [Repository Structure](#repository-structure)
- [Environment Variables](#environment-variables)
- [Local Setup](#local-setup)
- [How It Works](#how-it-works)
- [Deployment Notes](#deployment-notes)
- [Security Notes](#security-notes)
- [SEO and Accessibility Notes](#seo-and-accessibility-notes)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

---

## About

The **JNTUA Student Attendance Checking App** helps students at Jawaharlal Nehru Technological University Anantapur (JNTUA) track class attendance without manually navigating the official portal.

The app:
- authenticates with the portal using the student’s own credentials,
- scrapes attendance data,
- computes subject-wise statistics,
- renders a dashboard with skip/attend guidance,
- and serves public information pages such as holidays, contributors, and support.

This project is intentionally lightweight:
- Flask for the web layer
- `requests` + BeautifulSoup for scraping
- Jinja templates for server-side rendering
- Vercel for deployment

---

## Features

- Login with existing JNTUA portal credentials
- Subject-wise attendance summary
- Present / absent counts per subject
- Skip / attend calculator for the 75% rule
- Current semester filtering
- Detailed date-wise attendance drill-down
- Contact / issue form with optional screenshot upload
- Email notification support through Flask-Mail
- CSRF protection for forms
- SEO routes: `robots.txt` and `sitemap.xml`
- Social metadata and JSON-LD on public pages
- Browser-side storage for subject drill-down details
- Public pages designed for responsive, accessible rendering

---

## System Design

### 1) Scraping layer
`attendance_scraper.py` is the portal integration layer. It:
- opens a session with the attendance portal,
- submits login credentials,
- parses student metadata,
- fetches subject lists,
- loads attendance for each subject,
- and returns structured records for the dashboard.

### 2) Web application layer
`index.py` owns the Flask app and routes:
- `/` for login
- `/dashboard` for the attendance view
- `/contact` for issue reporting
- `/contributors` for project credits
- `/loh` for holidays
- `/robots.txt` and `/sitemap.xml` for SEO
- `/icon.png` for the favicon

### 3) Runtime state model
The app uses:
- `ACTIVE_SESSIONS` for short-lived authenticated portal sessions on the server

The attendance detail rows are no longer stored in a separate server-side cache. They are rendered into the dashboard and used by the browser for modal display. That reduces server RAM pressure and removes the old attendance detail cache path.

### 4) UI layer
Templates are server-rendered HTML pages with compact, page-specific styling. The main dashboard is `result.html`, which renders subject cards and loads per-subject details from browser state.

### 5) Contact flow
The contact form accepts:
- admission number
- email
- issue description
- optional screenshot

The backend validates the request and sends the report via Flask-Mail when mail credentials are configured. If mail is unavailable, it falls back to a log file.

---

## Repository Structure

```text
├── attendance_scraper.py        # Login + scraping engine
├── index.py                     # Flask app, routes, session state, SEO routes
├── requirements.txt             # Python dependencies
├── runtime.txt                  # Python version for Vercel
├── vercel.json                  # Vercel deployment config
├── README.md                    # Project documentation
├── .gitignore                   # Ignore build/runtime junk
├── .env.example                 # Local environment template
├── static/
│   ├── css/
│   │   └── output.css           # Compiled Tailwind output
│   └── src/
│       └── input.css            # Tailwind source entry
└── templates/
    ├── index.html               # Login page
    ├── result.html              # Attendance dashboard
    ├── error.html               # Error page
    ├── contact.html             # Issue reporting form
    ├── contributors.html        # Contributors page
    ├── list_of_holidays.html    # Holidays page
    └── icon.png                 # App icon
```

---

## Environment Variables

Create a `.env` file for local development or configure the same values in Vercel.

| Variable | Required | Purpose |
|---|---:|---|
| `SECRET_KEY` | Yes | Flask session signing key |
| `MAIL_SERVER` | No | SMTP host, default: `smtp.gmail.com` |
| `MAIL_PORT` | No | SMTP port, default: `587` |
| `MAIL_USE_TLS` | No | TLS toggle, default: `True` |
| `MAIL_USE_SSL` | No | SSL toggle, default: `False` |
| `MAIL_USERNAME` | No | SMTP username |
| `MAIL_PASSWORD` | No | SMTP password / app password |
| `MAIL_DEFAULT_SENDER` | No | Default sender address |
| `RATELIMIT_STORAGE_URI` | Optional | Redis backend for rate limiting if enabled later |

Example:

```env
SECRET_KEY=replace-with-a-long-random-secret
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USE_SSL=False
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_app_password
MAIL_DEFAULT_SENDER=your_email@gmail.com
# Optional if rate limiting is enabled with Redis later:
# RATELIMIT_STORAGE_URI=redis://default:password@host:6379/0
```

---

## Local Setup

### 1) Clone the repository
```bash
git clone https://github.com/Chanikya-WebDev/JNTUA---Attendance-App.git
cd JNTUA---Attendance-App
```

### 2) Create a virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3) Install Python dependencies
```bash
pip install -r requirements.txt
```

### 4) Install Node dependencies for Tailwind
```bash
npm install
```

### 5) Build the CSS
```bash
npm run build-css
```

### 6) Configure environment variables
Create a `.env` file from `.env.example`.

### 7) Run the app
```bash
python index.py
```

Open:
```text
http://localhost:5001
```

---

## How It Works

1. Student enters JNTUA portal credentials.
2. `attendance_scraper.py` authenticates and builds a `requests.Session`.
3. The app fetches student details and subject list.
4. Attendance is fetched per subject.
5. The dashboard calculates:
   - total classes
   - present / absent counts
   - attendance percentage
   - skip / attend guidance
6. The dashboard renders attendance detail rows into the page for browser-side modal use.
7. Clicking a subject opens detailed attendance rows without an extra server cache lookup.

---

## Deployment Notes

This project is deployed on **Vercel**.

Recommended deployment steps:
1. Push the repository to GitHub.
2. Connect the repo to Vercel.
3. Set `SECRET_KEY` and mail variables in the Vercel environment.
4. Deploy.

Important:
- Vercel serverless functions are stateless.
- Keep runtime state small and disposable.
- Browser-side detail storage is preferable to a separate server-side attendance cache for this project size.
- If traffic grows, move shared runtime state to Redis or another external store.

---

## Security Notes

The app includes the following protections:
- CSRF protection for form submissions
- secure cookie settings in production
- email input and upload validation
- optional screenshot verification for the contact form
- server-side session storage for portal auth state

Recommended operational rules:
- never store portal passwords in your own database
- do not log raw credentials
- keep uploaded files size-limited and image-validated
- rotate your `SECRET_KEY` if it is ever exposed
- keep Google Search Console and Google Analytics tags only on the public landing page, not private pages

---

## SEO and Accessibility Notes

Public pages use:
- Open Graph meta tags
- canonical URLs
- JSON-LD structured data
- `robots.txt`
- `sitemap.xml`

Accessibility rules used in this codebase:
- consistent base font sizing
- visible focus states
- light color scheme on public pages
- noindex on personalized dashboard pages
- responsive layouts that work on mobile and desktop

The dashboard and other private user-specific pages should remain **noindex** so attendance data is not surfaced to search engines.

---

## Contributing

Contributions are welcome.

Suggested workflow:
1. Fork the repository
2. Create a feature branch
3. Make a focused change
4. Open a pull request with a clear description

Bug reports and feature ideas can also be submitted through the contact form on the live site.

---

## License

```text
MIT License
Copyright (c) 2026 Chanikya-WebDev
```

---

## Contact

Chanikya · [@Chanikya-WebDev](https://github.com/Chanikya-WebDev)
