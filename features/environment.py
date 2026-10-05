"""Behave environment setup for Django."""

import os

import django
from django.core.management import call_command
from django.test.utils import setup_test_environment, teardown_test_environment

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")
django.setup()

import editor.assist  # noqa: E402


def before_all(context):
    setup_test_environment()


def after_all(context):
    teardown_test_environment()


def before_scenario(context, scenario):
    call_command("flush", verbosity=0, interactive=False)


def after_scenario(context, scenario):
    settings_override = getattr(context, "ai_settings", None)
    if settings_override is not None:
        settings_override.disable()
        context.ai_settings = None
    provider = getattr(context, "_provider", None)
    if provider is not None:
        editor.assist.get_provider = provider
        context._provider = None
