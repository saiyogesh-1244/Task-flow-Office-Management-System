import os
import sqlite3
import hashlib
import hmac
import secrets
from datetime import date, datetime, time, timedelta

import streamlit as st
import pandas as pd

st.set_page_config(page_title="TaskFlow Office Suite", page_icon="📋", layout="wide")

DB_PATH = os.getenv("TASKFLOW_DB", "taskflow.db")

def db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 240_000)
    return f"{salt}${digest.hex()}"

def verify_password(password: str, stored: str) -> bool:
    try:
        salt, digest = stored.split("$", 1)
        check = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 240_000).hex()
        return hmac.compare_digest(check, digest)
    except Exception:
        return False

def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            password TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS projects(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            owner_id INTEGER NOT NULL REFERENCES users(id),
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            completed_at TEXT
        );
        CREATE TABLE IF NOT EXISTS project_members(
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            role TEXT NOT NULL DEFAULT 'member',
            PRIMARY KEY(project_id,user_id)
        );
        CREATE TABLE IF NOT EXISTS tasks(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'todo',
            priority TEXT NOT NULL DEFAULT 'medium',
            assignee_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            due_date TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS meetings(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            agenda TEXT DEFAULT '',
            meeting_date TEXT NOT NULL,
            meeting_time TEXT NOT NULL,
            duration INTEGER NOT NULL DEFAULT 30,
            location TEXT DEFAULT '',
            meeting_link TEXT DEFAULT '',
            organizer_id INTEGER NOT NULL REFERENCES users(id),
            status TEXT NOT NULL DEFAULT 'scheduled',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS meeting_attendees(
            meeting_id INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            PRIMARY KEY(meeting_id,user_id)
        );
        """)
        demo = con.execute("SELECT id FROM users WHERE email=?", ("demo@taskflow.local",)).fetchone()
        if not demo:
            cur = con.execute(
                "INSERT INTO users(email,name,password) VALUES(?,?,?)",
                ("demo@taskflow.local", "Demo Admin", hash_password("taskflow123"))
            )
            uid = cur.lastrowid
            pcur = con.execute(
                "INSERT INTO projects(name,description,owner_id) VALUES(?,?,?)",
                ("Website Launch", "Plan and deliver the new company website.", uid)
            )
            pid = pcur.lastrowid
            con.execute("INSERT INTO project_members(project_id,user_id,role) VALUES(?,?,?)", (pid, uid, "admin"))
            con.execute(
                "INSERT INTO tasks(project_id,title,description,status,priority,assignee_id,due_date) VALUES(?,?,?,?,?,?,?)",
                (pid, "Create landing page", "Design and build the public landing page.", "in_progress", "high", uid, (date.today()+timedelta(days=3)).isoformat())
            )
            con.execute(
                "INSERT INTO tasks(project_id,title,description,status,priority,assignee_id,due_date) VALUES(?,?,?,?,?,?,?)",
                (pid, "Prepare launch checklist", "Collect launch requirements and owners.", "todo", "medium", uid, (date.today()+timedelta(days=7)).isoformat())
            )

def current_user():
    return st.session_state.get("user")

def login_screen():
    st.markdown("<div class='brand'>TASKFLOW <span>OFFICE SUITE</span></div>", unsafe_allow_html=True)
    left, right = st.columns([1.15, 1])
    with left:
        st.markdown("## Bring your team's work into focus.")
        st.write("Projects, people, meetings and progress — organized in one workspace.")
        st.info("Demo account\n\nEmail: `demo@taskflow.local`\n\nPassword: `taskflow123`")
    with right:
        mode = st.radio("Account", ["Sign in", "Create account"], horizontal=True)
        with st.form("auth_form"):
            name = st.text_input("Full name") if mode == "Create account" else ""
            email = st.text_input("Work email", value="demo@taskflow.local" if mode == "Sign in" else "")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Continue" if mode == "Sign in" else "Create account", use_container_width=True)
        if submitted:
            email = email.strip().lower()
            if mode == "Create account":
                if len(name.strip()) < 2 or "@" not in email or len(password) < 8:
                    st.error("Enter your name, a valid email and a password with at least 8 characters.")
                else:
                    try:
                        with db() as con:
                            cur = con.execute(
                                "INSERT INTO users(name,email,password) VALUES(?,?,?)",
                                (name.strip(), email, hash_password(password))
                            )
                            uid = cur.lastrowid
                        st.session_state.user = {"id": uid, "name": name.strip(), "email": email}
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("That email is already registered.")
            else:
                with db() as con:
                    user = con.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
                if user and verify_password(password, user["password"]):
                    st.session_state.user = {"id": user["id"], "name": user["name"], "email": user["email"]}
                    st.rerun()
                else:
                    st.error("Email or password is incorrect.")

def get_projects(uid, status=None):
    with db() as con:
        sql = """SELECT p.*, pm.role,
                 (SELECT COUNT(*) FROM tasks t WHERE t.project_id=p.id) task_count
                 FROM projects p JOIN project_members pm ON pm.project_id=p.id
                 WHERE pm.user_id=?"""
        args = [uid]
        if status:
            sql += " AND p.status=?"
            args.append(status)
        sql += " ORDER BY p.created_at DESC"
        return con.execute(sql, args).fetchall()

def get_tasks(uid, project_id=None):
    with db() as con:
        sql = """SELECT t.*, p.name AS project_name, u.name AS assignee_name
                 FROM tasks t JOIN projects p ON p.id=t.project_id
                 JOIN project_members pm ON pm.project_id=p.id
                 LEFT JOIN users u ON u.id=t.assignee_id
                 WHERE pm.user_id=?"""
        args = [uid]
        if project_id is not None:
            sql += " AND t.project_id=?"
            args.append(project_id)
        sql += " ORDER BY t.due_date IS NULL, t.due_date, t.created_at DESC"
        return con.execute(sql, args).fetchall()

def get_meetings(uid):
    with db() as con:
        return con.execute("""
            SELECT DISTINCT m.*, u.name AS organizer_name
            FROM meetings m JOIN users u ON u.id=m.organizer_id
            LEFT JOIN meeting_attendees a ON a.meeting_id=m.id
            WHERE m.organizer_id=? OR a.user_id=?
            ORDER BY m.meeting_date,m.meeting_time
        """, (uid, uid)).fetchall()

def create_project(uid, name, description):
    with db() as con:
        cur = con.execute(
            "INSERT INTO projects(name,description,owner_id) VALUES(?,?,?)",
            (name.strip(), description.strip(), uid)
        )
        con.execute(
            "INSERT INTO project_members(project_id,user_id,role) VALUES(?,?,?)",
            (cur.lastrowid, uid, "admin")
        )

def project_members(project_id):
    with db() as con:
        return con.execute("""
            SELECT u.id,u.name,u.email,pm.role
            FROM project_members pm JOIN users u ON u.id=pm.user_id
            WHERE pm.project_id=? ORDER BY pm.role,u.name
        """, (project_id,)).fetchall()

def main_app():
    user = current_user()
    uid = user["id"]
    with st.sidebar:
        st.markdown("## 📋 TASKFLOW")
        st.caption("OFFICE SUITE")
        st.divider()
        page = st.radio(
            "WORKSPACE",
            ["Overview", "Active projects", "Completed projects", "Meetings", "My tasks"],
            label_visibility="collapsed"
        )
        st.divider()
        st.write(f"**{user['name']}**")
        st.caption(user["email"])
        if st.button("Sign out", use_container_width=True):
            st.session_state.pop("user", None)
            st.rerun()

    projects = get_projects(uid)
    active = [p for p in projects if p["status"] != "completed"]
    completed = [p for p in projects if p["status"] == "completed"]
    tasks = get_tasks(uid)
    meetings = get_meetings(uid)
    today = date.today().isoformat()
    my_tasks = [t for t in tasks if t["assignee_id"] == uid and t["status"] != "done"]
    overdue = [t for t in tasks if t["status"] != "done" and t["due_date"] and t["due_date"] < today]
    upcoming = [m for m in meetings if m["status"] == "scheduled" and m["meeting_date"] >= today]

    st.markdown(f"# {page}")
    st.caption(f"Company workspace · Welcome, {user['name'].split()[0]}")

    if page == "Overview":
        cols = st.columns(4)
        metrics = [
            ("Active projects", len(active)),
            ("Completed projects", len(completed)),
            ("My open tasks", len(my_tasks)),
            ("Upcoming meetings", len(upcoming)),
        ]
        for col, (label, value) in zip(cols, metrics):
            col.metric(label, value)
        st.subheader("Active projects")
        show_project_cards(active[:4], uid)
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("My open tasks")
            show_task_table(my_tasks[:6])
        with c2:
            st.subheader("Upcoming meetings")
            show_meeting_list(upcoming[:5], uid)
        if overdue:
            st.warning(f"You have {len(overdue)} overdue task(s).")

    elif page in ("Active projects", "Completed projects"):
        rows = active if page == "Active projects" else completed
        c1, c2 = st.columns([2, 1])
        with c1:
            st.write("Plan new work, coordinate owners and keep delivery moving.")
        with c2:
            with st.popover("＋ New project", use_container_width=True):
                with st.form("new_project"):
                    name = st.text_input("Project name")
                    desc = st.text_area("Project overview")
                    if st.form_submit_button("Create project"):
                        if len(name.strip()) < 2:
                            st.error("Project name must contain at least 2 characters.")
                        else:
                            create_project(uid, name, desc)
                            st.success("Project created.")
                            st.rerun()
        show_project_cards(rows, uid, allow_create=False)

    elif page == "Meetings":
        c1, c2 = st.columns([2, 1])
        with c1:
            st.write("Schedule discussions, reviews and team check-ins.")
        with c2:
            with st.popover("＋ Schedule meeting", use_container_width=True):
                with st.form("new_meeting"):
                    title = st.text_input("Meeting title")
                    agenda = st.text_area("Agenda")
                    meeting_date = st.date_input("Date", value=date.today())
                    meeting_time = st.time_input("Time", value=time(10, 0))
                    duration = st.selectbox("Duration", [15, 30, 45, 60, 90])
                    location = st.text_input("Room / location")
                    link = st.text_input("Video meeting link")
                    if st.form_submit_button("Schedule meeting"):
                        if len(title.strip()) < 2:
                            st.error("Enter a meeting title.")
                        else:
                            with db() as con:
                                con.execute("""INSERT INTO meetings
                                    (title,agenda,meeting_date,meeting_time,duration,location,meeting_link,organizer_id)
                                    VALUES(?,?,?,?,?,?,?,?)""",
                                    (title.strip(), agenda, meeting_date.isoformat(), meeting_time.strftime("%H:%M"),
                                     duration, location, link, uid))
                                mid = con.execute("SELECT last_insert_rowid()").fetchone()[0]
                                con.execute("INSERT OR IGNORE INTO meeting_attendees(meeting_id,user_id) VALUES(?,?)", (mid, uid))
                            st.success("Meeting scheduled.")
                            st.rerun()
        show_meeting_list(meetings, uid, full=True)

    elif page == "My tasks":
        st.write("All open work currently assigned to you.")
        show_task_table(my_tasks, full=True)

def show_project_cards(rows, uid, allow_create=True):
    if not rows:
        st.info("No projects here yet.")
        return
    cols = st.columns(2)
    for i, p in enumerate(rows):
        with cols[i % 2]:
            with st.container(border=True):
                st.markdown(f"### {p['name']}")
                st.caption(f"{p['status'].title()} · {p['task_count']} tasks · Created {p['created_at'][:10]}")
                st.write(p["description"] or "No project overview provided.")
                if st.button("Open workspace →", key=f"open_{p['id']}", use_container_width=True):
                    st.session_state.project_id = p["id"]
                    st.session_state.page_project = True
                    st.rerun()
                if p["role"] == "admin":
                    label = "Reopen project" if p["status"] == "completed" else "Mark completed"
                    if st.button(label, key=f"archive_{p['id']}"):
                        new_status = "active" if p["status"] == "completed" else "completed"
                        with db() as con:
                            con.execute("UPDATE projects SET status=?, completed_at=? WHERE id=?",
                                        (new_status, datetime.now().isoformat() if new_status == "completed" else None, p["id"]))
                        st.rerun()

def project_workspace(uid):
    pid = st.session_state.get("project_id")
    with db() as con:
        p = con.execute("""
            SELECT p.*,pm.role FROM projects p
            JOIN project_members pm ON pm.project_id=p.id
            WHERE p.id=? AND pm.user_id=?
        """, (pid, uid)).fetchone()
    if not p:
        st.error("Project not found or access denied.")
        if st.button("Back to workspace"):
            st.session_state.page_project = False
            st.rerun()
        return
    if st.button("← Back to workspace"):
        st.session_state.page_project = False
        st.rerun()
    st.markdown(f"# {p['name']}")
    st.write(p["description"])
    tasks = get_tasks(uid, pid)
    members = project_members(pid)
    c1, c2 = st.columns([2, 1])
    with c1:
        st.subheader("Project board")
    with c2:
        with st.popover("＋ Add task", use_container_width=True):
            with st.form("new_task"):
                title = st.text_input("Task title")
                desc = st.text_area("Details")
                priority = st.selectbox("Priority", ["low", "medium", "high"], index=1)
                status = st.selectbox("Status", ["todo", "in_progress", "done"])
                choices = {f"{m['name']} ({m['email']})": m["id"] for m in members}
                assignee_label = st.selectbox("Assign to", ["Unassigned"] + list(choices))
                due = st.date_input("Due date", value=None)
                if st.form_submit_button("Save task"):
                    if len(title.strip()) < 2:
                        st.error("Task title must contain at least 2 characters.")
                    else:
                        assignee_id = choices.get(assignee_label)
                        due_date = due.isoformat() if due else None
                        with db() as con:
                            con.execute("""INSERT INTO tasks
                                (project_id,title,description,status,priority,assignee_id,due_date)
                                VALUES(?,?,?,?,?,?,?)""",
                                (pid, title.strip(), desc, status, priority, assignee_id, due_date))
                        st.success("Task added.")
                        st.rerun()
    columns = st.columns(3)
    for col, (status, label) in zip(columns, [("todo", "To do"), ("in_progress", "In progress"), ("done", "Completed")]):
        with col:
            st.markdown(f"### {label}")
            for task in [t for t in tasks if t["status"] == status]:
                with st.container(border=True):
                    st.caption(f"{task['priority'].upper()} PRIORITY")
                    st.markdown(f"**{task['title']}**")
                    if task["description"]:
                        st.write(task["description"])
                    st.caption(f"{task['assignee_name'] or 'Unassigned'} · Due {task['due_date'] or 'Not set'}")
                    options = ["todo", "in_progress", "done"]
                    new_status = st.selectbox("Status", options, index=options.index(status), key=f"status_{task['id']}")
                    if new_status != status:
                        with db() as con:
                            con.execute("UPDATE tasks SET status=? WHERE id=?", (new_status, task["id"]))
                        st.rerun()
                    if p["role"] == "admin":
                        with st.expander("Edit / delete"):
                            new_title = st.text_input("Title", task["title"], key=f"title_{task['id']}")
                            new_desc = st.text_area("Description", task["description"], key=f"desc_{task['id']}")
                            new_priority = st.selectbox("Priority", ["low", "medium", "high"],
                                index=["low", "medium", "high"].index(task["priority"]), key=f"priority_{task['id']}")
                            if st.button("Save changes", key=f"save_{task['id']}"):
                                with db() as con:
                                    con.execute("UPDATE tasks SET title=?,description=?,priority=? WHERE id=?",
                                                (new_title, new_desc, new_priority, task["id"]))
                                st.rerun()
                            if st.button("Delete task", key=f"delete_{task['id']}"):
                                with db() as con:
                                    con.execute("DELETE FROM tasks WHERE id=?", (task["id"],))
                                st.rerun()
    st.divider()
    st.subheader("Project members")
    if members:
        st.dataframe(pd.DataFrame([dict(m) for m in members])[["name", "email", "role"]], use_container_width=True, hide_index=True)
    if p["role"] == "admin":
        with st.expander("Add a registered member"):
            with st.form("add_member"):
                email = st.text_input("Member email")
                role = st.selectbox("Role", ["member", "admin"])
                if st.form_submit_button("Add member"):
                    with db() as con:
                        target = con.execute("SELECT id FROM users WHERE email=?", (email.strip().lower(),)).fetchone()
                        if not target:
                            st.error("No account found. Ask them to register first.")
                        else:
                            con.execute("INSERT OR REPLACE INTO project_members(project_id,user_id,role) VALUES(?,?,?)",
                                        (pid, target["id"], role))
                            st.success("Member added.")
                            st.rerun()

def show_task_table(rows, full=False):
    if not rows:
        st.info("No open tasks assigned to you.")
        return
    data = []
    for t in rows:
        data.append({
            "Task": t["title"],
            "Project": t["project_name"],
            "Assignee": t["assignee_name"] or "Unassigned",
            "Priority": t["priority"].title(),
            "Status": t["status"].replace("_", " ").title(),
            "Due date": t["due_date"] or "—"
        })
    st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

def show_meeting_list(rows, uid, full=False):
    if not rows:
        st.info("No meetings scheduled.")
        return
    for m in rows:
        with st.container(border=True):
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.markdown(f"**{m['title']}**")
                st.caption(f"{m['meeting_date']} · {m['meeting_time']} · {m['duration']} min")
                if m["agenda"]:
                    st.write(m["agenda"])
                if m["location"]:
                    st.caption(f"Location: {m['location']}")
                if m["meeting_link"]:
                    st.markdown(f"[Join meeting]({m['meeting_link']})")
            with col2:
                st.caption(m["status"].title())
            with col3:
                if m["status"] == "scheduled" and m["organizer_id"] == uid:
                    if st.button("Mark done", key=f"meeting_done_{m['id']}"):
                        with db() as con:
                            con.execute("UPDATE meetings SET status='completed' WHERE id=?", (m["id"],))
                        st.rerun()

def main():
    init_db()
    st.markdown("""
    <style>
    .stApp { background: #f5f7fb; color: #17243a; }
    [data-testid="stSidebar"] { background: #10213b; }
    [data-testid="stSidebar"] * { color: #f4f7fb !important; }
    .brand { font-size: 1.55rem; font-weight: 800; letter-spacing: .08em; color: #142844; margin-bottom: 2rem; }
    .brand span { display:block; font-size:.72rem; letter-spacing:.22em; color:#b38a45; }
    div[data-testid="stMetric"] { background:white; border:1px solid #e6eaf1; padding:1rem; border-radius:14px; }
    .stButton>button, .stFormSubmitButton>button { border-radius:9px; }
    </style>
    """, unsafe_allow_html=True)
    if not current_user():
        login_screen()
    else:
        if st.session_state.get("page_project"):
            project_workspace(st.session_state.user["id"])
        else:
            main_app()

if __name__ == "__main__":
    main()
