# JNTUA Student Attendance Checking App

> A web‑app for students of JNTUA to easily check their attendance percentage by scraping the official attendance portal.

## Table of Contents
- [About](#about)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture & Files](#architecture--files)
- [Getting Started](#getting-started)
- [Usage](#usage)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

## About
The **JNTUA Student Attendance Checking App** is a tool designed to help students at Jawaharlal Nehru Technological University Anantapur (JNTUA) track their class attendance in a more transparent and convenient manner. Instead of navigating through multiple pages manually, this app aggregates attendance data and displays it clearly.

## Features
- Automatically **scrapes** the official JNTUA attendance portal to fetch attendance data.
- Provides a clean UI to see overall attendance percentage and breakdowns.
- Fast response — minimal manual input required.
- Deployable to cloud platforms (e.g. Vercel).

## Tech Stack
| Component | Technology |
|-----------|------------|
| Backend / Scraper | Python (attendance_scraper.py) |
| Frontend / UI | HTML / Templates (Flask or equivalent) |
| Hosting / Deployment | Vercel |
| Dependency Management | `requirements.txt` |

## Architecture & Files
Here is a high‑level overview of the repository structure:
```
├── attendance_scraper.py    # Script to log in and scrape attendance information
├── index.py                 # Main app / server entry point
├── templates/               # HTML templates for the UI
├── public/                  # Static assets (CSS, JS, images, etc.)
├── requirements.txt         # Python dependencies
├── runtime.txt              # Specifies runtime version for deployment
├── vercel.json              # Configuration file for Vercel deployment
└── .gitignore               # Files and folders to ignore in Git
```

## Getting Started
To run this project locally, follow these steps:

1. **Clone the repository**
   ```bash
   git clone https://github.com/Chanikya-WebDev/JNTUA---Attendance-App.git
   cd JNTUA---Attendance-App
   ```

2. **Create a virtual environment** (optional but recommended)
   ```bash
   python3 -m venv venv
   source venv/bin/activate     # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Usage
1. Launch the application:
   ```bash
   python index.py
   ```
   or via whatever command starts your server.

2. Open your browser and go to the local address (e.g. `http://localhost:5000/`) to see the UI.

3. Input required credentials/info (if any) to let the scraper fetch your attendance.

4. View your attendance percentage and details.

## Configuration
- Make sure you have proper login credentials for the JNTUA attendance portal.
- If the attendance portal changes its HTML structure, you may need to update parsing logic in `attendance_scraper.py`.
- If deploying to Vercel (or another host), ensure environment variables (if any) are correctly set.

## Deployment
This project is ready for deployment. Steps may include:
- Push to a GitHub repository.
- Connect repository to hosting provider (e.g. Vercel).
- Configure build settings (make sure `python` version corresponds to `runtime.txt`).
- Add any needed secrets/environment variables.
- Deploy and test live.

Live demo : [jntua-attendance-app.vercel.app](https://jntua-attendance-app.vercel.app)

## Contributing
Contributions and suggestions are welcome! If you want to:
- Report bugs
- Request features
- Submit pull requests

Please fork the repo, create a branch, and submit your PR. Make sure to document changes and test them.

## License
Specify here the license under which your project is released (e.g. MIT, Apache-2.0).
Example:
```
MIT License
Copyright (c) 2025 Chanikya-WebDev
Permission is hereby granted, free of charge, to any person obtaining a copy…
```

## Contact
Chanikya (Chanikya-WebDev)
GitHub: [@Chanikya-WebDev](https://github.com/Chanikya-WebDev)
Email: jchanikya06@gmail.com
Thank you for checking out the project!
Happy coding 😊
