# Scenario Planning Studio

**Version:** 0.1.0 (Specification Draft)  
**Author:** Dr. Jose Mendoza  
**Copyright 2026 by Dr. Jose Mendoza. All rights reserved.**

## Overview

Scenario Planning Studio is a web-based decision support application for structured scenario planning analysis. Users define two critical uncertainties, construct a 2×2 scenario matrix of plausible futures, assess how strategic alternatives perform across each scenario, and generate a robustness ranking — all from a browser interface with no installation required.

The tool is designed for the Competitive Strategy — Decision Tools Module and integrates with AHP Studio, the Negotiation Simulation, the Airlines Simulation, and the Dynamic Pricing Sandbox as part of the analytical toolkit students use in the Strategic Decision-Making Lab.

## Pedagogical Purpose

Scenario Planning answers the question: *"Does our recommended strategy hold up across multiple plausible futures, or does it only win in one specific world?"*

Where AHP ranks options against weighted criteria and Decision Trees compute expected values under uncertainty, Scenario Planning stress-tests a recommendation against qualitatively different futures defined by the intersection of two driving uncertainties. A team that can show their strategy performs well across three of four scenarios — and has a mitigation plan for the fourth — presents a substantially more defensible recommendation in the pitch competition.

## Features

### Core Scenario Planning Workflow

- **Problem Definition** — Title, description, and context for the decision being analyzed
- **Uncertainty Axes** — Define two critical uncertainties, each with a high and low pole (e.g., "Gen Z adoption of premium skincare" ranging from "Fast adoption" to "Slow adoption"); optional descriptions for each pole to anchor the framing
- **2×2 Scenario Matrix** — Four scenarios generated automatically from the axis combinations; each scenario receives a user-defined name and narrative description (e.g., "Premium Boom" for high Gen Z adoption × declining acquisition costs)
- **Strategic Alternatives** — Add up to 8 strategic alternatives (the options being evaluated across scenarios)
- **Impact Assessment** — For each alternative × scenario combination, rate strategic fit on a 5-point scale (Very Weak, Weak, Moderate, Strong, Very Strong) with an optional rationale text field
- **Robustness Ranking** — Computed ranking of alternatives by average score across all four scenarios; identifies which alternatives are robust (perform well everywhere) vs. fragile (perform well in only one or two scenarios)
- **Sensitivity Indicators** — Flag alternatives whose scores vary significantly across scenarios (high variance = strategy is a bet on a specific future; low variance = robust hedge)
- **Visual Matrix Display** — Interactive 2×2 grid with scenario cards; color-coded heatmap overlay showing alternative performance by scenario

### Problem Management

- **Create, save, load, delete** scenario planning problems
- **Import/export `.SCN` files** — JSON-based file format for sharing and reuse; download to local machine, upload to resume later
- **Problem list dashboard** — All saved problems with last-modified timestamps, status indicators, and quick actions

### Group Participation

- **Participants** — Add up to 12 participants per problem; each receives a unique tokenized link to complete impact assessments independently without creating an account
- **Owner self-participation** — The problem owner can add themselves as a participant; assessments are locked until they do so
- **PIN Protection** — Optionally protect participation links with a 4-digit PIN (bcrypt-hashed, 3-attempt lockout with 15-minute cooldown)
- **Anonymous Mode** — Enable anonymous participation where submitted responses are dissociated from participant identities
- **Real-time status** — WebSocket-powered live updates on the admin dashboard as participants save or submit assessments; automatic fallback to polling
- **Aggregation** — Median and mean scores across participants for each alternative × scenario cell; per-cell agreement indicators

### Consensus Measurement

- **Inter-rater agreement** — Kendall's W (coefficient of concordance) with chi-squared test and p-value for the robustness ranking across participants
- **Per-scenario agreement** — Breakdown of consensus strength within each of the four scenarios to identify where the group agrees and where assessments diverge
- **Delphi Iteration** — Multi-round assessment cycles: close a round, share aggregated group results, and open a new round so participants can revise assessments toward convergence

