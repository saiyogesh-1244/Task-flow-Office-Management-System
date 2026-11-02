import Database from 'better-sqlite3';
import bcrypt from 'bcryptjs';
const db = new Database('server/taskflow.db');
db.pragma('journal_mode = WAL');
db.pragma('foreign_keys = ON');
db.exec(`
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,email TEXT UNIQUE NOT NULL,name TEXT NOT NULL,password TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS projects(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,description TEXT DEFAULT '',owner_id INTEGER NOT NULL REFERENCES users(id),status TEXT NOT NULL DEFAULT 'active',created_at TEXT DEFAULT CURRENT_TIMESTAMP,completed_at TEXT);
CREATE TABLE IF NOT EXISTS project_members(project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,role TEXT NOT NULL DEFAULT 'member' CHECK(role IN ('admin','member')),PRIMARY KEY(project_id,user_id));
CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY AUTOINCREMENT,project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,title TEXT NOT NULL,description TEXT DEFAULT '',status TEXT NOT NULL DEFAULT 'todo' CHECK(status IN ('todo','in_progress','done')),priority TEXT NOT NULL DEFAULT 'medium' CHECK(priority IN ('low','medium','high')),assignee_id INTEGER REFERENCES users(id) ON DELETE SET NULL,due_date TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP,updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS meetings(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,agenda TEXT DEFAULT '',meeting_date TEXT NOT NULL,meeting_time TEXT NOT NULL,duration INTEGER NOT NULL DEFAULT 30,location TEXT DEFAULT '',meeting_link TEXT DEFAULT '',organizer_id INTEGER NOT NULL REFERENCES users(id),status TEXT NOT NULL DEFAULT 'scheduled',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS meeting_attendees(meeting_id INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,PRIMARY KEY(meeting_id,user_id));
CREATE TABLE IF NOT EXISTS login_otps(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,otp_hash TEXT NOT NULL,expires_at INTEGER NOT NULL,attempts INTEGER NOT NULL DEFAULT 0,created_at INTEGER NOT NULL);
`);
// Safe additive migrations for databases created by the earlier TaskFlow version.
const cols = db.prepare('PRAGMA table_info(projects)').all().map(x=>x.name);
if (!cols.includes('status')) db.exec("ALTER TABLE projects ADD COLUMN status TEXT NOT NULL DEFAULT 'active'");
if (!cols.includes('completed_at')) db.exec('ALTER TABLE projects ADD COLUMN completed_at TEXT');
const demo = db.prepare('SELECT id FROM users WHERE email=?').get('demo@taskflow.local');
if (!demo) {
 const info=db.prepare('INSERT INTO users(email,name,password) VALUES(?,?,?)').run('demo@taskflow.local','Demo Admin',bcrypt.hashSync('taskflow123',10));
 const p=db.prepare('INSERT INTO projects(name,description,owner_id) VALUES(?,?,?)').run('Website Launch','Plan and deliver the new company website.',info.lastInsertRowid);
 db.prepare('INSERT INTO project_members(project_id,user_id,role) VALUES(?,?,?)').run(p.lastInsertRowid,info.lastInsertRowid,'admin');
 db.prepare('INSERT INTO tasks(project_id,title,description,status,priority,assignee_id,due_date) VALUES(?,?,?,?,?,?,?)').run(p.lastInsertRowid,'Create landing page','Design and build the public landing page.','in_progress','high',info.lastInsertRowid,new Date(Date.now()+3*86400000).toISOString().slice(0,10));
 db.prepare('INSERT INTO tasks(project_id,title,description,status,priority,assignee_id,due_date) VALUES(?,?,?,?,?,?,?)').run(p.lastInsertRowid,'Prepare launch checklist','Collect launch requirements and owners.','todo','medium',info.lastInsertRowid,new Date(Date.now()+7*86400000).toISOString().slice(0,10));
}
export default db;
