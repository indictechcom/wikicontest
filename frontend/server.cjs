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

/**
 * Rewrite Location header in redirect responses from the backend.
 *
 * When the backend returns a redirect (e.g., 308 from Flask strict_slashes),
 * the Location header may point to the backend URL. We rewrite it to point
 * to the frontend URL so the browser stays on the frontend domain and
 * subsequent requests continue going through the proxy.
 */
function rewriteLocation(req, location) {
    if (!location || location.startsWith('/')) return location; // relative URL — fine as-is
    try {
        const backendOrigin = new URL(backendUrl).origin;
        const frontendHost = req.headers.host || 'wikicontest.toolforge.org';
        const frontendOrigin = `https://${frontendHost}`;
        if (location.startsWith(backendOrigin)) {
            return location.replace(backendOrigin, frontendOrigin);
        }
        return location;
    } catch {
        return location;
    }
}

// Proxy /oauth/callback to the backend (for Toolforge OAuth flow)
// The OAuth consumer is registered with callback URL /oauth/callback,
// so Wikimedia redirects here. We must forward it to the backend.
app.use('/oauth', createProxyMiddleware({
    target: backendUrl,
    changeOrigin: true,
    pathRewrite: { '^/oauth': '/oauth' },
    followRedirects: false,
    on: {
        error: (err, req, res) => {
            console.error('[OAuth Proxy Error]', err.message);
            if (!res.headersSent) {
                res.writeHead(502, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: 'OAuth service unavailable' }));
            }
        },
        proxyReq: (proxyReq, req, res) => {
            proxyReq.setHeader('x-forwarded-host', req.headers.host || 'wikicontest.toolforge.org');
            proxyReq.setHeader('x-forwarded-proto', 'https');
        },
        proxyRes: (proxyRes, req, res) => {
            if (proxyRes.headers.location) {
                proxyRes.headers.location = rewriteLocation(req, proxyRes.headers.location);
            }
        }
    }
}));

// Proxy /api traffic to the Python backend Toolforge service
// NOTE: Express strips the '/api' mount prefix before passing to the middleware,
// so we use pathRewrite to re-add it (e.g. /api/user/login → /user/login → /api/user/login).
app.use('/api', createProxyMiddleware({
    target: backendUrl,
    changeOrigin: true,
    pathRewrite: { '^/': '/api/' },
    // Do NOT follow redirects server-side. When the backend returns a redirect
    // (e.g., 308 from Flask strict_slashes), following it can crash the Node.js
    // process with an unhandled error. Instead, rewrite the Location header to
    // point back to the frontend domain and let the browser follow the redirect.
    followRedirects: false,
    // Propagate cookie domain securely
    cookieDomainRewrite: 'wikicontest.toolforge.org',
    // Optional: add useful headers for backend logs
    on: {
        error: (err, req, res) => {
            console.error('[API Proxy Error]', err.message);
            if (!res.headersSent) {
                res.writeHead(502, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: 'Backend service unavailable' }));
            }
        },
        proxyReq: (proxyReq, req, res) => {
            // Forward the original host so Flask's ProxyFix sees wikicontest.toolforge.org
            proxyReq.setHeader('x-forwarded-host', req.headers.host || 'wikicontest.toolforge.org');
            // Tell Flask the connection is HTTPS (the proxy terminates TLS)
            proxyReq.setHeader('x-forwarded-proto', 'https');
        },
        proxyRes: (proxyRes, req, res) => {
            // Rewrite any redirect Location headers from backend → frontend domain
            if (proxyRes.headers.location) {
                proxyRes.headers.location = rewriteLocation(req, proxyRes.headers.location);
            }
        }
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
    console.log(`Proxying /api and /oauth to -> ${backendUrl}`);
});
