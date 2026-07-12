"""Template context processors."""

from django.conf import settings


def platform_settings(request):
    return {
        "PLATFORM_NAME": "Worlds",
        "PLATFORM_FEE_PERCENT": settings.PLATFORM_FEE_PERCENT,
        "STRIPE_PUBLISHABLE_KEY": settings.STRIPE_PUBLISHABLE_KEY,
        "TIER_DEFAULTS": settings.TIER_DEFAULTS,
    }
