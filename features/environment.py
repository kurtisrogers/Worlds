"""Behave environment setup for Django."""

import os
import urllib.request

import django
from django.conf import settings
from django.core.management import call_command
from django.test.utils import setup_test_environment, teardown_test_environment

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")
django.setup()

_REAL_URL_OPEN = urllib.request.urlopen


def _guard_urlopen(url, *args, **kwargs):
    """Refuse the live OpenAI API. Other URLs keep the real opener."""
    target = url.full_url if hasattr(url, "full_url") else str(url)
    if "openai.com" in target.lower():
        calls = getattr(_guard_urlopen, "calls", None)
        if calls is not None:
            calls.append(target.split("?", 1)[0])
        raise AssertionError(
            "BDD must not call the live OpenAI API. "
            "Stub the client at editor.assist.get_provider."
        )
    return _REAL_URL_OPEN(url, *args, **kwargs)


def before_all(context):
    setup_test_environment()
    urllib.request.urlopen = _guard_urlopen


def after_all(context):
    urllib.request.urlopen = _REAL_URL_OPEN
    teardown_test_environment()


def before_scenario(context, scenario):
    _guard_urlopen.calls = []
    context.live_openai_calls = _guard_urlopen.calls
    context._setting_originals = {}
    _assign_settings(context, OPENAI_API_KEY="")
    call_command("flush", verbosity=0, interactive=False)


def after_scenario(context, scenario):
    module = getattr(context, "_provider_module", None)
    original = getattr(context, "_original_get_provider", None)
    if module is not None and original is not None:
        module.get_provider = original
    for key, value in getattr(context, "_setting_originals", {}).items():
        setattr(settings, key, value)
    _guard_urlopen.calls = []


def _assign_settings(context, **kwargs):
    originals = context._setting_originals
    for key, value in kwargs.items():
        if key not in originals:
            originals[key] = getattr(settings, key)
        setattr(settings, key, value)
