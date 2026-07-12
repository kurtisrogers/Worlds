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

Load sample stories and chapters:

```bash
python manage.py loaddata demo
```

Demo accounts (password: `demo1234`):

- `demo_author` — sample author with a published story
- `demo_reader` — sample reader account
