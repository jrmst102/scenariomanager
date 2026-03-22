# Decision Making Lab

A web portal providing unified access to decision-making and strategy simulation tools for academic courses. Built for NYU School of Professional Studies by [Dr. Jose Mendoza](https://www.jose-mendoza.com).

## Overview

The Decision Making Lab consolidates six simulation tools under one platform with role-based access control, course management, and centralized tool launching.

### Lab Tools

| Tool | Status | Description |
|------|--------|-------------|
| AHP Studio | Active | Analytic Hierarchy Process decision tool |
| Airlines Sim | Active | Airline industry simulation |
| Dynamic Pricing Sandbox | Active | Dynamic pricing strategy tool |
| Negotiation Sim | Coming Soon | Negotiation simulation |
| Scenario Sim | Coming Soon | Scenario planning tool |
| Decision Trees | Coming Soon | Decision tree analysis |

### User Roles

- **Admin** — Full platform management: users, courses, schools, tools
- **Professor** — Course management, student enrollment, tool assignment
- **Student** — Access assigned tools, view enrolled courses

## Tech Stack

- **Framework:** Next.js 16 (App Router, TypeScript)
- **Database:** PostgreSQL 16 with Prisma 7 ORM
- **Auth:** JWT (jose library), bcryptjs password hashing, httpOnly cookies
- **Styling:** Tailwind CSS v4, NYU brand palette (Violet #57068C)
- **Icons:** Lucide React
- **Deployment:** DigitalOcean App Platform (Docker)

## Project Structure

```
app/
├── prisma/                  # Schema, migrations, seed script
├── src/
│   ├── app/                 # Next.js App Router pages & API routes
│   │   ├── (authenticated)/ # Protected pages (dashboard, admin, courses, etc.)
│   │   ├── api/             # REST API endpoints
│   │   └── *.tsx            # Public pages (login, about, terms, etc.)
│   ├── components/          # Shared UI components
│   ├── generated/prisma/    # Generated Prisma client
│   └── lib/                 # Auth, DB client, tool definitions
├── .do/app.yaml             # DigitalOcean App Platform config
├── Dockerfile               # Multi-stage Docker build
└── docker-compose.yml       # Local development with Docker
```

## Getting Started

### Quick Start

```bash
python3 start.py
```

This handles everything: starts PostgreSQL (Docker), installs dependencies, runs migrations, seeds demo data, and launches the dev server.

### Manual Setup

#### Prerequisites

- Node.js 20+
- PostgreSQL 16 (or Docker)

#### Steps

1. **Clone and install:**
   ```bash
   cd app
   npm install
   ```

2. **Set up environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your DATABASE_URL and JWT_SECRET
   ```

3. **Start PostgreSQL** (via Docker):
   ```bash
   docker run -d --name decisionlab-db \
     -e POSTGRES_USER=decisionlab \
     -e POSTGRES_PASSWORD=decisionlab2026 \
     -e POSTGRES_DB=decisionlab \
     -p 5433:5432 postgres:16-alpine
   ```

4. **Run migrations and seed:**
   ```bash
   npx prisma migrate dev
   npx tsx prisma/seed.ts
   ```

5. **Start dev server:**
   ```bash
   npm run dev
   ```

6. **Open** http://localhost:3000

### Demo Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | jm10697@nyu.edu | LimeKoala1! |
| Professor | josermendoza@icloud.com | LimeKoala1! |
| Students | See `docs/classlist.csv` | Per classlist |

### Docker Compose (Full Stack)

```bash
cd app
docker compose up --build
```

## Features

### Admin Dashboard (`/admin`)
- **Users** — Create, edit (name, email, password, role), activate/deactivate
- **Courses** — Create, edit, delete courses
- **Schools** — Add and remove schools
- **Tools** — Manage simulation tools

### Course Management (`/manage/courses/[id]`)
- View course details (code, school, semester, professor)
- Add/remove students with search
- Assign/unassign tools via checkbox editor

### Student Experience (`/dashboard`)
- View enrolled courses
- Launch assigned tools
- Profile management

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/login` | Email/password login |
| POST | `/api/auth/logout` | Clear session |
| GET | `/api/auth/me` | Current user info |
| GET/POST | `/api/users` | List/create users (admin) |
| GET/PUT/DELETE | `/api/users/[id]` | User CRUD |
| GET/POST | `/api/courses` | List/create courses |
| GET/PUT/DELETE | `/api/courses/[id]` | Course CRUD |
| POST/DELETE | `/api/courses/[id]/enroll` | Add/remove students |
| POST | `/api/courses/[id]/tools` | Assign tools to course |
| GET/POST | `/api/schools` | List/create schools (admin) |
| DELETE | `/api/schools/[id]` | Delete school (admin) |
| GET | `/api/tools` | List all active tools |
| GET | `/api/tools/assigned` | User's assigned tools |
| POST | `/api/tools/[id]/launch` | Generate launch URL |

## Deployment

### DigitalOcean App Platform

The app includes a `.do/app.yaml` spec for DigitalOcean deployment:

```bash
doctl apps create --spec app/.do/app.yaml
```

Set production environment variables:
- `DATABASE_URL` — Managed PostgreSQL connection string
- `JWT_SECRET` — Strong random secret
- `TOOL_SSO_SECRET` — Secret for tool SSO tokens

### Manual Docker

```bash
cd app
docker build -t decisionlab .
docker run -p 3000:3000 \
  -e DATABASE_URL="postgresql://..." \
  -e JWT_SECRET="..." \
  decisionlab
```

## Scripts

| Command | Description |
|---------|-------------|
| `python3 start.py` | Full setup & launch (recommended) |
| `npm run dev` | Start dev server |
| `npm run build` | Production build |
| `npm start` | Start production server |
| `npm run db:generate` | Regenerate Prisma client |
| `npm run db:migrate` | Run database migrations |
| `npm run db:push` | Push schema to DB (no migration) |
| `npm run db:seed` | Seed demo data |
| `npm run db:studio` | Open Prisma Studio |

## Contact

Dr. Jose Mendoza — [jose.mendoza@nyu.edu](mailto:jose.mendoza@nyu.edu) — [www.jose-mendoza.com](https://www.jose-mendoza.com)

## License

See [LICENSE](LICENSE) for details.
