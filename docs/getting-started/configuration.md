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

## AI assist

Assist is off by default. The OpenAI credential is `OPENAI_API_KEY`, read from the environment or the platform's secrets. Leave it empty here. It is not a value you commit, and it is not sent to the browser.

Product rules, the audit record, and what happens to prompt and response text are in [AI creative partner](../authors/ai-partner.md).

| Variable | Description |
|----------|-------------|
| `AI_ASSIST_ENABLED` | `False` by default |
| `WORLDS_ENVIRONMENT` | `local` or `shared` |
| `OPENAI_API_KEY` | OpenAI credential. Empty in the repo |
| `OPENAI_MODEL` | Model name assembled on the server |
| `OPENAI_TIMEOUT_SECONDS` | How long a call may wait |
| `AI_USER_RATE_LIMIT` | Optional. Calls per user in the window. No number is fixed |
| `AI_USER_RATE_WINDOW_SECONDS` | Optional. Window for the rate limit. Required if the limit is set |
| `AI_SPEND_CAP_CENTS` | Optional. Per-user spend cap in cents. No number is fixed |
| `AI_SPEND_WINDOW_SECONDS` | Optional. Window for the spend cap. Empty means all recorded spend |
| `OPENAI_INPUT_CENTS_PER_MILLION_TOKENS` | Optional price used to enforce a spend cap |
| `OPENAI_OUTPUT_CENTS_PER_MILLION_TOKENS` | Optional price used to enforce a spend cap |

Local development may run without the cap. Any shared environment must have both caps before the flag is on. Set `WORLDS_ENVIRONMENT=shared` outside a single writer's machine.
