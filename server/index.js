
import express from 'express';
import cors from 'cors';
import jwt from 'jsonwebtoken';
import bcrypt from 'bcryptjs';
import { z } from 'zod';
import db from './db.js';

const app = express();
const PORT = process.env.PORT || 8080;
const SECRET = process.env.JWT_SECRET || 'dev-only-change-this-secret';

app.use(cors({ origin: true, credentials: true }));
app.use(express.json());

const auth = (req, res, next) => {
  try {
    const h = req.headers.authorization || '';
    req.user = jwt.verify(
      h.startsWith('Bearer ') ? h.slice(7) : '',
      SECRET
    );
    next();
  } catch {
    return res.status(401).json({ error: 'Please log in to continue.' });
  }
};

const member = (req, res, next) => {
  const row = db.prepare(
    'SELECT role FROM project_members WHERE project_id=? AND user_id=?'
  ).get(Number(req.params.id), req.user.id);

  if (!row) {
    return res.status(403).json({ error: 'You are not a member of this project.' });
  }

  req.role = row.role;
  next();
};

const admin = (req, res, next) => {
  if (req.role !== 'admin') {
    return res.status(403).json({ error: 'Admin permission required.' });
  }
  next();
};

const wrap = fn => (req, res) => {
  Promise.resolve()
    .then(() => fn(req, res))
    .catch(e => {
      if (e instanceof z.ZodError) {
        return res.status(400).json({
          error: e.issues[0]?.message || 'Invalid input.'
        });
      }
      console.error(e);
      res.status(500).json({ error: 'Something went wrong on the server.' });
    });
};

function publicUser(u) {
  return { id: u.id, name: u.name, email: u.email };
}

app.get('/api/health', (req, res) => {
  res.json({ ok: true, mailConfigured: false });
});

// REGISTER
app.post('/api/auth/register', wrap((req, res) => {
  const v = z.object({
    name: z.string().min(2).max(80),
    email: z.string().email(),
    password: z.string().min(8)
  }).parse(req.body);

  const email = v.email.toLowerCase();

  if (db.prepare('SELECT id FROM users WHERE email=?').get(email)) {
    return res.status(409).json({ error: 'Email is already registered.' });
  }

  const r = db.prepare(
    'INSERT INTO users(name,email,password) VALUES(?,?,?)'
  ).run(v.name, email, bcrypt.hashSync(v.password, 12));

  const user = publicUser({
    id: Number(r.lastInsertRowid),
    name: v.name,
    email
  });

  res.status(201).json({
    token: jwt.sign(user, SECRET, { expiresIn: '8h' }),
    user
  });
}));

// LOGIN
app.post('/api/auth/login', wrap((req, res) => {
  const v = z.object({
    email: z.string().email(),
    password: z.string().min(1)
  }).parse(req.body);

  const u = db.prepare('SELECT * FROM users WHERE email=?')
    .get(v.email.toLowerCase());

  if (!u || !bcrypt.compareSync(v.password, u.password)) {
    return res.status(401).json({
      error: 'Email or password is incorrect.'
    });
  }

  const user = publicUser(u);

  res.json({
    token: jwt.sign(user, SECRET, { expiresIn: '8h' }),
    user
  });
}));

// GET LOGGED-IN USER — FIXED ROUTE
app.get('/api/auth/me', auth, (req, res) => {
  res.json({
    user: {
      id: req.user.id,
      name: req.user.name,
      email: req.user.email
    }
  });
});

// DASHBOARD
app.get('/api/dashboard', auth, wrap((req, res) => {
  const id = req.user.id;

  const projects = db.prepare(`
    SELECT p.*, pm.role,
    (SELECT COUNT(*) FROM tasks t WHERE t.project_id=p.id) task_count
    FROM projects p
    JOIN project_members pm ON pm.project_id=p.id
    WHERE pm.user_id=?
    ORDER BY p.created_at DESC
  `).all(id);

  const tasks = db.prepare(`
    SELECT t.*, p.name project_name, u.name assignee_name
    FROM tasks t
    JOIN projects p ON p.id=t.project_id
    LEFT JOIN users u ON u.id=t.assignee_id
    JOIN project_members pm ON pm.project_id=p.id
    WHERE pm.user_id=?
    ORDER BY t.due_date IS NULL, t.due_date
  `).all(id);

  const today = new Date().toISOString().slice(0, 10);

  res.json({
    projects,
    tasks,
    stats: {
      projects: projects.filter(p => p.status === 'active').length,
      completedProjects: projects.filter(p => p.status === 'completed').length,
      myTasks: tasks.filter(t => t.assignee_id === id && t.status !== 'done').length,
      inProgress: tasks.filter(t => t.status === 'in_progress').length,
      overdue: tasks.filter(
        t => t.status !== 'done' && t.due_date && t.due_date < today
      ).length,
      meetings: db.prepare(`
        SELECT COUNT(*) n FROM meetings
        WHERE organizer_id=? AND meeting_date>=date('now')
        AND status='scheduled'
      `).get(id).n
    }
  });
}));

