# WikiContest Frontend - Vue.js Application

A modern, responsive Vue.js 3 frontend for the WikiContest platform, providing an intuitive user interface for managing Wikipedia article contests, submissions, and user accounts.

## Table of Contents

- [Overview](#overview)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Development Workflow](#development-workflow)
- [Building for Production](#building-for-production)
- [Features](#features)
- [API Integration](#api-integration)
- [State Management](#state-management)
- [Routing](#routing)
- [Styling](#styling)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)



## Overview

The WikiContest frontend is a single-page application (SPA) built with Vue.js 3 that provides a complete user interface for the WikiContest platform. It features responsive design, real-time updates, and seamless integration with the Flask backend API.



## Technology Stack

| Technology | Purpose |
|------------|---------|
| **Vue.js 3** | Progressive JavaScript framework with Composition API |
| **Vue Router** | Official router for client-side navigation |
| **Vite** | Next-generation frontend build tool with HMR |
| **Axios** | Promise-based HTTP client for API requests |
| **Bootstrap 5** | CSS framework for responsive design and components |

---

## Project Structure

```
frontend/
├── src/
│   ├── components/          # Reusable Vue components
│   │   └── AlertContainer.vue  # Alert notification component
│   ├── views/               # Page-level components
│   │   ├── Home.vue        # Landing page
│   │   ├── Login.vue       # User login page
│   │   ├── Register.vue    # User registration page
│   │   ├── Contests.vue    # Contest listing page
│   │   ├── Dashboard.vue   # User dashboard
│   │   └── Profile.vue     # User profile page
│   ├── router/              # Vue Router configuration
│   │   └── index.js        # Route definitions and navigation guards
│   ├── services/            # API service layer
│   │   └── api.js          # Axios configuration and API methods
│   ├── store/               # State management
│   │   └── index.js        # Composable store pattern
│   ├── utils/               # Utility functions
│   │   └── alerts.js       # Alert notification utilities
│   ├── App.vue              # Root component
│   ├── main.js              # Application entry point
│   └── style.css            # Global styles
├── index.html               # HTML template
├── package.json             # Dependencies and scripts
├── vite.config.js           # Vite configuration
└── README.md                # This file
```

### Key Directories

- **`src/components/`** - Reusable UI components used across multiple views
- **`src/views/`** - Page-level components representing different routes
- **`src/router/`** - Client-side routing configuration and guards
- **`src/services/`** - API communication layer with backend
- **`src/store/`** - Application state management using Composition API



## Prerequisites

Ensure you have the following installed:

- **Node.js** 16 or higher
- **npm** (comes with Node.js)



## Installation

### 1. Navigate to Frontend Directory

```bash
cd frontend
```

### 2. Install Dependencies

```bash
npm install
```

This will install all required packages including Vue.js, Vue Router, Vite, Axios, and Bootstrap.

### 3. Verify Installation

```bash
# Check installed packages
npm list --depth=0
```



## Development Workflow

### Running the Development Server

For the best development experience, run both the backend and frontend simultaneously:

#### Terminal 1 - Flask Backend

```bash
cd backend
python main.py
```

Backend API will be available at `http://localhost:5000/api`

#### Terminal 2 - Vue.js Frontend

```bash
cd frontend
npm run dev
```

Frontend will be available at `http://localhost:5173`

### How It Works

- **Vite Dev Server** - Provides hot module replacement (HMR) for instant updates
- **API Proxy** - Configured in `vite.config.js` to proxy `/api` requests to Flask
- **Live Reload** - Changes to Vue files are reflected immediately without refresh

### Accessing the Application

1. Open your browser to `http://localhost:5173`
2. The frontend makes API requests to `http://localhost:5173/api/*`
3. Vite proxies these requests to Flask at `http://localhost:5000/api/*`



## Building for Production

### 1. Build the Vue.js Application

```bash
cd frontend
npm run build
```

This command:
- Compiles and minifies the application
- Optimizes assets (images, fonts, etc.)
- Creates a production-ready `dist/` directory
- Generates source maps for debugging

### 2. Preview Production Build (Optional)

```bash
npm run preview
```

This starts a local server to preview the production build at `http://localhost:4173`

### 3. Deploy with Flask

The Flask backend automatically serves built files from the `frontend/dist/` directory. No additional configuration needed.

**Workflow:**
1. Build frontend: `npm run build`
2. Start Flask: `cd ../backend && python main.py`
3. Access at: `http://localhost:5000`



## Features

### Authentication & User Management

- **Email/Password Login** - Traditional authentication with JWT tokens
- **Wikimedia OAuth** - Login with Wikimedia account (optional)
- **User Registration** - Create new accounts with validation
- **Session Management** - Secure JWT-based sessions with HTTP-only cookies
- **Protected Routes** - Automatic redirection for unauthenticated users
- **Profile Management** - View and edit user profile information

### Contest Management

- **Contest Listing** - Browse current, upcoming, and past contests
- **Contest Creation** - Create new contests with customizable rules
- **Contest Details** - View comprehensive contest information
- **Article Submission** - Submit Wikipedia articles to active contests
- **Leaderboard** - View contest rankings and scores
- **Filtering & Search** - Find contests by status, date, or name

### User Dashboard

- **Statistics Overview** - Total score, contests created, jury memberships
- **Recent Submissions** - Track your article submissions and their status
- **Contest Performance** - View scores broken down by contest
- **Created Contests** - Manage contests you've created
- **Quick Actions** - Fast access to common tasks

### UI Components & UX

- **Responsive Design** - Optimized for mobile, tablet, and desktop
- **Alert Notifications** - Real-time feedback for user actions
- **Modal Dialogs** - Context-aware forms and confirmations
- **Loading States** - Visual feedback during async operations
- **Error Handling** - User-friendly error messages
- **Accessibility** - ARIA labels and keyboard navigation support



## API Integration

### API Service Layer

The frontend communicates with the Flask backend through a centralized API service (`src/services/api.js`).

**Key Features:**
- Axios instance configuration with base URL
- Automatic CSRF token handling
- Cookie-based JWT authentication
- Request/response interceptors
- Consistent error handling
- Request timeout configuration

**Example API Call:**

```javascript
import api from '@/services/api'

// GET request
const contests = await api.get('/contest')

// POST request with data
const newContest = await api.post('/contest', {
  name: 'My Contest',
  description: 'Contest description'
})
```

### Security Features

- **CSRF Protection** - Tokens included in all state-changing requests
- **Credentials** - Cookies sent with every request for authentication
- **HTTPS Support** - Ready for secure production deployment



## State Management

### Composable Store Pattern

The application uses Vue 3's Composition API with a composable store pattern (`src/store/index.js`) for lightweight state management.

**Managed State:**
- User authentication status
- Current user information
- Contest data and filters
- Loading states
- UI state (modals, alerts)

**Benefits:**
- No external state management library needed
- Reactive state updates
- Simple and maintainable
- TypeScript-friendly

**Example Usage:**

```javascript
import { useStore } from '@/store'

const store = useStore()

// Access state
console.log(store.user.value)

// Update state
store.setUser(userData)
```



## Routing

### Vue Router Configuration

Client-side routing is handled by Vue Router (`src/router/index.js`) with:

- **History Mode** - Clean URLs without hash fragments
- **Route Protection** - Navigation guards for authentication
- **Lazy Loading** - Code splitting for better performance
- **Meta Fields** - Route-level metadata (authentication, titles)
- **Query Parameters** - Support for URL parameters

### Protected Routes

Routes requiring authentication automatically redirect to login:

```javascript
{
  path: '/dashboard',
  name: 'Dashboard',
  component: Dashboard,
  meta: { requiresAuth: true }
}
```

### Available Routes

| Route       | Component | Auth Required |
|-------------|-----------|---------------|
| `/`         | Home      | No            |
| `/login`    | Login     | No            |
| `/register` | Register  | No            |
| `/contests` | Contests  | No            |
| `/dashboard`| Dashboard | Yes           |
| `/profile`  | Profile   | Yes           |



## Styling

### Design System

- **Bootstrap 5** - Base component styles and grid system
- **Custom CSS** - Brand colors, spacing, and specific styling
- **CSS Variables** - Consistent theming throughout the application
- **Responsive Utilities** - Mobile-first responsive design

### Customization

Global styles are defined in `src/style.css`:

```css
:root {
  --primary-color: #007bff;
  --secondary-color: #6c757d;
  --success-color: #28a745;
  /* ... more variables */
}
```

### Component Styles

- **Scoped Styles** - Component-specific styles using `<style scoped>`
- **Bootstrap Classes** - Utility classes for rapid development
- **Custom Classes** - Additional styling for unique components



## Deployment

### Local Production Deployment

**Step 1:** Build the frontend
```bash
cd frontend
npm run build
```

**Step 2:** The Flask backend automatically serves files from `frontend/dist/`
```bash
cd ../backend
python main.py
```

**Step 3:** Access at `http://localhost:5000`

### Toolforge Deployment

For Wikimedia Toolforge deployment:

1. Build the Vue.js application locally
2. The built files in `dist/` are included in the deployment
3. Flask serves the static files on Toolforge

See [`docs/TOOLFORGE_DEPLOYMENT.md`](../docs/TOOLFORGE_DEPLOYMENT.md) for detailed instructions.

### Production Considerations

- **Environment Variables** - Configure API base URL for production
- **HTTPS** - Always use HTTPS in production
- **CDN** - Consider using a CDN for static assets
- **Caching** - Configure appropriate cache headers
- **Monitoring** - Set up error tracking (e.g., Sentry)



## Troubleshooting

### Development Server Issues

#### Port Already in Use

**Problem:** Vite cannot start because port 5173 is in use

**Solution:** Change the port in `vite.config.js`:
```javascript
export default {
  server: {
    port: 3000  // Use a different port
  }
}
```

#### API Requests Failing

**Problem:** Frontend cannot connect to backend API

**Solutions:**
- Ensure Flask backend is running on port 5000
- Check Vite proxy configuration in `vite.config.js`
- Verify Flask CORS settings allow `http://localhost:5173`

#### CORS Errors

**Problem:** Cross-Origin Resource Sharing errors in browser console

**Solutions:**
- Check Flask CORS configuration includes frontend URL
- Ensure Flask app has `CORS_ORIGINS` environment variable set
- Verify credentials are being sent with requests

### Build Issues

#### Module Not Found

**Problem:** Build fails with module not found errors

**Solution:**
```bash
# Remove node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

#### Build Errors

**Problem:** Build fails with syntax or compilation errors

**Solutions:**
- Check Node.js version: `node --version` (requires 16+)
- Update dependencies: `npm update`
- Clear Vite cache: `rm -rf node_modules/.vite`

#### Out of Memory

**Problem:** Build fails with JavaScript heap out of memory

**Solution:**
```bash
# Increase Node.js memory limit
NODE_OPTIONS="--max-old-space-size=4096" npm run build
```

### Runtime Issues

#### Blank Page After Deployment

**Problem:** Production build shows blank page

**Solutions:**
- Check browser console for errors
- Verify Flask is serving files from correct `dist/` directory
- Ensure all assets paths are correct (use relative paths)

#### Authentication Not Working

**Problem:** Login succeeds but user is not authenticated

**Solutions:**
- Check browser allows cookies
- Verify Flask JWT configuration
- Check cookie domain and path settings



## Contributing

### Adding New Features

When contributing to the frontend:

#### 1. Create Components

Place reusable components in `src/components/`:

```vue
<!-- src/components/MyComponent.vue -->
<template>
  <div class="my-component">
    <!-- Component template -->
  </div>
</template>

<script>
export default {
  name: 'MyComponent',
  // Component logic
}
</script>

<style scoped>
/* Component styles */
</style>
```

#### 2. Create Views

Place page-level components in `src/views/`:

```vue
<!-- src/views/MyPage.vue -->
<template>
  <div class="my-page">
    <h1>My Page</h1>
    <!-- Page content -->
  </div>
</template>
```

#### 3. Add Routes

Update `src/router/index.js`:

```javascript
{
  path: '/my-page',
  name: 'MyPage',
  component: () => import('@/views/MyPage.vue'),
  meta: { requiresAuth: true }
}
```

#### 4. Update Store (If Needed)

Add state management in `src/store/index.js` if your feature requires shared state.

#### 5. Test Thoroughly

- Test in development mode (`npm run dev`)
- Test production build (`npm run build && npm run preview`)
- Test with backend integration
- Test responsive design on different screen sizes
- Verify accessibility

### Development Guidelines

- Follow Vue.js style guide and best practices
- Use Composition API for new components
- Write semantic HTML with proper ARIA attributes
- Keep components focused and under 200 lines
- Use ESLint to maintain code quality
- Write meaningful commit messages
- Document complex logic with comments



## Additional Resources

- **Vue.js 3 Documentation:** [https://vuejs.org](https://vuejs.org)
- **Vue Router Documentation:** [https://router.vuejs.org](https://router.vuejs.org)
- **Vite Documentation:** [https://vitejs.dev](https://vitejs.dev)
- **Bootstrap 5 Documentation:** [https://getbootstrap.com](https://getbootstrap.com)
- **Backend Documentation:** [`../backend/README.md`](../backend/README.md)
- **Deployment Guide:** [`../docs/TOOLFORGE_DEPLOYMENT.md`](../docs/TOOLFORGE_DEPLOYMENT.md)



## License

Part of the WikiContest platform project.



**Built with using Vue.js 3 and modern web technologies**