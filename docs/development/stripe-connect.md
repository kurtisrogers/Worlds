# Stripe Connect

Authors receive payouts directly via **Stripe Connect Express**.

## Setup

1. Go to **Payouts** in the navigation
2. Click **Connect with Stripe**
3. Complete Stripe's Express onboarding flow
4. Once verified, reader payments transfer automatically

## How payouts work

- Chapter unlocks and subscriptions use **destination charges**
- Worlds retains a 2% application fee
- The remainder transfers to the author's connected account
- Webhook `account.updated` keeps onboarding status in sync

## Webhooks

Add `account.updated` to your Stripe webhook endpoint alongside `checkout.session.completed`.
