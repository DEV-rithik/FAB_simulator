# PatternIQ — FAB Yield Simulator SaaS

A full-stack web application that turns the semiconductor FAB yield simulator into a multi-user SaaS platform. The UI preserves the exact design and page structure from the `stitch_dashboard` reference files.

## Tech Stack

| Layer | Choice |
|-------|--------|
| Frontend | HTML + [Tailwind CSS via CDN](https://tailwindcss.com/docs/installation/play-cdn) |
| Backend | [Django 6](https://www.djangoproject.com/) |
| Database | [Supabase](https://supabase.com/) (Postgres) — or SQLite for local dev |
| Auth | Django built-in (username + email + password) |
| PDF export | [ReportLab](https://www.reportlab.com/) |
| Charts | Matplotlib (server-side PNG generation) |

## Features

- **Auth** — Register, login, logout (username + email + password)
- **Dashboard** — At-a-glance yield metrics and recent run history
- **Simulation** — Configure and run SKY130 Monte Carlo yield analysis (same logic as `step1_yield_simulation.py`)
- **Results** — Wafer map, yield distribution histogram, Pareto chart, stat summary
- **History** — Paginated list of all past runs (per-user isolation)
- **Export** — CSV and PDF download per run

## Project Structure

```
FAB_simulator/
├── fab_saas/               # Django project package
│   ├── settings.py         # Configuration (DB, auth, static/media)
│   └── urls.py             # Root URL routing
├── simulator/              # Main Django app
│   ├── migrations/         # DB migrations
│   ├── models.py           # SimulationRun model
│   ├── services.py         # Simulator engine (wraps step1_yield_simulation logic)
│   ├── views.py            # Dashboard, config, results, history, export views
│   ├── views_auth.py       # Register / login / logout views
│   ├── urls.py             # Simulator URL patterns
│   ├── urls_auth.py        # Auth URL patterns
│   └── tests.py            # Tests for auth, runs, exports
├── templates/
│   ├── base.html           # Shared layout (nav, sidebar, footer)
│   ├── auth/               # Login & register pages
│   └── simulator/          # Dashboard, config, results, history pages
├── step1_yield_simulation.py  # Original standalone simulator (unchanged)
├── .env.example            # Required environment variables
├── manage.py
└── requirements.txt
```

## Local Setup

### 1. Prerequisites

- Python 3.10+
- pip

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env and set DJANGO_SECRET_KEY, DATABASE_URL (optional), etc.
```

> **Supabase**: Paste your Supabase connection string as `DATABASE_URL`.  
> Leave `DATABASE_URL` blank to use the built-in SQLite fallback (no extra setup needed).

### 4. Apply migrations

```bash
python manage.py migrate
```

### 5. Run the development server

```bash
python manage.py runserver
```

Then open **http://127.0.0.1:8000** in your browser.

### 6. Create your first account

Visit `/auth/register/` to create a user account, then log in at `/auth/login/`.

## Running Tests

```bash
python manage.py test simulator
```

16 tests covering: registration, login, dashboard access control, per-user run isolation, CSV export, and PDF export.

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `DJANGO_SECRET_KEY` | Yes (prod) | Long random string for signing sessions/tokens |
| `DJANGO_DEBUG` | No | `True` (default) or `False` |
| `ALLOWED_HOSTS` | No | Comma-separated hostnames, default `localhost,127.0.0.1` |
| `DATABASE_URL` | No | Supabase Postgres URI; falls back to SQLite if unset |

## Python / System Dependencies for PDF Generation

PDF export uses **ReportLab**, which is a pure-Python library — no system packages needed.  
Install it via `pip install reportlab` (already in `requirements.txt`).

## Supabase Database Configuration

1. Create a new project at [supabase.com](https://supabase.com)
2. Go to **Settings → Database → Connection string → URI**
3. Copy the URI and set it as `DATABASE_URL` in your `.env` file
4. Run `python manage.py migrate` to create all tables in Supabase

> Django uses direct Postgres connection (not the Supabase JS client), so no Supabase-specific SDK is needed.
