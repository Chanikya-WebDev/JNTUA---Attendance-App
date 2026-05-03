# JNTUA Student Attendance Checking App

> A web application for JNTUA students to instantly check their subject-wise attendance percentage — no manual portal navigation needed.

**Live:** [jntua-attendance-app.vercel.app](https://jntua-attendance-app.vercel.app)

---

## Table of Contents
- [About](#about)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture & Files](#architecture--files)
- [Getting Started](#getting-started)
- [Usage](#usage)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

---

## About

The **JNTUA Student Attendance Checking App** helps students at Jawaharlal Nehru Technological University Anantapur (JNTUA) track their class attendance in a fast, transparent, and convenient way. Instead of navigating through multiple portal pages manually, this app scrapes, parses, and displays all attendance data in a single clean dashboard.

Built as a real-world full-stack project — live, deployed, and actively used by students.

---

## Features

- Secure login using existing JNTUA portal credentials
- Concurrent scraping — all subjects fetched in parallel using `ThreadPoolExecutor`
- Subject-wise attendance percentage with present/absent counts
- Skip / Attend calculator — shows exactly how many classes can be skipped (≥75%) or must be attended (<75%)
- Smart semester filter — auto-detects and shows only current semester data
- Date-wise attendance drill-down per subject
- Contact / Issue reporting form with email notification support
- Holiday calendar with list of JNTUA holidays
- SEO optimised — sitemap, robots.txt, canonical meta tags

---

## Tech Stack

| Component | Technology |
|---|---|
| Backend | Python · Flask |
| Web Scraping | `requests` · `BeautifulSoup4` |
| Frontend | HTML · CSS · Font Awesome |
| Email | Flask-Mail |
| Deployment | Vercel |

---

## Architecture & Files

```
├── attendance_scraper.py    # Login + attendance scraping logic
├── index.py                 # Flask app — all routes and session handling
├── templates/
│   ├── index.html           # Login page
│   ├── result.html          # Attendance dashboard
│   ├── error.html           # Error page
│   ├── contact.html         # Contact / issue reporting form
│   ├── contributors.html    # Contributors page
│   └── list_of_holidays.html
├── requirements.txt         # Python dependencies
├── runtime.txt              # Python runtime version for Vercel
├── vercel.json              # Vercel deployment config
└── .gitignore
```

---

## Getting Started

1. **Clone the repository**
   ```bash
   git clone https://github.com/Chanikya-WebDev/JNTUA---Attendance-App.git
   cd JNTUA---Attendance-App
   ```

2. **Create a virtual environment** (recommended)
   ```bash
   python3 -m venv venv
   source venv/bin/activate     # Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set environment variables** — create a `.env` file:
   ```env
   SECRET_KEY=your_flask_secret_key
   ```

---

## Usage

1. Run the app:
   ```bash
   python index.py
   # Visit http://localhost:5001
   ```

2. Enter your JNTUA portal username and password.

3. View your attendance dashboard — subject-wise percentages, skip/attend counts, and daily history.

---

## Deployment

Deployed on **Vercel** with zero-config Python serverless support:

1. Push to GitHub
2. Connect repository to [Vercel](https://vercel.com)
3. Set environment variable: `SECRET_KEY`
4. Deploy — Vercel picks up `vercel.json` and `runtime.txt` automatically

### Important: Attendance Portal Anti-Bot Restriction

The upstream attendance portal currently blocks direct server-side HTTP scraping from many serverless/data-center IPs.
This app now relies on a browser-fingerprinted HTTP client (`curl_cffi`) instead of a headless browser runtime.
For reliable production behavior, deploy with the dependencies installed in the same environment that runs the app.

### Recommended Deployment (Render + Docker)

This repository now includes:

- `Dockerfile` (installs Python deps)
- `render.yaml` (one-click Render blueprint)
- `.dockerignore`

Steps:

1. Push the repository with these files.
2. Create a new Render Web Service from the repo (it will detect `render.yaml`).
3. Set required environment variables (`SECRET_KEY`, mail vars, `DATABASE_URL` if used).
4. Deploy.

### Run Locally with Docker

```bash
docker build -t jntua-attendance-app .
docker run --rm -p 10000:10000 --env SECRET_KEY=dev-secret jntua-attendance-app
```

Then open: `http://localhost:10000`

---

## Contributing

Contributions are welcome. To contribute:

- Fork the repository
- Create a feature branch
- Submit a pull request with a clear description

To report bugs or request features, use the [Contact page](https://jntua-attendance-app.vercel.app/contact) on the live site.

---

## License

```
MIT License
Copyright (c) 2026 Chanikya-WebDev
```

---

## Contact

Chanikya · [@Chanikya-WebDev](https://github.com/Chanikya-WebDev) · jchanikya06@gmail.com
