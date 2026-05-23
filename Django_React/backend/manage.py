#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def _configure_dev_runserver():
    """Speed up local `runserver` when developers do not pass flags manually."""
    if len(sys.argv) < 2 or sys.argv[1] != "runserver":
        return
    if "--skip-checks" not in sys.argv:
        sys.argv.append("--skip-checks")


def main():
    """Run administrative tasks."""
    _configure_dev_runserver()
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CustomerClub.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
