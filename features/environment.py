"""Behave environment setup for Django."""

import os

import django
from django.test.utils import setup_test_environment, teardown_test_environment

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")
django.setup()


def before_all(context):
    setup_test_environment()


def after_all(context):
    teardown_test_environment()


def before_scenario(context, scenario):
    from django.core.management import call_command

    call_command("flush", verbosity=0, interactive=False)
