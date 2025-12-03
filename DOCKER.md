# Docker Setup Instructions

## Quick Start

1. **Build and start all services:**

   ```bash
   docker-compose up --build
   ```

2. **Access the application:**

   - Frontend: http://localhost:5173
   - Backend API: http://localhost:4000
   - MySQL: localhost:3306

3. **Create admin user (first time only):**
   ```bash
   docker-compose exec backend npm run create:admin
   ```
   - Username: `admin`
   - Password: `admin123`

** Other commands: **

```bash
docker-compose exec backend npm run create:test-users
```

** Verify other commands: **

```bash
  "scripts": {
    "test": "node tests/flujo-test.js",
    "start": "node server.js",
    "test:flujo": "node tests/flujo-test.js",
    "test:setup": "node tests/verificar-setup.js",
    "test:dashboard": "node tests/test-dashboard.js",
    "create:admin": "node scripts/createAdmin.js",
    "create:test-users": "node scripts/createTestUsers.js",
    "fix:dashboard": "node scripts/fix-dashboard-view.js"
  }
```

## Useful Commands

**Stop all services:**

```bash
docker-compose down
```

**Stop and remove volumes (reset database):**

```bash
docker-compose down -v
```

**View logs:**

```bash
docker-compose logs -f
docker-compose logs backend
docker-compose logs frontend
docker-compose logs mysql
```

**Rebuild specific service:**

```bash
docker-compose up --build backend
```

**Execute commands in containers:**

```bash
docker-compose exec backend sh
docker-compose exec mysql mysql -uroot -proot123 academia_final
```

## Notes

- Database is automatically initialized with `init-db.sql` on first run
- Data persists in Docker volumes even after stopping containers
- Backend hot-reloads on code changes (volume mounted)
- Frontend hot-reloads on code changes (volume mounted)
- MySQL password is `root123` (change in docker-compose.yml if needed)
