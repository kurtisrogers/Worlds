# Fixture Data

Comprehensive demo dataset for local development.

## Load

```bash
python manage.py loadfixtures
python manage.py loadfixtures --flush      # wipe and reload
python manage.py loadfixtures --no-covers  # skip Pillow cover generation
```

## What's included

| Data | Count |
|------|-------|
| Authors | 4 |
| Readers | 3 (+ 2 legacy aliases) |
| Stories | 8 |
| Chapters | 21 |
| Saved books | 9 |
| Author follows | 7 |
| Subscriptions | 4 |
| Chapter unlocks | 3 |
| Comments | 6 |
| Reactions | 8 |
| Transactions | 3 |

## Accounts

All passwords: `demo1234`

### Authors

| Username | Genre | Stripe Connect |
|----------|-------|----------------|
| `elena_rivers` | Fantasy | ✓ |
| `marcus_chen` | Sci-fi | ✓ |
| `amara_okafor` | Literary | ○ |
| `james_wolf` | Thriller | ✓ |

### Readers

| Username | Profile |
|----------|---------|
| `alex_reader` | Power user — subscriptions, saves, comments |
| `sam_reader` | Literary fan |
| `jordan_reader` | Sci-fi/thriller fan |

### Legacy aliases

- `demo_author` (same as `elena_rivers`)
- `demo_reader` (same as `alex_reader`)

## Customizing

Edit `accounts/fixture_data.py` to add stories, chapters, library relationships, and engagement data. The loader in `accounts/management/commands/loadfixtures.py` handles creation and cover image generation.
