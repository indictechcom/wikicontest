# Docker Development Guide

This guide covers using Docker for local development of WikiContest.

## Prerequisites

- Docker Desktop (Windows/Mac) or Docker Engine (Linux)
- Docker Compose (included with Docker Desktop)

## Quick Start

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd wikicontest
   ```

2. **Configure OAuth credentials:**
   ```bash
   cp .env.docker.example .env
   # Edit .env and add your CONSUMER_KEY and CONSUMER_SECRET
   ```

3. **Start all services:**
   ```bash
   docker compose up
   ```

   This will start:
   - MySQL database on port 3306
   - Flask backend on port 5000
   - Vite frontend on port 5173

4. **Access the application:**
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:5000/api
   - Health check: http://localhost:5000/api/health

5. **Stop the services:**
   ```bash
   docker compose down
   ```

## Docker Commands

### View logs
```bash
# Follow all logs
docker compose logs -f

# Follow specific service logs
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f mysql
```

### Restart services
```bash
# Restart all services
docker compose restart

# Restart specific service
docker compose restart backend
```

### Rebuild after code changes
```bash
# Rebuild and start
docker compose up --build

# Rebuild specific service
docker compose up --build backend
```

### Database operations
```bash
# Run database migrations
docker compose exec backend flask db upgrade

# Create new migration
docker compose exec backend flask db migrate -m "description"

# Access backend shell
docker compose exec backend flask shell

# Access MySQL directly
docker compose exec mysql mysql -u wikicontest_user -pwikicontest_password wikicontest
```

### Reset database
```bash
# WARNING: This deletes all data
docker compose down -v
docker compose up
```

## Troubleshooting

### Port already in use

**Symptoms:** Error like `port is already allocated`

**Solutions:**
```bash
# Check what's using the port (Windows)
netstat -ano | findstr :5000

# Check what's using the port (Mac/Linux)
lsof -i :5000

# Change ports in docker-compose.yml if needed
```

### Database connection errors

**Symptoms:** SQLAlchemy connection errors or `Can't connect to MySQL server`

**Solutions:**
```bash
# Check MySQL is healthy
docker compose ps

# View MySQL logs
docker compose logs mysql

# Wait for MySQL to be fully ready
docker compose logs -f mysql
# Look for "ready for connections" message
```

### Frontend not loading

**Symptoms:** Blank page or connection refused errors

**Solutions:**
```bash
# Clear node_modules and rebuild
docker compose exec frontend rm -rf node_modules
docker compose up --build frontend

# Check Vite proxy configuration in vite.config.js
# Ensure proxy target is http://localhost:5000
```

### Hot-reload not working

**Symptoms:** Code changes don't reflect in running containers

**Solutions:**
```bash
# Check volume mounts are working
docker compose exec backend ls -la /app

# Restart the specific service
docker compose restart backend

# Rebuild the container
docker compose up --build backend
```

### OAuth callback fails

**Symptoms:** OAuth redirects don't work or show errors

**Solutions:**
```bash
# Verify callback URL in OAuth consumer settings
# Should be: http://localhost:5173/oauth/callback

# Check OAuth environment variables
docker compose exec backend env | grep OAUTH

# Ensure CORS allows the callback origin
# Check CORS_ORIGINS in docker-compose.yml
```

## Architecture

```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│   Frontend      │         │    Backend      │         │     MySQL       │
│   (Vite Dev)    │────────▶│   (Flask Dev)   │────────▶│   Database      │
│   Port 5173     │ Proxy   │   Port 5000     │         │   Port 3306     │
└─────────────────┘         └─────────────────┘         └─────────────────┘
     Hot Reload                 Hot Reload                Persistent Data
```

### Services

- **mysql**: MySQL 8.0 database with persistent volume
- **backend**: Flask development server with hot-reload
- **frontend**: Vite development server with hot-reload

### Networks

All services communicate via the `wikicontest_network` bridge network.

### Volumes

- `mysql_data`: Persistent MySQL data storage
- `./backend`: Mounted to `/app` in backend container (hot-reload)
- `./frontend`: Mounted to `/app` in frontend container (hot-reload)

## Development Workflow

1. Make code changes in your local editor
2. Changes are immediately reflected via hot-reload
3. View logs in real-time: `docker compose logs -f`
4. Access services at localhost ports

## Production Testing

To test the production build locally:

```bash
# Build production image
docker build -t wikicontest:prod .

# Run production container
docker run -p 8000:8000 \
  -e DATABASE_URL="mysql+pymysql://user:pass@host:3306/db" \
  -e SECRET_KEY="test-key" \
  -e JWT_SECRET_KEY="test-jwt-key" \
  wikicontest:prod

# Access at http://localhost:8000
```

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Vue.js Documentation](https://vuejs.org/)
