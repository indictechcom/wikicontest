/**
 * Toolforge Node.js Frontend Server
 * 
 * Serves the Vue static dist files and proxies /api requests to the backend.
 * This inherently resolves issues with 3rd-party cookies blocked by browsers when
 * using cross-domain API calls, as the browser only ever talks to the frontend server.
 */

const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');
const path = require('path');

const app = express();

// Standard port Toolforge supplies
const port = process.env.PORT || 8000;

// Set via Toolforge Env, defaults to backend tool name
const backendUrl = process.env.BACKEND_URL || 'https://wikicontest-backend.toolforge.org';

// Proxy /api traffic to the Python backend Toolforge service
app.use('/api', createProxyMiddleware({
    target: backendUrl,
    changeOrigin: true,
    // Propagate cookie domain securely
    cookieDomainRewrite: 'wikicontest.toolforge.org',
    // Optional: add useful headers for backend logs
    onProxyReq: (proxyReq, req, res) => {
        proxyReq.setHeader('x-forwarded-host', req.headers.host || 'wikicontest.toolforge.org');
    }
}));

// Serve static Vue application from 'dist' (created by Vite)
const distPath = path.join(__dirname, 'dist');
app.use(express.static(distPath));

// For Vue Router HTML5 history mode (serves index.html for unknown routes)
// Note: app.use() is used instead of app.get('*') to avoid a breaking change
// in path-to-regexp v8+ (bundled with http-proxy-middleware v3).
app.use((req, res) => {
    res.sendFile(path.join(distPath, 'index.html'));
});

// Bind to 0.0.0.0
app.listen(port, '0.0.0.0', () => {
    console.log(`Frontend Node.js server listening on port ${port}`);
    console.log(`Proxying /api to -> ${backendUrl}`);
});
