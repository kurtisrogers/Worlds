"""Load demo data for development and testing.

Deprecated: use `loadfixtures` for the full dataset.
This command remains as a shortcut alias.
"""

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Load demo fixture data (alias for loadfixtures)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete existing fixture users and their content before loading",
        )

    def handle(self, *args, **options):
        call_command(
            "loadfixtures",
            flush=options["flush"],
        )
