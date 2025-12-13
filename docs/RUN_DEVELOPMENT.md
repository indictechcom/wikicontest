# Running WikiContest in Development Mode

This guide explains how to run both the Flask backend and Vue.js frontend during development.

## Option 1: Development Mode (Recommended)

Run both servers separately for the best development experience with hot reload.

### Step 1: Start Flask Backend

Open a terminal and run:

```bash
cd backend
python main.py
```

Flask will start on `http://localhost:5000`

### Step 2: Start Vue.js Frontend

Open a **second terminal** and run:

```bash
cd frontend
npm install  # Only needed first time
npm run dev
```

Vue.js dev server will start on `http://localhost:5173`

### Step 3: Access the Application

- **Frontend (Vue.js)**: http://localhost:5173
- **Backend API**: http://localhost:5000/api

The Vue.js dev server automatically proxies API requests to Flask, so you can use `http://localhost:5173` for everything.

### Benefits

- ✅ Hot module replacement (instant updates)
- ✅ Fast development builds
- ✅ Better error messages
- ✅ Vue DevTools support

---

## Option 2: Production Build (Flask Serves Everything)

Build Vue.js and let Flask serve the built files (like before).

### Step 1: Build Vue.js Frontend

```bash
cd frontend
npm install  # Only needed first time
npm run build
```

This creates a `dist/` directory with production files.

### Step 2: Start Flask Backend

```bash
cd backend
python main.py
```

Flask will automatically detect and serve the built Vue.js files from `frontend/dist/`.

### Step 3: Access the Application

- **Application**: http://localhost:5000

### Benefits

- ✅ Single server to run
- ✅ Production-like environment
- ✅ No need for two terminals

### Note

After making frontend changes, you need to rebuild:
```bash
cd frontend
npm run build
```

---

## Quick Start Scripts

### Windows (PowerShell)

Create `start-dev.ps1`:

```powershell
# Start Flask backend
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend; python main.py"

# Wait a moment
Start-Sleep -Seconds 2

# Start Vue.js frontend
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; npm run dev"
```

Run with: `.\start-dev.ps1`

### Linux/Mac (Bash)

Create `start-dev.sh`:

```bash
#!/bin/bash

# Start Flask backend in background
cd backend
python main.py &
BACKEND_PID=$!

# Wait a moment
sleep 2

# Start Vue.js frontend
cd ../frontend
npm run dev

# Cleanup on exit
trap "kill $BACKEND_PID" EXIT
```

Make executable: `chmod +x start-dev.sh`
Run with: `./start-dev.sh`

---

## Troubleshooting

### Port Already in Use

**Flask (port 5000):**
- Change port in `backend/main.py`: `app.run(port=5001)`

**Vue.js (port 5173):**
- Change port in `frontend/vite.config.js`: `server: { port: 5174 }`

### API Requests Failing

- Ensure Flask is running on port 5000
- Check CORS configuration in `backend/app/__init__.py`
- Verify proxy settings in `frontend/vite.config.js`

### Module Not Found Errors

```bash
cd frontend
npm install
```

### Build Errors

- Ensure Node.js 16+ is installed: `node --version`
- Clear node_modules and reinstall: `rm -rf node_modules && npm install`

---

## Recommended Workflow

For daily development, use **Option 1** (separate servers):

1. Terminal 1: `cd backend && python main.py`
2. Terminal 2: `cd frontend && npm run dev`
3. Open browser: http://localhost:5173

This gives you:
- Instant frontend updates
- Fast development experience
- Better debugging tools

For testing production builds, use **Option 2** (Flask serves built files).

