# Configuration

Copy `.env.example` to `.env` and configure:

## Core

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Django secret key |
| `DEBUG` | `True` for development |
| `DATABASE_URL` | Default: SQLite |

## Stripe

| Variable | Description |
|----------|-------------|
| `STRIPE_PUBLISHABLE_KEY` | Stripe publishable key |
| `STRIPE_SECRET_KEY` | Stripe secret key |
| `STRIPE_WEBHOOK_SECRET` | Webhook signing secret |
| `PLATFORM_FEE_PERCENT` | Platform fee (default: 2) |

Set up a webhook endpoint at `/payments/webhook/stripe/` for `checkout.session.completed`.

## Google Sheets

| Variable | Description |
|----------|-------------|
| `GOOGLE_CLIENT_ID` | OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | OAuth client secret |
| `GOOGLE_REDIRECT_URI` | OAuth callback URL |
