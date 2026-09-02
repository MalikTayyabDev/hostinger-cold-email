import traceback

try:
    from app import create_app
    app = create_app()
except Exception as exc:
    traceback.print_exc()
    from flask import Flask

    app = Flask(__name__)
    _error = f"{type(exc).__name__}: {exc}"

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def startup_error(path):
        return (
            "<h1>Startup error</h1>"
            f"<pre>{_error}</pre>"
            "<p>Check DATABASE_URL in Vercel (use Supabase pooler port 6543).</p>"
        ), 500
