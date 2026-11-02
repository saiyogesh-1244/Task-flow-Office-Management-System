TASKFLOW NEON ANIME UPDATE

This update changes authentication to normal email + password (no OTP).
It also applies a neon anime-inspired dark visual theme.

Apply these files to your existing project:
- server/index.js
- server/db.js
- client/src/main.jsx
- client/src/style.css
- client/index.html
- vite.config.js

IMPORTANT:
1. Stop the running app before replacing files.
2. Back up your existing server/taskflow.db. Do not replace it.
3. Copy these files into the matching locations in your existing taskflow-office folder.
4. From the project root run: npm.cmd install
5. Then run: npm.cmd run dev
6. Open http://localhost:5173/

The existing demo account remains:
demo@taskflow.local
taskflow123

New registrations use the password they choose (minimum 8 characters).
Passwords continue to be stored as bcrypt hashes.
New users are not automatically granted admin rights.
