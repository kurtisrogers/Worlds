# Worlds

**Reader-funded publishing for the next generation of creatives.**

Worlds connects emerging authors with readers who fund publishing directly — no algorithms, no gatekeepers. Authors release chapters, offer tiered subscriptions (Bronze, Silver, Gold), and sync content from Google Sheets, document uploads, or our in-app editor.

We take **2%** of transactions to cover operating costs. The rest goes to creators.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py loaddata demo  # optional demo data
python manage.py runserver
```

Visit [http://localhost:8000](http://localhost:8000).

## Tech stack

| Layer | Technology |
|-------|------------|
| Backend | Django 6.1, Python 3.12 |
| Frontend | HTMX, Alpine.js, Tailwind CSS |
| Payments | Stripe Checkout & webhooks |
| Integrations | Google Sheets API, DOCX upload |
| Testing | pytest, behave (BDD) |
| Docs | MkDocs Material |
| Quality | pre-commit (black, ruff, isort) |

## Project structure

```
accounts/       User profiles and authentication
stories/        Books, chapters, reading experience
payments/       Stripe integration, 2% platform fee
integrations/   Google Sheets sync, document upload
editor/         In-app chapter editor with autosave
features/       BDD tests (behave)
tests/          Functional tests (pytest)
landing/        GitHub Pages static site
docs/           MkDocs documentation
```

## Running tests

```bash
# Functional tests
pytest

# BDD tests. Pending chapter-review scenarios are excluded here.
behave features/

# Chapter review, including panel scenarios that fail until issue #5.
make test-review-e2e

# Pre-commit
pre-commit run --all-files
```

## Documentation

```bash
mkdocs serve
```

## Environment variables

See `.env.example` for Stripe, Google OAuth, and database configuration.

AI assist is off by default. `OPENAI_API_KEY` is read from the environment or from secrets. It is not committed and it is not sent to the browser. The product rules are in `docs/authors/ai-partner.md`.

## Mission

Create the next generation of creatives. Do away with algorithms and predictive successes. Let readers decide what deserves to be published.
