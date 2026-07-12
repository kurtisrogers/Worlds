# Stripe Integration

## Checkout flows

- **Chapter unlock**: One-time payment via `create_chapter_checkout_session`
- **Subscription**: Recurring monthly via `create_subscription_checkout_session`

## Webhooks

Configure Stripe to send `checkout.session.completed` to:

```
https://your-domain/payments/webhook/stripe/
```

The webhook handler grants chapter access or activates subscriptions.

## Platform fee

The 2% fee is calculated in `payments.services.calculate_fees` and recorded on each `Transaction`.

## Local testing

Use the [Stripe CLI](https://stripe.com/docs/stripe-cli) to forward webhooks:

```bash
stripe listen --forward-to localhost:8000/payments/webhook/stripe/
```