### Decision Report

- **Printable report** — Problem definition, uncertainty axes, scenario matrix with narratives, participant list, impact assessment heatmap, robustness ranking, consensus analysis (Kendall's W), round history, and sensitivity summary
- **AI Report Narrative** — LLM-generated unified narrative summary covering scenario logic, robustness findings, consensus interpretation, and strategic implications; inline editing and up to 3 regenerations per session; model attribution footnote
- **PDF-ready** — Report formatted for browser print-to-PDF

### Authentication & Security

- **JWT authentication** — httpOnly cookies, bcryptjs hashing, 24-hour expiry
- **Account lockout** — 3 failed login attempts triggers lockout
- **Participation tokens** — UUID v4 (122-bit entropy), scoped to a single problem and participant
- **PIN verification** — bcrypt-hashed PINs, 3-attempt lockout with 15-minute cooldown; short-lived JWT (4h) in httpOnly cookie after verification
- **HTTPS, CORS, rate limiting** — 60 req/min API, 5 req/15min PIN verification
- **LLM input sanitization** — Length limits, control character stripping, prompt injection mitigation via system prompts
- **LLM rate controls** — 10-second cooldown between requests, 3 regenerations per session (1-hour TTL)

### User Management

- **Admin panel** — User CRUD, account unlock, password reset
- **Roles** — Admin users manage problems and participants; participant users complete assessments via tokenized links

## Scenario Planning Methodology

### The 2×2 Matrix Framework

The application implements the standard 2×2 scenario matrix approach:

1. **Identify driving uncertainties** — The user selects two uncertainties that are both highly impactful to the decision and genuinely uncertain (i.e., reasonable people could disagree on the direction).

2. **Define poles** — Each uncertainty has a high pole and a low pole representing the endpoints of a plausible range. Poles should be concrete and observable, not vague (e.g., "CAC drops below $30" vs. "CAC exceeds $50," not "good" vs. "bad").

3. **Name the scenarios** — The four quadrant combinations each receive a memorable name and a 2–3 sentence narrative describing what that world looks like. Naming makes scenarios sticky and discussable.

4. **Assess alternatives** — Each strategic alternative is rated for strategic fit in each scenario. The rating reflects how well the alternative would perform *if that specific future materialized*.

5. **Rank for robustness** — The alternative with the highest average score across all four scenarios is the most robust. Alternatives with high variance are "bets" — they win big in one world but fail in others.

### Scoring Model

| Rating | Label | Numeric Value |
|--------|-------|---------------|
| 1 | Very Weak | 1 |
| 2 | Weak | 2 |
| 3 | Moderate | 3 |
| 4 | Strong | 4 |
| 5 | Very Strong | 5 |

**Robustness Score** = Mean of the four scenario scores for a given alternative.

**Fragility Index** = Standard deviation of the four scenario scores. A higher value indicates the alternative is more sensitive to which future materializes.

### Aggregation Across Participants

When multiple participants submit assessments:

- **Cell score** = Median of all participant ratings for that alternative × scenario combination (median is preferred over mean to reduce sensitivity to outliers)
- **Agreement indicator** = Interquartile range (IQR) per cell; IQR ≤ 1 = strong agreement, IQR = 2 = moderate, IQR ≥ 3 = divergent
- **Robustness ranking** = Computed from the aggregated (median) cell scores
- **Kendall's W** = Computed across participants' full robustness rankings to measure overall concordance

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, Uvicorn, Jinja2 |
| Frontend | Server-side rendered HTML, Tailwind CSS, vanilla JavaScript |
| Authentication | bcrypt + itsdangerous signed session cookies; JWT for API |
| Real-time | WebSocket (fastapi-websockets) with polling fallback |
| Data | CSV files via storage abstraction layer |
| Storage | DigitalOcean Spaces (S3-compatible) with local filesystem fallback |
| Computation | NumPy/SciPy (Kendall's W, descriptive statistics) |
| LLM Integration | OpenAI API (gpt-4o-mini default, gpt-4o-mini fallback) — optional, graceful degradation when unavailable |
| Hosting | DigitalOcean App Platform |
| CI/CD | GitHub Actions |

## Data Model

### Problem File (`.SCN`)

Each problem is stored as a JSON file with the `.SCN` extension. The schema:

```json
{
  "version": "1.0",
  "problemId": "uuid-v4",
  "title": "Vela Skincare Growth Strategy",
  "description": "Evaluate four strategic options...",
  "createdAt": "ISO-8601",
  "updatedAt": "ISO-8601",
  "axes": {
    "x": {
      "label": "Gen Z Adoption of Premium Skincare",
      "lowPole": { "label": "Slow adoption", "description": "Gen Z remains price-sensitive..." },
      "highPole": { "label": "Fast adoption", "description": "Gen Z begins trading up..." }
    },
    "y": {
      "label": "DTC Customer Acquisition Costs",
      "lowPole": { "label": "Declining CAC", "description": "New channels reduce costs..." },
      "highPole": { "label": "Rising CAC", "description": "Platform fees continue to climb..." }
    }
  },
  "scenarios": [
    {
      "id": "Q1",
      "name": "Premium Boom",
      "xPole": "high",
      "yPole": "low",
      "narrative": "Gen Z embraces premium skincare while acquisition costs drop..."
    },
    {
      "id": "Q2",
      "name": "Expensive Growth",
      "xPole": "high",
      "yPole": "high",
      "narrative": "Gen Z wants premium but reaching them costs more..."
    },
    {
      "id": "Q3",
      "name": "Stagnation",
      "xPole": "low",
      "yPole": "high",
      "narrative": "Gen Z stays price-sensitive and CAC keeps rising..."
    },
    {
      "id": "Q4",
      "name": "Efficient Niche",
      "xPole": "low",
      "yPole": "low",
      "narrative": "Gen Z stays affordable-focused but DTC costs drop..."
    }
  ],
  "alternatives": [
    { "id": "A", "name": "Double Down on Hero Line", "description": "..." },
    { "id": "B", "name": "Launch Vela V (Gen Z Sub-Brand)", "description": "..." },
    { "id": "C", "name": "Southeast Asia Expansion", "description": "..." },
    { "id": "D", "name": "Build DTC Ecosystem", "description": "..." }
  ],
  "config": {
    "anonymousMode": false,
    "pinProtected": false
  },
  "participants": [
    {
      "id": "uuid-v4",
      "name": "Alice Chen",
      "token": "uuid-v4",
      "pinHash": null,
      "status": "submitted",
      "addedAt": "ISO-8601"
    }
  ],
  "rounds": [
    {
      "roundNumber": 1,
      "status": "closed",
      "openedAt": "ISO-8601",
      "closedAt": "ISO-8601"
    }
  ],
  "currentRound": 2,
  "assessments": {
    "round_1": {
      "participant-uuid": {
        "A_Q1": { "score": 4, "rationale": "Strong fit because..." },
        "A_Q2": { "score": 3, "rationale": "" },
        "B_Q1": { "score": 5, "rationale": "Best scenario for Gen Z play..." }
      }
    }
  },
  "report": {
    "narrative": "Based on the group's assessment...",
    "generatedAt": "ISO-8601",
    "model": "gpt-4o-mini"
  }
}
```

### Storage Layout (DigitalOcean Spaces)

```
data/users.json
data/participation-tokens.json
users/{userId}/problems/index.json
users/{userId}/problems/{problemId}.SCN
```

No database server is required.

## API Endpoints

| Group | Endpoints |
|-------|-----------|
| **Auth** | `POST /api/v1/auth/login`, `POST /auth/logout`, `GET /auth/me`, `POST /auth/change-password` |
| **Problems** | `GET/POST /api/v1/problems`, `GET/PUT/DELETE /problems/:id`, `POST /problems/:id/save`, `GET /problems/:id/download`, `POST /problems/upload` |
| **Participants** | `GET/POST /api/v1/problems/:id/participants`, `PUT/DELETE /problems/:id/participants/:pid`, `POST /problems/:id/participants/:pid/regenerate-pin` |
| **Config & Rounds** | `PUT /api/v1/problems/:id/config`, `POST /problems/:id/round/close`, `POST /round/reopen`, `POST /round/new`, `POST /problems/:id/finalize` |
| **Consensus** | `GET /api/v1/problems/:id/consensus`, `GET /problems/:id/rounds` |
| **Participation** | `POST /api/v1/participate/:problemId/:token/verify-pin`, `GET /participate/:problemId/:token`, `PUT /participate/:problemId/:token` |
| **Compute** | `POST /api/v1/compute/robustness`, `POST /compute/consensus`, `POST /compute/aggregate` |
| **Admin** | `GET/POST /api/v1/admin/users`, `PUT/DELETE /admin/users/:id`, `POST /admin/users/:id/unlock`, `POST /admin/users/:id/reset-password` |
| **WebSocket** | `ws://host/ws/problems/:id/status` (admin JWT required) |
| **LLM** | `GET /api/v1/llm/status`, `POST /problems/:id/report/narrative`, `POST /problems/:id/report/narrative/regenerate` |
| **Health** | `GET /api/v1/health` |

## Page Structure

### Owner Pages (Authenticated)

| Page | Route | Description |
|------|-------|-------------|
| Login | `/` | Shared login page |
| Problem List | `/problems` | Dashboard of all saved problems with create/load/delete actions |
| Problem Editor | `/problems/:id/edit` | Define axes, scenarios, alternatives; manage participants |
| Assessment View | `/problems/:id/assess` | Owner completes their own impact assessment (if self-added as participant) |
| Results | `/problems/:id/results` | Robustness ranking, heatmap, consensus analysis, report generation |
| Report | `/problems/:id/report` | Printable decision report (opens in new window) |

### Participant Pages (Token-Based)

| Page | Route | Description |
|------|-------|-------------|
| PIN Verification | `/participate/:problemId/:token` | PIN entry (if required), then redirects to assessment |
| Assessment | `/participate/:problemId/:token/assess` | Read-only view of axes and scenarios; input impact ratings and rationales |
| Confirmation | `/participate/:problemId/:token/done` | Submission confirmation with option to revise (if round is still open) |

## User Interface

### Problem Editor

The editor is a single-page workflow with collapsible sections:

1. **Problem Definition** — Title and description fields
2. **Uncertainty Axes** — Two axis editors, each with a label and two pole descriptions; the 2×2 matrix preview updates in real time as poles are edited
3. **Scenario Cards** — Four cards arranged in a 2×2 grid; each card shows the axis combination and has fields for the scenario name and narrative
4. **Alternatives** — List of strategic alternatives with add/edit/remove; drag-to-reorder
5. **Participants** — Add participants, generate tokenized links, toggle anonymous mode and PIN protection; real-time status indicators (Pending / In Progress / Submitted)
6. **Round Management** — Close current round, view results, open new round for Delphi iteration

### Participant Assessment

The participant sees:

- **Read-only context** — Problem title, description, axis definitions, and scenario narratives (they cannot modify the problem structure)
- **Assessment grid** — A matrix with alternatives as rows and scenarios as columns; each cell contains a 5-point rating selector and an optional rationale text field
- **Progress indicator** — Shows how many cells have been rated out of the total
- **Save draft / Submit** — Participants can save partial work and return later; submission locks their responses for the current round

### Results Dashboard

The results page displays:

- **Robustness Ranking Table** — Alternatives ranked by mean score across scenarios, with fragility index and per-scenario scores
- **Heatmap** — Color-coded matrix (alternatives × scenarios) where darker shading indicates stronger fit; click a cell to see aggregated rationales
- **Consensus Panel** — Kendall's W with interpretation, per-scenario agreement breakdown, and round-over-round convergence chart (if multiple Delphi rounds)
- **Report Generation** — Button to generate the printable report; button to generate or regenerate the AI narrative

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SESSION_SECRET` | Yes | — | Secret for signing session cookies |
| `JWT_SECRET` | Yes | — | Secret for signing JWTs |
| `SPACES_ENDPOINT` | Yes | — | DigitalOcean Spaces endpoint |
| `SPACES_KEY` | Yes | — | Spaces access key |
| `SPACES_SECRET` | Yes | — | Spaces secret key |
| `SPACES_BUCKET` | Yes | — | Spaces bucket name |
| `SPACES_REGION` | Yes | — | Spaces region |
| `APP_URL` | No | `http://localhost:8000` | Frontend URL for CORS and participation links |
| `NODE_ENV` | No | `development` | Environment mode |
| `PORT` | No | `8000` | Server port |
| `OPENAI_API_KEY` | No | — | OpenAI API key (enables LLM features) |
| `LLM_ENABLED` | No | `true` | Set to `false` to disable LLM features even with an API key |
| `OPENAI_MODEL` | No | `gpt-4o-mini` | Primary OpenAI model |
| `OPENAI_FALLBACK_MODEL` | No | `gpt-4o-mini` | Fallback model on primary failure |
| `OPENAI_TIMEOUT_MS` | No | `14000` | Per-call API request timeout (total budget hard-capped at 28s) |
| `OPENAI_MAX_RETRIES` | No | `0` | Retries per model before fallback |

## Project Structure

```
scenario_planning_studio/
├── run.py                         # Application launcher
├── Procfile                       # App Platform run command
├── requirements.txt
├── .env.example                   # Environment variable template
├── app/
│   ├── main.py                    # FastAPI app, middleware, startup
│   ├── config.py                  # Application configuration
│   ├── auth/
│   │   ├── login_manager.py       # Authentication, session management
│   │   └── password_manager.py    # bcrypt hash/verify
│   ├── core/
│   │   ├── problems.py            # Problem CRUD, .SCN file I/O
│   │   ├── scenarios.py           # Axis, scenario, alternative management
│   │   ├── assessments.py         # Impact assessment storage and retrieval
│   │   ├── participants.py        # Participant CRUD, token generation, PIN management
│   │   ├── rounds.py              # Round lifecycle (open, close, reopen, new)
│   │   ├── compute.py             # Robustness ranking, fragility index, aggregation
│   │   └── consensus.py           # Kendall's W, per-scenario agreement, IQR
│   ├── ai/
│   │   ├── openai_client.py       # OpenAI API client with timeout and fallback
│   │   └── prompts.py             # System prompts for report narrative generation
│   ├── data/
│   │   └── csv_manager.py         # CSV read/write helpers (if needed for user data)
│   ├── storage/
│   │   ├── config.py              # Storage backend selection
│   │   └── store.py               # DO Spaces / local filesystem abstraction
│   └── routes/
│       ├── auth_routes.py         # Login/logout, session cookies
│       ├── problem_routes.py      # Problem CRUD, editor pages
│       ├── participant_routes.py  # Tokenized participation flow
│       ├── compute_routes.py      # Robustness, consensus API endpoints
│       ├── admin_routes.py        # User management
│       ├── llm_routes.py          # Report narrative generation
│       └── ws_routes.py           # WebSocket status updates
├── web/
│   ├── templates/
│   │   ├── login.html             # Shared login page
│   │   ├── problem_list.html      # Problem dashboard
│   │   ├── problem_editor.html    # Axis, scenario, alternative editor
│   │   ├── assessment.html        # Owner assessment view
│   │   ├── participate_pin.html   # PIN verification for participants
│   │   ├── participate_assess.html # Participant assessment grid
│   │   ├── participate_done.html  # Submission confirmation
│   │   ├── results.html           # Robustness ranking, heatmap, consensus
│   │   ├── report.html            # Printable decision report
│   │   └── admin_users.html       # User management
│   └── static/
│       ├── style.css              # Application styles
│       └── js/
│           ├── editor.js          # Problem editor interactivity
│           ├── assessment.js      # Assessment grid logic
│           ├── results.js         # Heatmap rendering, chart interactions
│           └── ws.js              # WebSocket connection management
├── scripts/
│   └── provision_demo.py          # Demo data provisioning
└── tests/
    ├── test_compute.py            # Robustness and consensus computation tests
    ├── test_problems.py           # Problem CRUD tests
    ├── test_participation.py      # Token and assessment flow tests
    └── helpers/
        └── fixtures.py            # Test data generators
```

## Deployment

The application is deployed as a Python web service on **DigitalOcean App Platform**, with auto-deploy on push to `main`.

| Setting | Value |
|---------|-------|
| Source | GitHub — `jrmst102/scenario_planning_studio` |
| Branch | `main` |
| Type | Web Service |
| Build Command | `pip install -r requirements.txt` |
| Run Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |

The `Procfile` at the repo root defines the run command for App Platform auto-detection.

### Environment variables (App Platform)

Set in the App Platform UI. Mark secrets as **Encrypted**:

| Variable | Type |
|----------|------|
| `SESSION_SECRET` | SECRET |
| `JWT_SECRET` | SECRET |
| `SPACES_KEY` | SECRET |
| `SPACES_SECRET` | SECRET |
| `SPACES_ENDPOINT` | Plain |
| `SPACES_BUCKET` | Plain |
| `SPACES_REGION` | Plain |
| `APP_URL` | Plain |
| `OPENAI_API_KEY` | SECRET |

### Health check

```bash
curl https://your-app-url.ondigitalocean.app/api/v1/health
# → {"status":"ok"}
```

## Version Roadmap

| Version | Scope |
|---------|-------|
| **1.0.0** | Core workflow: problem editor, 2×2 matrix, alternatives, impact assessment, robustness ranking, .SCN file save/load, single-user mode |
| **1.1.0** | Group participation: tokenized links, PIN protection, anonymous mode, real-time status, aggregation, consensus (Kendall's W) |
| **1.2.0** | Delphi iteration: multi-round cycles, round history, convergence tracking |
| **1.3.0** | AI report narrative: LLM-generated unified narrative, inline editing, regeneration |
| **1.4.0** | Decision report: printable report with full analysis, heatmap, consensus summary |

## Integration with the Decision Tools Module

In the Strategic Decision-Making Lab, Scenario Planning Studio complements the other tools:

- **AHP Studio** answers: *"Given our priorities, which option ranks highest?"*
- **Game Theory** answers: *"How will competitors respond to our move?"*
- **Decision Trees** answer: *"What is the expected value of a staged approach?"*
- **Scenario Planning Studio** answers: *"Does our recommendation hold up across multiple plausible futures?"*

A team using Scenario Planning Studio alongside AHP Studio can present a particularly strong case: AHP identifies the highest-ranked option under current assumptions, while Scenario Planning shows whether that ranking is robust across different futures or fragile to a single assumption.

## Security

- bcrypt password hashing (cost factor 12)
- JWT with 24h expiry and httpOnly secure cookies
- 3-attempt account lockout
- Participation tokens: UUID v4 (122-bit entropy), scoped to single problem/participant
- PIN protection: bcrypt-hashed 4-digit PINs, 3-attempt lockout with 15-minute cooldown
- Participant session: short-lived JWT (4h) in httpOnly cookie after PIN verification
- HTTPS, CORS, Helmet-equivalent headers, rate limiting (60 req/min API, 5 req/15min PIN verification)
- LLM input sanitization: length limits, control character stripping, prompt injection mitigation via system prompts
- LLM rate controls: 10-second cooldown, 3 regenerations per session (1-hour TTL)

---

Copyright 2026 by Dr. Jose Mendoza. All rights reserved.
