<<<<<<< HEAD
# TaskFlow Office Suite — Streamlit edition

This is a Python/Streamlit rebuild of the TaskFlow Office Suite.

## Features
- Account registration and sign-in
- Dashboard metrics
- Active and completed projects
- Project workspace with a three-column task board
- Task creation, assignment, editing, deletion, priority, due dates and status
- Project members and admin/member roles
- Meeting scheduling and completion
- SQLite persistence while the app's filesystem persists

## Run locally
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

Demo login:
- Email: `demo@taskflow.local`
- Password: `taskflow123`

## Deploy on Streamlit Community Cloud
1. Create a GitHub repository for this Streamlit version.
2. Upload `app.py`, `requirements.txt`, and this README.
3. In Streamlit Community Cloud, choose **New app**, select the repository and `app.py`.
4. Deploy.

## Important database note
The app creates `taskflow.db` automatically. Streamlit Community Cloud's local filesystem should not be treated as permanent storage; a restart/redeploy can reset local SQLite data. For a real multi-user office app, connect a persistent hosted database (for example, PostgreSQL or a managed database) before relying on it for important company data. Do not commit a database containing real user passwords or private business data to GitHub.

The existing Node/React SQLite database is not automatically imported by this Streamlit rebuild. The demo account and sample project are created on first run.
=======
# TaskFlow Office Suite

A local-first office workspace with projects, completed-project archive, team tasks, meetings, and email OTP sign-in.

## Requirements
- Node.js 22 LTS recommended
- Windows, macOS, or Linux

## Setup
1. Extract the ZIP and open this folder in VS Code.
2. Open a terminal in this folder and run `npm install`.
3. Copy `.env.example` to `.env` and set a long random `JWT_SECRET`.
4. Configure SMTP values in `.env` to send real OTP emails (Gmail users should use a Google App Password, not their normal account password).
5. Run `npm run dev`.
6. Open `http://localhost:5173`.

## Email OTP
After password validation, TaskFlow sends a 6-digit OTP that expires after five minutes. Codes are single-use, limited to five failed attempts, and resend is rate-limited to once every 30 seconds. If SMTP is not configured, OTPs are printed to the API terminal for local development only. Do not use console OTP mode in production.

## Demo
- Email: `demo@taskflow.local`
- Password: `taskflow123`
- With SMTP configured, demo sign-in also requires the email OTP.

## Features
- Password + email OTP authentication
- Active and completed project views
- Project tasks with priority, assignee, due date and status
- Meeting scheduling with agenda, date, time, duration, location and optional video link
- Overview metrics and personal task list
- SQLite persistence in `server/taskflow.db`

## Important production notes
This is a development-ready MVP, not a hardened enterprise deployment. Before public deployment, configure a strong secret, SMTP, HTTPS, backups, rate limiting at the edge, audit logging, and a proper employee invitation/attendee workflow. The meeting attendee selector and automated calendar invitations are not yet implemented.
>>>>>>> 705d732881f5938beb26611074956d5a5bbcd6fe
