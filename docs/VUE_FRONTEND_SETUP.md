# Vue.js Frontend Setup Guide

A comprehensive guide for setting up and working with the Vue.js 3 frontend for the WikiEval platform.

## Table of Contents

- [Overview](#overview)
- [Technology Stack](#technology-stack)
- [Prerequisites](#prerequisites)
- [Development Setup](#development-setup)
- [Building for Production](#building-for-production)
- [Project Structure](#project-structure)
- [Key Features](#key-features)
- [Adding New Features](#adding-new-features)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)
- [Migration Notes](#migration-notes)
- [Resources](#resources)



## Overview

The WikiEval frontend has been migrated from vanilla JavaScript to **Vue.js 3**, providing significant improvements in:

- **Component-Based Architecture** - Modular, reusable UI components
- **State Management** - Predictable state with Composition API
- **Developer Experience** - Hot module replacement and better debugging
- **Toolforge Compatibility** - Optimized for Wikimedia Toolforge deployment

### Why Vue.js 3?

- Modern framework with excellent performance
- Composition API for better code organization
- Strong ecosystem with official routing and state management
- Easy integration with existing Flask backend
- Production-ready build tooling with Vite



## Technology Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| **Vue.js** | 3.x | Progressive JavaScript framework |
| **Vue Router** | 4.x | Client-side routing and navigation |
| **Vite** | 5.x | Fast build tool with HMR |
| **Axios** | 1.x | HTTP client for API requests |
| **Bootstrap** | 5.x | CSS framework and components |



## Prerequisites

Before you begin, ensure you have:

- **Node.js** 16 or higher
- **npm** (included with Node.js)
- **Flask backend** running on port 5000

**Verify installation:**
```bash
node --version  # Should show v16.0.0 or higher
npm --version   # Should show 7.0.0 or higher
```



## Development Setup

### Step 1: Install Dependencies

Navigate to the frontend directory and install all required packages:

```bash
cd frontend
npm install
```

This installs:
- Vue.js 3 and related libraries
- Vite development server
- Axios for API calls
- Bootstrap for styling
- All build tools and dependencies

### Step 2: Start Development Server

```bash
npm run dev
```

**Expected output:**
```
VITE v5.x.x  ready in XXX ms

➜  Local:   http://localhost:5173/
➜  Network: use --host to expose
```

The development server starts at `http://localhost:5173` with hot module replacement (HMR) enabled.

### Step 3: Complete Development Workflow

For full functionality, run both frontend and backend:

#### Terminal 1 - Flask Backend

```bash
cd backend
python app.py
```

**Backend runs at:** `http://localhost:5000/api`

#### Terminal 2 - Vue.js Frontend

```bash
cd frontend
npm run dev
```

**Frontend runs at:** `http://localhost:5173`

### Step 4: Access the Application

Open your browser to:
- **Frontend URL:** `http://localhost:5173`
- **API requests** are automatically proxied to `http://localhost:5000/api`

**How the proxy works:**
- Vite dev server intercepts requests to `/api/*`
- Forwards them to Flask backend
- Returns responses to frontend
- No CORS issues in development!



## Building for Production

### Build Command

Generate an optimized production build:

```bash
cd frontend
npm run build
```

**What happens during build:**
1. Compiles Vue components to JavaScript
2. Minifies and optimizes all code
3. Processes and optimizes CSS
4. Generates production HTML
5. Creates source maps for debugging
6. Outputs everything to `dist/` directory

**Build output:**
```
frontend/
└── dist/
    ├── index.html           # Entry HTML file
    ├── assets/
    │   ├── index-[hash].js  # Bundled JavaScript
    │   ├── index-[hash].css # Bundled CSS
    │   └── [images/fonts]   # Optimized assets
    └── favicon.ico          # Site favicon
```

### Preview Production Build (Optional)

Test the production build locally before deployment:

```bash
npm run preview
```

This starts a local server at `http://localhost:4173` serving the built files.

### Flask Integration

The Flask backend automatically detects and serves the built Vue.js files:

| Mode | Serves From | When |
|------|-------------|------|
| **Development** | `frontend/` | No `dist/` directory exists |
| **Production** | `frontend/dist/` | After running `npm run build` |

**No additional configuration needed!** Flask handles the switching automatically.



## Project Structure

```
frontend/
├── src/                        # Source code
│   ├── components/            # Reusable Vue components
│   │   └── AlertContainer.vue # Alert notification system
│   ├── views/                 # Page-level components
│   │   ├── Home.vue          # Landing page
│   │   ├── Login.vue         # User login
│   │   ├── Register.vue      # User registration
│   │   ├── Contests.vue      # Contest listing
│   │   ├── Dashboard.vue     # User dashboard
│   │   └── Profile.vue       # User profile
│   ├── router/                # Vue Router configuration
│   │   └── index.js          # Route definitions & guards
│   ├── services/              # API service layer
│   │   └── api.js            # Axios configuration & API methods
│   ├── store/                 # State management
│   │   └── index.js          # Composable store pattern
│   ├── utils/                 # Utility functions
│   │   └── alerts.js         # Alert helpers
│   ├── App.vue                # Root component
│   ├── main.js                # Application entry point
│   └── style.css              # Global styles
├── public/                     # Static assets (copied as-is)
├── index.html                  # HTML template
├── package.json                # Dependencies & scripts
├── vite.config.js             # Vite configuration
└── dist/                       # Production build (generated)
```

### Directory Purposes

| Directory | Purpose |
|-----------|---------|
| **`src/components/`** | Reusable components used across multiple pages |
| **`src/views/`** | Page-level components mapped to routes |
| **`src/router/`** | Client-side routing and navigation guards |
| **`src/services/`** | API communication with Flask backend |
| **`src/store/`** | Application state management |
| **`src/utils/`** | Helper functions and utilities |



## Key Features

### 1. Component-Based Architecture

Each page is a self-contained Vue component:

**Structure of a Vue component:**
```vue
<template>
  <!-- HTML template -->
  <div class="container">
    <h1>{{ title }}</h1>
  </div>
</template>

<script>
// JavaScript logic
export default {
  name: 'MyComponent',
  data() {
    return {
      title: 'Hello World'
    }
  }
}
</script>

<style scoped>
/* Component-specific CSS */
.container {
  padding: 20px;
}
</style>
```

**Benefits:**
- Encapsulated logic and styling
- Reusable across the application
- Easy to test and maintain
- Automatic scoped styling

### 2. State Management

Uses Vue 3 Composition API with a composable store pattern for lightweight state management:

**Store usage example:**
```javascript
import { useStore } from '../store'

export default {
  setup() {
    const store = useStore()
    
    // Access state
    const user = store.user
    const isAuthenticated = store.isAuthenticated
    
    // Update state
    const login = async (credentials) => {
      await store.login(credentials)
    }
    
    return { user, isAuthenticated, login }
  }
}
```

**Managed state:**
- User authentication status
- Current user information
- Contest data
- Loading states
- UI state (modals, alerts)

### 3. Client-Side Routing

Vue Router handles navigation with:

- **Route Protection** - Authentication-required routes
- **Automatic Redirects** - Unauthenticated users redirected to login
- **Query Parameters** - URL-based state management
- **History Mode** - Clean URLs without hash fragments
- **Lazy Loading** - Code splitting for better performance

**Route configuration example:**
```javascript
{
  path: '/dashboard',
  name: 'Dashboard',
  component: () => import('../views/Dashboard.vue'),
  meta: { requiresAuth: true }  // Protected route
}
```

### 4. API Integration

Centralized API service (`src/services/api.js`) provides:

- **CSRF Token Management** - Automatic token inclusion
- **Cookie Handling** - JWT authentication with HTTP-only cookies
- **Error Handling** - Consistent error responses
- **Request Interceptors** - Modify requests before sending
- **Response Interceptors** - Process responses globally

**API usage example:**
```javascript
import api from '@/services/api'

// GET request
const contests = await api.get('/contest')

// POST request with data
const newContest = await api.post('/contest', {
  name: 'My Contest',
  description: 'Description here'
})

// Error handling
try {
  const response = await api.get('/contest/123')
} catch (error) {
  console.error('API error:', error.response?.data)
}
```



## Adding New Features

### Creating a New Page

#### Step 1: Create View Component

Create a new file in `src/views/`:

**Example:** `src/views/NewPage.vue`
```vue
<template>
  <div class="container py-5">
    <h2>{{ pageTitle }}</h2>
    <p>{{ description }}</p>
  </div>
</template>

<script>
export default {
  name: 'NewPage',
  data() {
    return {
      pageTitle: 'New Page',
      description: 'This is a new page in the application.'
    }
  },
  mounted() {
    console.log('NewPage component mounted')
  }
}
</script>

<style scoped>
.container {
  max-width: 800px;
  margin: 0 auto;
}
</style>
```

#### Step 2: Add Route

Update `src/router/index.js`:

```javascript
import NewPage from '../views/NewPage.vue'

const routes = [
  // ... existing routes
  {
    path: '/new-page',
    name: 'NewPage',
    component: NewPage,
    meta: { requiresAuth: false }  // Set to true if login required
  }
]
```

#### Step 3: Add Navigation Link

Add a link in your navigation or other components:

```vue
<router-link to="/new-page" class="btn btn-primary">
  Go to New Page
</router-link>
```

### Creating a Reusable Component

#### Step 1: Create Component

Create a new file in `src/components/`:

**Example:** `src/components/MyComponent.vue`
```vue
<template>
  <div class="my-component">
    <h3>{{ title }}</h3>
    <p>{{ message }}</p>
    <button @click="handleClick" class="btn btn-primary">
      {{ buttonText }}
    </button>
  </div>
</template>

<script>
export default {
  name: 'MyComponent',
  props: {
    title: {
      type: String,
      required: true
    },
    message: {
      type: String,
      default: 'Default message'
    },
    buttonText: {
      type: String,
      default: 'Click me'
    }
  },
  emits: ['button-clicked'],
  methods: {
    handleClick() {
      this.$emit('button-clicked')
    }
  }
}
</script>

<style scoped>
.my-component {
  padding: 20px;
  border: 1px solid #ddd;
  border-radius: 8px;
}
</style>
```

#### Step 2: Use in Views

Import and use the component in any view:

```vue
<template>
  <div>
    <MyComponent
      title="Welcome"
      message="This is a reusable component"
      button-text="Click Here"
      @button-clicked="handleButtonClick"
    />
  </div>
</template>

<script>
import MyComponent from '../components/MyComponent.vue'

export default {
  components: {
    MyComponent
  },
  methods: {
    handleButtonClick() {
      alert('Button was clicked!')
    }
  }
}
</script>
```



## Deployment

### Local Production Deployment

#### Step 1: Build Frontend

```bash
cd frontend
npm run build
```

**Output:** `frontend/dist/` directory with optimized files

#### Step 2: Run Flask

```bash
cd backend
python app.py
```

Flask automatically serves files from `frontend/dist/`

#### Step 3: Access Application

Open browser to `http://localhost:5000`

### Toolforge Deployment

For Wikimedia Toolforge deployment:

#### Step 1: Build Locally

```bash
cd frontend
npm run build
```

#### Step 2: Deploy with Backend

Deploy the `frontend/dist/` directory along with your Flask backend to Toolforge.

#### Step 3: Configure Flask

Flask automatically serves the built files. No additional configuration needed!

**For complete deployment instructions:**
See [`docs/TOOLFORGE_DEPLOYMENT.md`](../docs/TOOLFORGE_DEPLOYMENT.md)

### Production Checklist

- [ ] Build frontend with `npm run build`
- [ ] Verify `dist/` directory was created
- [ ] Test production build with `npm run preview`
- [ ] Set environment variables for production
- [ ] Configure HTTPS for secure deployment
- [ ] Set up proper CORS configuration
- [ ] Enable production mode in Flask
- [ ] Test all functionality in production environment



## Troubleshooting

### Development Server Issues

#### Port Already in Use

**Problem:** Error message "Port 5173 is already in use"

**Solution:** Change the port in `vite.config.js`:
```javascript
export default {
  server: {
    port: 3000  // Use different port
  }
}
```

#### API Requests Failing

**Problem:** Network errors when calling API endpoints

**Solutions:**
1. Ensure Flask backend is running on port 5000
2. Check Vite proxy configuration in `vite.config.js`
3. Verify Flask app is accessible at `http://localhost:5000/api`

**Check proxy configuration:**
```javascript
export default {
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true
      }
    }
  }
}
```

#### CORS Errors

**Problem:** Cross-Origin Resource Sharing errors in browser console

**Solutions:**
1. Check Flask CORS configuration includes `http://localhost:5173`
2. Ensure Flask has `CORS_ORIGINS` environment variable set
3. Verify credentials are being sent with requests

**Flask CORS configuration:**
```python
from flask_cors import CORS

CORS(app, origins=['http://localhost:5173'], supports_credentials=True)
```

### Build Issues

#### Module Not Found

**Problem:** Build fails with "Cannot find module" errors

**Solution:**
```bash
# Remove node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

#### Build Errors

**Problem:** Build fails with syntax or compilation errors

**Solutions:**
1. Check Node.js version: `node --version` (requires 16+)
2. Update Node.js if needed
3. Update dependencies: `npm update`
4. Clear Vite cache: `rm -rf node_modules/.vite`

#### Type Errors

**Problem:** TypeScript or prop validation errors

**Solution:** Check Vue component syntax:
- Verify prop types are correct
- Ensure required props are provided
- Check component import statements

### Runtime Issues

#### Routes Not Working

**Problem:** 404 errors or routes not rendering

**Solutions:**
1. Check Vue Router configuration in `src/router/index.js`
2. Verify component imports are correct
3. Ensure routes are properly defined
4. Check that `router-view` exists in `App.vue`

#### State Not Updating

**Problem:** UI not reflecting state changes

**Solutions:**
1. Verify you're using reactive data (ref, reactive)
2. Check that mutations/methods are being called
3. Ensure computed properties are updating
4. Use Vue DevTools to inspect state

#### API Errors

**Problem:** API calls returning errors or unexpected responses

**Solutions:**
1. Check network tab in browser DevTools
2. Verify API endpoint URLs are correct
3. Check Flask backend logs for errors
4. Ensure authentication tokens are valid
5. Verify request payload format

### Performance Issues

#### Slow Development Server

**Problem:** Vite dev server is slow to start or reload

**Solutions:**
1. Clear Vite cache: `rm -rf node_modules/.vite`
2. Reduce number of npm packages
3. Check for circular dependencies
4. Update Vite to latest version

#### Large Bundle Size

**Problem:** Production build is too large

**Solutions:**
1. Use lazy loading for routes
2. Remove unused dependencies
3. Optimize images and assets
4. Enable code splitting
5. Use production build optimizations



## Migration Notes

The WikiEval frontend was migrated from vanilla JavaScript to Vue.js 3 to improve maintainability and developer experience.

### Key Changes

| Aspect         | Before (Vanilla JS)     | After (Vue.js 3)        |
|----------------|-------------------------|------------------       |
| **State**      | Global variables        | Composable store        |
| **Routing**    | Manual DOM manipulation | Vue Router              |
| **Components** | Inline HTML strings     | Single File Components  |
| **API Calls**  | Native `fetch()`        | Axios with interceptors |
| **Styling**    | Inline and global CSS   | Scoped component styles |
| **Build**      | No build process        | Vite build optimization |

### Migration Benefits

  **Better Code Organization** - Components are self-contained and reusable  
  **Improved Performance** - Virtual DOM and optimized rendering  
  **Enhanced DX** - Hot module replacement and better debugging  
  **Type Safety** - Optional TypeScript support  
  **Easier Testing** - Component-based testing approach  
  **Modern Tooling** - Vite for fast development and builds

### Preserved Functionality

All existing functionality has been preserved and enhanced:
- User authentication (email/password and OAuth)
- Contest management (create, view, edit)
- Article submissions
- Dashboard and statistics
- Leaderboards
- Profile management

---

## Resources

### Official Documentation

- **Vue.js 3** - [https://vuejs.org/](https://vuejs.org/)
- **Vue Router** - [https://router.vuejs.org/](https://router.vuejs.org/)
- **Vite** - [https://vitejs.dev/](https://vitejs.dev/)
- **Axios** - [https://axios-http.com/](https://axios-http.com/)
- **Bootstrap 5** - [https://getbootstrap.com/](https://getbootstrap.com/)

### Learning Resources

- **Vue 3 Composition API** - [Composition API FAQ](https://vuejs.org/guide/extras/composition-api-faq.html)
- **Vue 3 Guide** - [Official Guide](https://vuejs.org/guide/introduction.html)
- **Vite Guide** - [Getting Started](https://vitejs.dev/guide/)

### Project Documentation

- **Backend Documentation** - [`../backend/README.md`](../backend/README.md)
- **Frontend Documentation** - [`frontend/README.md`](../frontend/README.md)
- **Toolforge Deployment** - [`docs/TOOLFORGE_DEPLOYMENT.md`](../docs/TOOLFORGE_DEPLOYMENT.md)

### Community & Support

- **Vue.js Discord** - [Join Community](https://discord.com/invite/vue)
- **Stack Overflow** - Tag questions with `vue.js`
- **GitHub Discussions** - Project-specific questions



## Next Steps

After setting up the Vue.js frontend:

1.   Explore the codebase and understand component structure
2.   Make a small change and see HMR in action
3.   Review Vue DevTools for better debugging
4.   Read Vue.js documentation for deeper understanding
5.   Start building new features!


