# Running WikiEval in Development Mode

This guide explains how to run the Flask backend and Vue.js frontend during development.



## Development Setup Options

### Option 1: Development Mode (Recommended)

Run both servers separately for the best development experience with hot reload and instant updates.

#### Step 1: Start the Flask Backend

Open a terminal and run:
```bash
cd backend
python main.py
```

Flask will start on `http://localhost:5000`

#### Step 2: Start the Vue.js Frontend

Open a **second terminal** and run:
```bash
cd frontend
npm install  # Only needed the first time
npm run dev
```

The Vue.js dev server will start on `http://localhost:5173`

#### Step 3: Access the Application

- **Frontend (Vue.js):** http://localhost:5173
- **Backend API:** http://localhost:5000/api

The Vue.js dev server automatically proxies API requests to Flask, so you can access everything through `http://localhost:5173`.

#### Benefits of Development Mode

-   Hot module replacement – see changes instantly without refreshing
-   Fast development builds with optimized performance
-   Clear, detailed error messages
-   Full Vue DevTools support for debugging



### Option 2: Production Build (Flask Serves Everything)

Build the Vue.js frontend and let Flask serve the production files. This simulates the production environment.

#### Step 1: Build the Vue.js Frontend
```bash
cd frontend
npm install  # Only needed the first time
npm run build
```

This creates a `dist/` directory containing optimized production files.

#### Step 2: Start the Flask Backend
```bash
cd backend
python main.py
```

Flask will automatically detect and serve the built Vue.js files from `frontend/dist/`.

#### Step 3: Access the Application

- **Application:** http://localhost:5000

#### Benefits of Production Mode

-   Single server to run – simpler setup
-   Production-like environment for testing
-   No need to manage two terminals

#### Important Note

After making frontend changes, you must rebuild:
```bash
cd frontend
npm run build
```

Changes won't appear until you rebuild and refresh the browser.



## Quick Start Scripts

Automate the startup process with these scripts.

### Windows (PowerShell)

Create `start-dev.ps1`:
```powershell
# Start Flask backend
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend; python main.py"

# Wait for Flask to initialize
Start-Sleep -Seconds 2

# Start Vue.js frontend
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; npm run dev"
```

Run with:
```powershell
.\start-dev.ps1
```

### Linux/Mac (Bash)

Create `start-dev.sh`:
```bash
#!/bin/bash

# Start Flask backend in background
cd backend
python main.py &
BACKEND_PID=$!

# Wait for Flask to initialize
sleep 2

# Start Vue.js frontend
cd ../frontend
npm run dev

# Cleanup on exit
trap "kill $BACKEND_PID" EXIT
```

Make the script executable:
```bash
chmod +x start-dev.sh
```

Run with:
```bash
./start-dev.sh
```



## Troubleshooting

### Port Already in Use

#### Flask (port 5000)

Change the port in `backend/main.py`:
```python
app.run(port=5001)
```

#### Vue.js (port 5173)

Change the port in `frontend/vite.config.js`:
```javascript
server: {
  port: 5174
}
```

### API Requests Failing

If API requests are not working:

- Ensure Flask is running on `http://localhost:5000`
- Check CORS configuration in `backend/app/__init__.py`
- Verify proxy settings in `frontend/vite.config.js`
- Check the browser console (F12) for specific error messages

### Module Not Found Errors

Reinstall frontend dependencies:
```bash
cd frontend
npm install
```

### Build Errors

If you encounter build errors:

- Verify Node.js version 16 or higher is installed:
```bash
  node --version
```
- Clear `node_modules` and reinstall:
```bash
  cd frontend
  rm -rf node_modules
  npm install
```



## Recommended Development Workflow

For daily development, **use Option 1** (separate servers):

1. **Terminal 1:** Start Flask
```bash
   cd backend
   python main.py
```

2. **Terminal 2:** Start Vue.js dev server
```bash
   cd frontend
   npm run dev
```

3. **Browser:** Open http://localhost:5173

This workflow provides:
- Instant frontend updates without manual rebuilds
- Fast development experience with hot reload
- Better debugging tools and error messages
- Full Vue DevTools integration

For testing production builds or simulating the deployment environment, **use Option 2** (Flask serves built files).



## Summary

| Feature        | Option 1: Development Mode | Option 2: Production Build |
|----------------|----------------------------|----------------------------|
| **Hot Reload** |   Yes                      |  No                        |
| **Speed**      |  Fast                      |  Slow (requires rebuild)   |
| **Setup**      | 2 terminals                | 1 terminal                 |
| **Best For**   | Daily development          | Testing production builds  |


For testing production builds, use **Option 2** (Flask serves built files).

