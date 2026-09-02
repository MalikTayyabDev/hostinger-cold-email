"""Vercel serverless entry — lazy load to surface startup errors."""
import os
import traceback

from logging_config import setup_logging

log = setup_logging("vercel")


def _build_app():
    from app import create_app
    return create_app()


try:
    app = _build_app()
except Exception:
    log.error("Failed to initialize app:\n%s", traceback.format_exc())
    raise
