# Dynamic Pricing Sandbox

An educational browser-based simulation for learning dynamic pricing strategy. Adjust prices in real time, observe demand shifts, apply promotional tactics, and maximize revenue across four progressively challenging industry scenarios.

## Scenarios

| # | Scenario | Context | Elasticity | Demand Base | Inventory | Optimal Revenue |
|---|----------|---------|------------|-------------|-----------|-----------------|
| 1 | **E-Commerce** 🛒 | Holiday flash sale on wireless headphones | 1.4 (High) | 4 | 200 units | $18,000 |
| 2 | **Airline Seats** ✈️ | Pricing a regional flight as departure approaches | 1.1 (Medium) | 6 | 90 seats | $38,000 |
| 3 | **Hotel** 🏨 | Convention weekend room rate management | 0.9 (Low) | 5 | 60 rooms | $25,000 |
| 4 | **Event Tickets** 🎵 | Summer music festival ticket sales | 1.6 (Very High) | 8 | 500 tickets | $57,000 |

Scenarios unlock sequentially — score 60% pricing efficiency or higher to advance. Optimal revenue benchmarks are calibrated via dynamic programming so that passive play (no price changes) earns a failing grade, while active dynamic pricing with slider alone achieves B+/A.

## Features (v1.2.0)

- **User Authentication** — Login/logout with session-based auth; unauthenticated users are redirected to login
- **Home Page** — Authenticated landing page with app launcher
- **Protected Routes** — All sandbox routes require authentication
- **Scenario Briefing Screens** — Context, objectives, competitor intel, and strategic hints before each challenge
- **Configurable Tick Pacing** — Deliberate (5 min/tick, manual advance), Standard (1 min/tick), or Fast/Hard (2 sec/tick)
- **Competitor Price Display** — Scripted competitor pricing shown each tick on the price position indicator and revenue chart
- **Competitive Pressure** — Demand shifts based on your price relative to the competitor's
- **Discounts** — Apply 5–25% price reductions to lower effective price
- **Promotions** — Run time-limited campaigns (Social Media Blast, Email Campaign, Influencer Partnership, Loyalty Reward) with demand multipliers and costs
- **Bundles** — Scenario-specific product bundles that add a price premium and boost demand
- **Decision-Support Panel** — Collapsible insights panel with elasticity indicator, revenue trend, price sensitivity, demand forecast, competitor delta, and inventory burn rate
- **LLM-Powered Feedback** — AI-generated post-scenario strategy analysis via Anthropic Claude
- **Print Report** — Save or print scenario results as PDF from the browser's print dialog
- **Persistent Score Tracking** — Best score, number of attempts, and last attempt date per scenario (stored in localStorage, visible on /pricing)
- **Challenge Retake** — Replay any unlocked scenario; highest score retained

## Getting Started

**Prerequisites:** Node.js 22.x, npm 10.x

This project uses private packages from the `@jrmst102` GitHub Package Registry scope. Configure access before installing:

```bash
# Set up GitHub Package Registry access
echo "@jrmst102:registry=https://npm.pkg.github.com" >> .npmrc
export NODE_AUTH_TOKEN=<your-github-pat>

npm install
npm run dev
```

The dev server runs at `http://localhost:3000`.

For production serving (used by DigitalOcean App Platform):

```bash
npm run build
npm start        # serves the build/ directory on port 8080
```

## Dependencies

| Package | Source | Purpose |
|---------|--------|---------|
| `@jrmst102/ui-kit` | GitHub Package Registry | Shared UI components |
| `@jrmst102/shared-config` | GitHub Package Registry | Design tokens and app constants |
| `@jrmst102/auth-client` | GitHub Package Registry | Authentication provider, hooks, and protected routes |
| `react`, `react-dom` | npm | UI framework |
| `react-router-dom` | npm | Client-side routing |
| `recharts` | npm | Charting library |
| `tailwindcss` | npm | Utility-first CSS framework (required by ui-kit) |
| `serve` | npm | Static file server (production) |

## LLM Feedback Setup

Post-scenario AI feedback requires a proxy endpoint to securely call the Anthropic API without exposing the API key in client-side code.

### 1. Deploy the proxy function (DigitalOcean Functions)

```bash
# Install and authenticate the DigitalOcean CLI
doctl auth init

# Install serverless plugin and connect to your namespace
doctl serverless install
doctl serverless connect

# Create the runtime env file for Functions (gitignored)
cat > api/.env <<'EOF'
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
EOF

# Deploy the proxy
doctl serverless deploy api

# Get the function URL
doctl serverless functions get llm/feedback --url
```

