"""
Shared configuration helpers for the command-line scripts.

Centralizes the loading of secrets from the environment (or a .env file)
so the individual scripts don't repeat the boilerplate, and so we never
accidentally log the token.
"""

import os
import sys

import dotenv
import structlog

from lib.moodle_api import URL, MoodleClient

log = structlog.get_logger()


def _require_env(name: str) -> str:
    dotenv.load_dotenv()
    value = os.getenv(name)
    if not value:
        sys.exit(f"Missing environment variable '{name}'")
    return value


def get_moodle_client() -> MoodleClient:
    """Build a MoodleClient from the TOKEN environment variable.

    Exits with an error message if TOKEN is not set.
    """
    token = _require_env("TOKEN")
    # Note: we deliberately don't log the token, it is a secret.
    log.info("connecting", url=URL)
    return MoodleClient(URL, token)


def get_salt() -> str:
    """Return the password salt from the SALT environment variable.

    Exits with an error message if SALT is not set.
    """
    return _require_env("SALT")