// PROJECTS
app.get('/api/projects', auth, (req, res) => {
  res.json(db.prepare(`
    SELECT p.*, pm.role,
    (SELECT COUNT(*) FROM tasks t WHERE t.project_id=p.id) task_count
    FROM projects p
    JOIN project_members pm ON pm.project_id=p.id
    WHERE pm.user_id=?
    ORDER BY p.created_at DESC
  `).all(req.user.id));
});

app.post('/api/projects', auth, wrap((req, res) => {
  const v = z.object({
    name: z.string().min(2).max(100),
    description: z.string().max(500).optional()
  }).parse(req.body);

  const r = db.prepare(
    'INSERT INTO projects(name,description,owner_id) VALUES(?,?,?)'
  ).run(v.name, v.description || '', req.user.id);

  db.prepare(`
    INSERT INTO project_members(project_id,user_id,role)
    VALUES(?,?,'admin')
  `).run(r.lastInsertRowid, req.user.id);

  res.status(201).json(
    db.prepare('SELECT * FROM projects WHERE id=?').get(r.lastInsertRowid)
  );
}));

app.patch('/api/projects/:id', auth, member, admin, wrap((req, res) => {
  const v = z.object({
    name: z.string().min(2).max(100).optional(),
    description: z.string().max(500).optional(),
    status: z.enum(['active', 'completed']).optional()
  }).parse(req.body);

  const p = db.prepare('SELECT * FROM projects WHERE id=?').get(req.params.id);
  const n = { ...p, ...v };

  db.prepare(`
    UPDATE projects SET name=?,description=?,status=?,completed_at=?
    WHERE id=?
  `).run(
    n.name,
    n.description,
    n.status,
    n.status === 'completed'
      ? (p.completed_at || new Date().toISOString())
      : null,
    req.params.id
  );

  res.json(db.prepare('SELECT * FROM projects WHERE id=?').get(req.params.id));
}));

app.get('/api/projects/:id/members', auth, member, (req, res) => {
  res.json(db.prepare(`
    SELECT u.id,u.name,u.email,pm.role
    FROM project_members pm
    JOIN users u ON u.id=pm.user_id
    WHERE pm.project_id=?
    ORDER BY pm.role,u.name
  `).all(req.params.id));
});

app.post('/api/projects/:id/members', auth, member, admin, wrap((req, res) => {
  const v = z.object({
    email: z.string().email(),
    role: z.enum(['admin', 'member']).default('member')
  }).parse(req.body);

  const u = db.prepare('SELECT id FROM users WHERE email=?')
    .get(v.email.toLowerCase());

  if (!u) {
    return res.status(404).json({
      error: 'No account found with that email. Ask them to register first.'
    });
  }

  db.prepare(`
    INSERT INTO project_members(project_id,user_id,role)
    VALUES(?,?,?)
    ON CONFLICT(project_id,user_id)
    DO UPDATE SET role=excluded.role
  `).run(req.params.id, u.id, v.role);

  res.status(201).json({ ok: true });
}));

app.patch('/api/projects/:id/members/:userId', auth, member, admin, wrap((req, res) => {
  const v = z.object({
    role: z.enum(['admin', 'member'])
  }).parse(req.body);

  db.prepare(
    'UPDATE project_members SET role=? WHERE project_id=? AND user_id=?'
  ).run(v.role, req.params.id, req.params.userId);

  res.json({ ok: true });
}));

app.delete('/api/projects/:id/members/:userId', auth, member, admin, (req, res) => {
  if (Number(req.params.userId) === req.user.id) {
    return res.status(400).json({ error: 'You cannot remove yourself.' });
  }

  db.prepare(
    'DELETE FROM project_members WHERE project_id=? AND user_id=?'
  ).run(req.params.id, req.params.userId);

  res.json({ ok: true });
});

// TASKS
app.get('/api/projects/:id/tasks', auth, member, (req, res) => {
  res.json(db.prepare(`
    SELECT t.*,u.name assignee_name
    FROM tasks t
    LEFT JOIN users u ON u.id=t.assignee_id
    WHERE t.project_id=?
    ORDER BY t.created_at DESC
  `).all(req.params.id));
});

app.post('/api/projects/:id/tasks', auth, member, wrap((req, res) => {
  const v = z.object({
    title: z.string().min(2).max(150),
    description: z.string().max(1000).optional(),
    status: z.enum(['todo', 'in_progress', 'done']).default('todo'),
    priority: z.enum(['low', 'medium', 'high']).default('medium'),
    assigneeId: z.number().int().positive().nullable().optional(),
    dueDate: z.string().nullable().optional()
  }).parse(req.body);

  const r = db.prepare(`
    INSERT INTO tasks(project_id,title,description,status,priority,assignee_id,due_date)
    VALUES(?,?,?,?,?,?,?)
  `).run(
    req.params.id,
    v.title,
    v.description || '',
    v.status,
    v.priority,
    v.assigneeId || null,
    v.dueDate || null
  );

  res.status(201).json(
    db.prepare('SELECT * FROM tasks WHERE id=?').get(r.lastInsertRowid)
  );
}));

