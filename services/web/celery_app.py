"""
services/web/celery_app.py
──────────────────────────
Celery factory that integrates with the Flask application context so that
all task code can safely use SQLAlchemy models, Flask-Login helpers, and
app.config values without triggering "working outside of application context"
errors.

Usage
──────
from celery_app import make_celery
celery = make_celery(app)
"""

from celery import Celery


def make_celery(app):
    """Build a Celery instance wired to the Flask app.

    The ContextTask base ensures every task body runs inside an active
    Flask application context, enabling db.session, current_app, etc.
    """
    celery = Celery(
        app.import_name,
        broker=app.config["broker_url"],
        backend=app.config["result_backend"],
    )

    # Push Flask config values into Celery namespace
    celery.conf.update(app.config)

    # Track STARTED state so /api/task/<id> can distinguish queued vs running
    celery.conf.task_track_started = True

    # Prevent serialization of large frames in result backend — tasks should
    # store results to disk and return a lightweight reference dict.
    celery.conf.task_serializer   = "json"
    celery.conf.result_serializer = "json"
    celery.conf.accept_content    = ["json"]

    # Store results for 24 hours (enough for the UI to poll)
    celery.conf.result_expires = 86_400

    class ContextTask(celery.Task):
        """Task subclass that automatically wraps execution in Flask app context."""
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return super().__call__(*args, **kwargs)

        def on_failure(self, exc, task_id, args, kwargs, einfo):
            """Update the Job row on hard failure (unhandled exception)."""
            from datetime import datetime
            try:
                with app.app_context():
                    from dataforge.db import db_get, db_update
                    job = db_get("jobs", task_id)
                    if job:
                        db_update("jobs", task_id, {
                            "status": "failure",
                            "error": str(exc)[:2000],
                            "finished_at": datetime.utcnow().isoformat()
                        })
            except Exception:
                pass  # best-effort; don't crash the worker

    celery.Task = ContextTask
    return celery