The proxy function lives in `api/packages/llm/feedback/index.js`. It forwards requests to the Anthropic API with the key appended server-side.
The Functions runtime variable is mapped in `api/project.yml`.

### 2. Configure the frontend environment variable

For local development, create a `.env` file in the project root:

```
REACT_APP_LLM_PROXY_URL=https://your-function-url-here
```

For DigitalOcean App Platform: add `REACT_APP_LLM_PROXY_URL` as an App-Level Environment Variable in the app settings.
This value is compiled into the React bundle at build time, so changing it requires a rebuild/redeploy of the app.

### 3. API key management

Store your Anthropic API key in `api/.env` (gitignored):

```
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
```

`ANTHROPIC_API_KEY` belongs to the DigitalOcean Functions runtime, not the React app. Adding it only to the root `.env` or App Platform app-level env vars will not make the proxy work.

The key is never embedded in client-side code. No personally identifiable information is sent to the API — only scenario configuration and in-session gameplay data.

If you rotate the Anthropic key, redeploy the function so the new runtime env is applied:

```bash
doctl serverless deploy api
```

### 4. Verify the proxy

Use a minimal test request to confirm the function can reach Anthropic:

```bash
FUNCTION_URL="$(doctl serverless functions get llm/feedback --url)"

curl -X POST "$FUNCTION_URL" \
    -H 'Content-Type: application/json' \
    -d '{"max_tokens":80,"messages":[{"role":"user","content":"Return exactly: ok"}]}'
```

Expected result: HTTP 200 with a response body containing `"text":"ok"`.

## Deployment

The application is deployed as a Node.js web service on **DigitalOcean App Platform**, with auto-deploy on push to `main`. The service builds the React app and serves the `build/` directory with `serve`.

| Setting | Value |
|---------|-------|
| Source | GitHub — `jrmst102/dynamic_sandbox` |
| Branch | `main` |
| Type | Web Service |
| Build Command | `npm run build` |
| Run Command | `npm start` |
| Environment Variable | `REACT_APP_LLM_PROXY_URL` (App-Level) |
| Environment Variable | `NODE_AUTH_TOKEN` (App-Level, for GitHub Package Registry) |

**Notes:**

- The DigitalOcean App Platform build environment needs `NODE_AUTH_TOKEN` set so `npm install` can fetch `@jrmst102/*` packages from the GitHub Package Registry. The `.npmrc` file in the repo configures the registry scope.
- `REACT_APP_LLM_PROXY_URL` must point to the deployed `llm/feedback` function URL.
- `ANTHROPIC_API_KEY` is required by DigitalOcean Functions and should be managed in `api/.env` before running `doctl serverless deploy api`.

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Framework | React 19 (functional components, hooks) |
| Charting | Recharts 3 |
| UI Components | `@jrmst102/ui-kit` — Button, Card, Select, Spinner (GitHub Package Registry) |
| Design Tokens | `@jrmst102/shared-config` — colors, shadows, radii (GitHub Package Registry) |
| CSS Framework | Tailwind CSS 3 with shared-config color palette |
| Fonts | DM Sans, DM Mono (Google Fonts CDN) |
| LLM Integration | Anthropic API (Claude Sonnet 4) via serverless proxy |
| Hosting | DigitalOcean App Platform |
| Serverless | DigitalOcean Functions (LLM proxy) |

## Project Structure

```
src/
├── App.js                  # Main app — screen routing, state management
├── engine.js               # Simulation engine — demand, sales, sentiment, scoring
├── scenarios.js            # Scenario configurations, promotions, discount levels
├── styles.js               # Shared design tokens from @jrmst102/shared-config
├── index.js                # React entry point
├── index.css               # Tailwind directives + ui-kit base styles
└── components/
    ├── LevelSelect.js      # Level select menu with unlock state and best scores
    ├── ScenarioBriefing.js  # Pre-scenario briefing with metrics and tick mode selector
    ├── Gameplay.js          # Gameplay screen with visualizations and promotional controls
    ├── Results.js           # Grade badge, revenue breakdown, LLM feedback, retry
    ├── HelpPage.js          # "What is Dynamic Pricing?" educational content
    ├── TermsPage.js         # Terms and Conditions
    └── PrivacyPage.js       # Privacy Policy
api/
├── project.yml             # DigitalOcean Functions config
└── packages/llm/feedback/
    └── index.js             # Anthropic API proxy function
.npmrc                       # GitHub Package Registry scope config
tailwind.config.js           # Tailwind CSS config with shared-config colors
postcss.config.js            # PostCSS config for Tailwind processing
```

## License

MIT — see [LICENSE](LICENSE) for details.

## Author

Dr. Jose Mendoza
