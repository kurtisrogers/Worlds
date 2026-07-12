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
python manage.py loadfixtures   # comprehensive demo data (--flush to reset)
python manage.py runserver
```

Visit [http://localhost:8000](http://localhost:8000).

## Tech stack

| Layer | Technology |
|-------|------------|
| Backend | Django 5, Python 3.12 |
| Frontend | HTMX, Alpine.js, Tailwind CSS |
| Payments | Stripe Checkout, Connect payouts & webhooks |
| Editor | TipTap rich-text with HTML rendering |
| Integrations | Google OAuth, Sheets API, DOCX upload |
| Engagement | Chapter comments & reactions (HTMX) |
| Testing | pytest, behave (BDD) |
| Docs | MkDocs Material |
| Quality | pre-commit (black, ruff, isort) |

## Project structure

```
accounts/       User profiles and authentication
stories/        Books, chapters, reading experience
payments/       Stripe integration, Connect payouts, 2% fee
integrations/   Google OAuth, Sheets sync, document upload
editor/         TipTap rich-text editor with autosave
library/        Saved books, follows, Kindle-style library
engagement/     Chapter comments and reactions
features/       BDD tests (behave)
tests/          Functional tests (pytest)
landing/        GitHub Pages static site
docs/           MkDocs documentation
```

## Running tests

```bash
# Functional tests
pytest

# BDD tests
behave features/

# Pre-commit
pre-commit run --all-files
```

## Documentation

```bash
mkdocs serve
```

## Environment variables

See `.env.example` for Stripe, Google OAuth, and database configuration.

## Mission

Create the next generation of creatives. Do away with algorithms and predictive successes. Let readers decide what deserves to be published.
