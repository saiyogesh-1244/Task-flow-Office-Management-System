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
