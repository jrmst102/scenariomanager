# Scenario Planning Studio

**v1.0** — A web-based decision support application for structured 2×2 scenario planning analysis. Define two critical uncertainties, construct a scenario matrix, assess how strategic alternatives perform across each future, and generate a robustness ranking — all from a browser.

Built for the **Competitive Strategy — Decision Tools Module** and designed to deploy on **DigitalOcean App Platform**.

## Features

- **2×2 Scenario Matrix** — Define two uncertainty axes with high/low poles; four scenarios generated automatically
- **Strategic Alternatives** — Up to 8 alternatives rated on a 5-point scale across all scenarios
- **Robustness Ranking** — Mean score + fragility index (std dev) identifies robust vs. fragile strategies
- **Group Participation** — Up to 12 participants per problem via tokenized links (no account required)
- **Consensus Measurement** — Kendall's W coefficient of concordance with chi-squared test; per-scenario agreement breakdown
- **Delphi Iteration** — Multi-round assessment cycles for convergence
- **AI Report Narrative** — LLM-generated summary of findings (OpenAI, optional)
- **PIN Protection** — Optional bcrypt-hashed PIN with lockout
- **Import/Export** — `.SCN` file format (JSON) for sharing problems
- **Print-ready Report** — Full decision report formatted for browser print-to-PDF

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, Uvicorn, Jinja2 |
| Frontend | Server-rendered HTML, Tailwind CSS (CDN), vanilla JS |
| Auth | bcrypt, itsdangerous (session cookies), PyJWT |
| Real-time | WebSocket with polling fallback |
| Storage | DigitalOcean Spaces (S3) / local filesystem fallback |
| Computation | NumPy, SciPy |
| LLM | OpenAI API (gpt-4o-mini) — optional |
| Hosting | DigitalOcean App Platform |

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Provision demo users and sample data
python -m scripts.provision_demo

# Start the development server
python run.py
```

Open `http://localhost:8000` and log in with:

| Username | Password | Role |
|----------|----------|------|
| `admin` | `admin123` | Admin |
| `analyst` | `analyst123` | User |

The analyst account includes a sample problem (Vela Skincare — EU Market Entry) with pre-configured axes, scenarios, and alternatives, plus a fully completed sample (Apex Fitness: Platform Growth Strategy) with 5 participants, round-1 assessments, and a generated report narrative.

## Project Structure

```
app/
├── ai/              # OpenAI client and prompt templates
├── auth/            # Password hashing, JWT, session management
├── core/            # Business logic (problems, scenarios, assessments,
│                    #   participants, rounds, compute, consensus)
├── routes/          # FastAPI route handlers
├── storage/         # Storage abstraction (Spaces + local filesystem)
├── config.py        # Environment-based configuration
└── main.py          # App entry point, middleware, route registration
web/
├── static/          # CSS and JavaScript
└── templates/       # Jinja2 HTML templates
scripts/
└── provision_demo.py  # Demo data provisioning (also loads docs/*.SCN fixtures)
tests/
└── test_compute.py    # Robustness, aggregation, and Kendall's W tests
docs/
├── scenario-planning-studio.md  # Full specification
└── *.SCN                        # Sample problem fixtures (auto-loaded by provisioning)
```

## Environment Variables

Copy `.env.example` and configure:

| Variable | Description | Required |
|----------|-------------|----------|
| `SESSION_SECRET` | Signed cookie secret | Yes |
| `JWT_SECRET` | JWT signing secret | Yes |
| `SPACES_ENDPOINT` | DO Spaces endpoint URL | Production |
| `SPACES_KEY` | DO Spaces access key | Production |
| `SPACES_SECRET` | DO Spaces secret key | Production |
| `SPACES_BUCKET` | DO Spaces bucket name | Production |
| `SPACES_REGION` | DO Spaces region | Production |
| `OPENAI_API_KEY` | OpenAI API key | For AI narratives |
| `APP_URL` | Public application URL | Production |

When Spaces credentials are not set, the app uses local filesystem storage (`local_data/`).

## DigitalOcean Deployment

The app is Procfile-ready for DO App Platform:

1. Connect the GitHub repo to a new DO App
2. Set environment variables in the App settings
3. The platform auto-detects the `Procfile` and deploys with Uvicorn

## Documentation

See [docs/scenario-planning-studio.md](docs/scenario-planning-studio.md) for the full specification.

## Sample Data

The provisioning script loads `.SCN` fixture files from `docs/`:

- **Vela Skincare — EU Market Entry** — Draft problem with axes, scenarios, and 5 alternatives (no assessments)
- **Apex Fitness: Platform Growth Strategy** — Completed problem with 5 participants, full round-1 assessments with rationales, and LLM-generated report narrative

Drop additional `.SCN` files into `docs/` and re-run `python -m scripts.provision_demo` to load them.

## License

See [LICENSE](LICENSE).
