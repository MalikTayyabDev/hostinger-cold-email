"""Vercel Cron endpoints — one email per invocation (serverless-safe)."""
import os

from flask import Blueprint, jsonify, request

from services import scheduler_service

cron_bp = Blueprint("cron", __name__, url_prefix="/api/cron")


def _authorized():
    secret = os.getenv("CRON_SECRET", "")
    if not secret:
        return True  # allow if unset (local dev only)
    return request.headers.get("Authorization") == f"Bearer {secret}"


def register_cron(app, con, cfg):
    @cron_bp.route("/inbox", methods=["GET", "POST"])
    def cron_inbox():
        if not _authorized():
            return jsonify({"error": "Unauthorized"}), 401
        result = scheduler_service.process_inbox(con, cfg)
        return jsonify({"ok": True, **result})

    @cron_bp.route("/send", methods=["GET", "POST"])
    def cron_send():
        if not _authorized():
            return jsonify({"error": "Unauthorized"}), 401
        # One email per cron tick — safe for Vercel timeouts
        result = scheduler_service.send_batch(con, cfg, limit=1)
        return jsonify({"ok": True, **result})

    app.register_blueprint(cron_bp)
