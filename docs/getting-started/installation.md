# Installation

## Requirements

- Python 3.12+
- pip

## Steps

```bash
git clone <repo-url>
cd worlds
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser  # optional
python manage.py runserver
```

## Demo data

Load a full demo dataset with authors, stories, library data, comments, and reactions:

```bash
python manage.py loadfixtures
python manage.py loadfixtures --flush   # reset and reload
python manage.py loadfixtures --no-covers  # skip cover image generation
```

`loaddemo` is an alias for `loadfixtures`.

Demo accounts (password: `demo1234`):

**Authors**
- `elena_rivers` — fantasy (Stripe Connect active)
- `marcus_chen` — sci-fi (Stripe Connect active)
- `amara_okafor` — literary fiction
- `james_wolf` — thriller (Stripe Connect active)

**Readers**
- `alex_reader` — subscriptions, saved books, comments
- `sam_reader` — follows literary authors
- `jordan_reader` — sci-fi/thriller fan

**Legacy aliases:** `demo_author` → `elena_rivers`, `demo_reader` → `alex_reader`
