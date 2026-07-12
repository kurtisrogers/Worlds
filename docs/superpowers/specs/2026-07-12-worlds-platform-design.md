# Worlds Platform Design

## Vision

Worlds connects emerging authors with readers who fund publishing directly—no algorithms, no gatekeepers. Authors release chapters, offer tiered subscriptions, and sync content from Google Sheets, document uploads, or an in-app editor. The platform takes 2% of transactions to cover operating costs.

## Architecture

Monolithic Django application with HTMX for partial updates and Alpine.js for lightweight client interactivity. Stripe handles payments; Google Sheets API syncs chapter content; python-docx parses uploads.

```
worlds/
├── config/          # Django settings, URLs, WSGI
├── accounts/        # Users, author profiles, authentication
├── stories/         # Books, chapters, reading experience
├── payments/        # Stripe checkout, subscriptions, 2% fee
├── integrations/    # Google Sheets sync, document upload
└── editor/          # In-app chapter editor
```

## Data Model

- **AuthorProfile**: extends User with bio, Stripe Connect account ID
- **Story**: title, slug, synopsis, cover, author, status (draft/publishing/published)
- **Chapter**: story FK, number, title, content (HTML), unlock_price_cents (nullable), tier_required (bronze/silver/gold/none)
- **SubscriptionTier**: story FK, name (bronze/silver/gold), price_cents, benefits
- **ReaderSubscription**: reader, story, tier, Stripe subscription ID
- **ChapterUnlock**: reader, chapter, amount paid
- **GoogleSheetConnection**: story FK, spreadsheet ID, sheet name, last_synced
- **DocumentUpload**: story FK, file, parsed_at

## Payment Flow

1. Reader selects tier or chapter unlock → Stripe Checkout Session
2. Webhook confirms payment → grant access
3. Platform fee: 2% retained via `application_fee_amount` on Stripe Connect

## Content Sources (priority: editor > upload > sheets)

Authors choose a primary source per story. Sync jobs pull Google Sheets rows (chapter number, title, body). DOCX uploads extract paragraphs. Editor saves directly to Chapter.content.

## Frontend

- Tailwind CSS via CDN for rapid styling
- Literary reading experience: generous typography, dark/light mode
- HTMX for chapter navigation, unlock modals, editor autosave
- Alpine.js for tier selection, theme toggle, mobile menu

## Testing

- **BDD**: behave features for author/reader journeys
- **Functional**: Django TestCase for views, models, Stripe webhooks (mocked)
- **Pre-commit**: black, ruff, isort, trailing whitespace

## Documentation & Landing

- MkDocs site in `docs/` with setup, API, author guide
- GitHub Pages static landing in `landing/` with mission statement and CTA