app.patch('/api/projects/:id/tasks/:taskId', auth, member, wrap((req, res) => {
  const v = z.object({
    title: z.string().min(2).max(150).optional(),
    description: z.string().max(1000).optional(),
    status: z.enum(['todo', 'in_progress', 'done']).optional(),
    priority: z.enum(['low', 'medium', 'high']).optional(),
    assigneeId: z.number().int().positive().nullable().optional(),
    dueDate: z.string().nullable().optional()
  }).parse(req.body);

  const t = db.prepare(
    'SELECT * FROM tasks WHERE id=? AND project_id=?'
  ).get(req.params.taskId, req.params.id);

  if (!t) return res.status(404).json({ error: 'Task not found.' });

  const n = { ...t, ...v };

  db.prepare(`
    UPDATE tasks SET title=?,description=?,status=?,priority=?,
    assignee_id=?,due_date=?,updated_at=CURRENT_TIMESTAMP
    WHERE id=?
  `).run(
    n.title,
    n.description,
    n.status,
    n.priority,
    n.assignee_id ?? n.assigneeId,
    n.due_date ?? n.dueDate,
    req.params.taskId
  );

  res.json(db.prepare('SELECT * FROM tasks WHERE id=?').get(req.params.taskId));
}));

app.delete('/api/projects/:id/tasks/:taskId', auth, member, (req, res) => {
  db.prepare(
    'DELETE FROM tasks WHERE id=? AND project_id=?'
  ).run(req.params.taskId, req.params.id);

  res.json({ ok: true });
});

// MEETINGS
app.get('/api/meetings', auth, (req, res) => {
  res.json(db.prepare(`
    SELECT m.*,u.name organizer_name,
    (SELECT GROUP_CONCAT(u2.name, ', ')
     FROM meeting_attendees ma
     JOIN users u2 ON u2.id=ma.user_id
     WHERE ma.meeting_id=m.id) attendees
    FROM meetings m
    JOIN users u ON u.id=m.organizer_id
    WHERE m.organizer_id=?
    OR m.id IN (SELECT meeting_id FROM meeting_attendees WHERE user_id=?)
    ORDER BY m.meeting_date,m.meeting_time
  `).all(req.user.id, req.user.id));
});

app.post('/api/meetings', auth, wrap((req, res) => {
  const v = z.object({
    title: z.string().min(2).max(140),
    agenda: z.string().max(1000).optional(),
    meetingDate: z.string().min(10),
    meetingTime: z.string().min(4),
    duration: z.number().int().min(5).max(480).default(30),
    location: z.string().max(200).optional(),
    meetingLink: z.string().max(500).optional(),
    attendeeIds: z.array(z.number().int().positive()).optional()
  }).parse(req.body);

  const r = db.prepare(`
    INSERT INTO meetings(title,agenda,meeting_date,meeting_time,duration,
    location,meeting_link,organizer_id)
    VALUES(?,?,?,?,?,?,?,?)
  `).run(
    v.title,
    v.agenda || '',
    v.meetingDate,
    v.meetingTime,
    v.duration,
    v.location || '',
    v.meetingLink || '',
    req.user.id
  );

  for (const id of new Set([req.user.id, ...(v.attendeeIds || [])])) {
    db.prepare(
      'INSERT OR IGNORE INTO meeting_attendees(meeting_id,user_id) VALUES(?,?)'
    ).run(r.lastInsertRowid, id);
  }

  res.status(201).json({ id: r.lastInsertRowid });
}));

app.patch('/api/meetings/:id', auth, wrap((req, res) => {
  const m = db.prepare(
    'SELECT * FROM meetings WHERE id=? AND organizer_id=?'
  ).get(req.params.id, req.user.id);

  if (!m) {
    return res.status(404).json({
      error: 'Meeting not found or you are not the organizer.'
    });
  }

  const v = z.object({
    status: z.enum(['scheduled', 'completed', 'cancelled']).optional()
  }).parse(req.body);

  db.prepare('UPDATE meetings SET status=? WHERE id=?')
    .run(v.status || m.status, req.params.id);

  res.json({ ok: true });
}));

app.delete('/api/meetings/:id', auth, (req, res) => {
  db.prepare(
    'DELETE FROM meetings WHERE id=? AND organizer_id=?'
  ).run(req.params.id, req.user.id);

  res.json({ ok: true });
});

// USERS
app.get('/api/users', auth, (req, res) => {
  res.json(db.prepare(
    'SELECT id,name,email FROM users ORDER BY name'
  ).all());
});

app.use((err, req, res, next) => {
  console.error(err);
  res.status(500).json({ error: 'Internal server error.' });
});

app.listen(PORT, () => {
  console.log(`TaskFlow API running at http://localhost:${PORT}`);
});
