"""Base Django settings for Worlds platform."""

from pathlib import Path

import environ

env = environ.Env(
    DEBUG=(bool, False),
    PLATFORM_FEE_PERCENT=(int, 2),
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent

environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="django-insecure-dev-key-change-in-production")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_htmx",
    "accounts",
    "stories",
    "payments",
    "integrations",
    "editor",
    "library",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "config.context_processors.platform_settings",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {"default": env.db(default="sqlite:///db.sqlite3")}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "stories:dashboard"
LOGOUT_REDIRECT_URL = "stories:home"

# Stripe
STRIPE_PUBLISHABLE_KEY = env("STRIPE_PUBLISHABLE_KEY", default="")
STRIPE_SECRET_KEY = env("STRIPE_SECRET_KEY", default="")
STRIPE_WEBHOOK_SECRET = env("STRIPE_WEBHOOK_SECRET", default="")
PLATFORM_FEE_PERCENT = env("PLATFORM_FEE_PERCENT")

# Google OAuth / Sheets
GOOGLE_CLIENT_ID = env("GOOGLE_CLIENT_ID", default="")
GOOGLE_CLIENT_SECRET = env("GOOGLE_CLIENT_SECRET", default="")
GOOGLE_REDIRECT_URI = env(
    "GOOGLE_REDIRECT_URI", default="http://localhost:8000/integrations/google/callback/"
)


def _optional_int(name):
    raw = env(name, default="")
    if raw is None or str(raw).strip() == "":
        return None
    return int(raw)


# AI assist. Off by default. OpenAI is the only provider.
# Caps are unset so local development can run without them.
# A shared environment must set both caps before the flag is turned on.
AI_ASSIST_ENABLED = env.bool("AI_ASSIST_ENABLED", default=False)
OPENAI_API_KEY = env("OPENAI_API_KEY", default="")
OPENAI_MODEL = env("OPENAI_MODEL", default="gpt-4o-mini")
OPENAI_TIMEOUT_SECONDS = env.int("OPENAI_TIMEOUT_SECONDS", default=30)
_environment = env("WORLDS_ENVIRONMENT", default="").strip().lower()
if _environment not in {"local", "shared"}:
    WORLDS_ENVIRONMENT = "local" if DEBUG else "shared"
else:
    WORLDS_ENVIRONMENT = _environment
AI_USER_RATE_LIMIT = _optional_int("AI_USER_RATE_LIMIT")
AI_USER_RATE_WINDOW_SECONDS = _optional_int("AI_USER_RATE_WINDOW_SECONDS")
AI_SPEND_CAP_CENTS = _optional_int("AI_SPEND_CAP_CENTS")
AI_SPEND_WINDOW_SECONDS = _optional_int("AI_SPEND_WINDOW_SECONDS")
OPENAI_INPUT_CENTS_PER_MILLION_TOKENS = _optional_int(
    "OPENAI_INPUT_CENTS_PER_MILLION_TOKENS"
)
OPENAI_OUTPUT_CENTS_PER_MILLION_TOKENS = _optional_int(
    "OPENAI_OUTPUT_CENTS_PER_MILLION_TOKENS"
)

# Subscription tier defaults (cents)
TIER_DEFAULTS = {
    "bronze": {"price_cents": 499, "label": "Bronze", "color": "#cd7f32"},
    "silver": {"price_cents": 999, "label": "Silver", "color": "#c0c0c0"},
    "gold": {"price_cents": 1999, "label": "Gold", "color": "#ffd700"},
}
