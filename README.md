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
