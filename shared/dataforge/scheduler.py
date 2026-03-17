"""
Scheduler
═════════
Thin APScheduler wrapper that:
  - Starts a BackgroundScheduler on app init
  - Stores schedule definitions in the DB (ReportSchedule model)
  - Reloads all persisted jobs on startup
  - Provides helpers to add / remove / list jobs

Usage::

    # In app.py after db.create_all():
    from dataforge.scheduler import scheduler, init_scheduler
    init_scheduler(app)

    # To schedule a report:
    from dataforge.scheduler import add_report_job
    add_report_job(upload_id=42, cron="0 9 * * 1",  # every Monday 9 AM
                   email="ceo@example.com")
"""

import logging
from datetime import datetime

from .settings import PROJECTS_DIR

log = logging.getLogger(__name__)

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    _APSCHEDULER_AVAILABLE = True
except ImportError:
    _APSCHEDULER_AVAILABLE = False
    log.warning("APScheduler not installed — scheduled reports disabled. pip install apscheduler")

scheduler = None


def init_scheduler(app):
    """
    Initialise and start the background scheduler.
    Call once after db.create_all() in app.py.
    """
    global scheduler

    if not _APSCHEDULER_AVAILABLE:
        return

    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.start()
    log.info("BackgroundScheduler started.")

    # Reload all active schedules from DB
    with app.app_context():
        _reload_all_jobs(app)


def _reload_all_jobs(app):
    """Load persisted ReportSchedule rows and register cron jobs."""
    try:
        from dataforge.models import ReportSchedule
        schedules = ReportSchedule.query.filter_by(enabled=True).all()
        for s in schedules:
            _register_job(app, s)
        log.info("Loaded %d scheduled report jobs.", len(schedules))
    except Exception as exc:
        log.warning("Could not reload scheduled jobs: %s", exc)


def _register_job(app, schedule_row):
    """Register a single ReportSchedule as an APScheduler cron job."""
    if not scheduler:
        return
    job_id = f"report_{schedule_row.id}"
    try:
        trigger = CronTrigger.from_crontab(schedule_row.cron_expression, timezone="UTC")
        scheduler.add_job(
            func      = _run_scheduled_report,
            trigger   = trigger,
            id        = job_id,
            args      = [app, schedule_row.id],
            replace_existing = True,
            misfire_grace_time = 3600,
        )
    except Exception as exc:
        log.warning("Could not register job %s: %s", job_id, exc)


def _run_scheduled_report(app, schedule_id: int):
    """
    Called by APScheduler.  Runs inside the Flask app context.
    Loads data, runs insights, generates report, sends notifications.
    """
    with app.app_context():
        try:
            from dataforge.models import db, ReportSchedule, Upload, Report, Alert
            from dataforge.insight_engine import detect_schema, run_insights, summarise_with_gemini
            from dataforge.report_generator import generate_html_report
            from dataforge.alert_engine import AlertEngine
            import pickle, pathlib

            sched = db.session.get(ReportSchedule, schedule_id)
            if not sched or not sched.enabled:
                return

            upload = db.session.get(Upload, sched.upload_id)
            if not upload:
                return

            # Load the latest cleaned dataframe for this upload
            project_dir = PROJECTS_DIR / str(upload.id)
            pkl_path    = project_dir / "df_clean.pkl"
            if not pkl_path.exists():
                pkl_path = project_dir / "df_raw.pkl"
            if not pkl_path.exists():
                log.warning("No dataframe found for upload %s", upload.id)
                return

            with open(pkl_path, "rb") as f:
                df = pickle.load(f)

            # Run insight pipeline
            schema   = detect_schema(df)
            insights = run_insights(df, schema, top_n=6)
            summary  = summarise_with_gemini(
                insights,
                dataset_name  = upload.filename,
                dataset_type  = schema["dataset_type"],
                gemini_fn     = _get_gemini_fn(),
            )

            # Check alerts
            alert_engine = AlertEngine()
            fired_alerts = alert_engine.check(upload.id, df, schema)

            # Generate HTML
            html = generate_html_report(
                insights     = insights,
                summary_text = summary,
                dataset_name = upload.filename,
                dataset_type = schema["dataset_type"],
                profile      = {"rows": upload.rows, "cols": upload.cols, "missing_pct": upload.missing_pct},
                scheduled    = True,
            )

            # Persist report
            report = Report(
                upload_id    = upload.id,
                user_id      = upload.user_id,
                report_html  = html,
                report_json  = _to_json(insights, summary),
                triggered_by = "scheduler",
            )
            db.session.add(report)

            # Persist alerts
            for a in fired_alerts:
                alert_row = Alert(
                    upload_id    = upload.id,
                    user_id      = upload.user_id,
                    rule         = a["rule"],
                    message      = a["message"],
                    severity     = a["severity"],
                    metric       = a.get("metric", ""),
                    pct_change   = a.get("pct_change"),
                )
                db.session.add(alert_row)

            db.session.commit()
            log.info("Scheduled report complete — upload %s, %d insights, %d alerts",
                     upload.id, len(insights), len(fired_alerts))

            # Send notifications
            if sched.email:
                _send_email_report(sched.email, upload.filename, html, fired_alerts, alert_engine)
            if sched.slack_webhook:
                _send_slack(sched.slack_webhook, upload.filename, fired_alerts, alert_engine)

        except Exception as exc:
            log.exception("Scheduled report %s failed: %s", schedule_id, exc)


def _get_gemini_fn():
    """Return a callable that accepts a prompt and returns a string."""
    try:
        from dataforge.gemini_pipeline import _call_gemini
        return _call_gemini
    except Exception:
        return None


def _to_json(insights: list, summary: str) -> str:
    import json
    safe = []
    for ins in insights:
        row = {k: v for k, v in ins.items() if k != "chart_data"}
        safe.append(row)
    return json.dumps({"summary": summary, "insights": safe}, default=str)


def _send_email_report(to: str, dataset_name: str, html: str, alerts: list, engine):
    try:
        import smtplib, os
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        smtp_host = os.getenv("SMTP_HOST", "")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER", "")
        smtp_pass = os.getenv("SMTP_PASS", "")

        if not smtp_host or not smtp_user:
            log.warning("SMTP not configured — skipping email delivery.")
            return

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"DataForge Report — {dataset_name}"
        msg["From"]    = smtp_user
        msg["To"]      = to

        # Plain-text fallback
        plain = engine.format_email_body(alerts, dataset_name)
        msg.attach(MIMEText(plain, "plain"))
        msg.attach(MIMEText(html,  "html"))

        with smtplib.SMTP(smtp_host, smtp_port) as s:
            s.starttls()
            s.login(smtp_user, smtp_pass)
            s.sendmail(smtp_user, to, msg.as_string())

        log.info("Email report sent to %s", to)
    except Exception as exc:
        log.warning("Email delivery failed: %s", exc)


def _send_slack(webhook_url: str, dataset_name: str, alerts: list, engine):
    try:
        import requests as req
        payload = engine.format_slack_payload(alerts, dataset_name)
        if not payload:
            return
        req.post(webhook_url, json=payload, timeout=10)
        log.info("Slack notification sent.")
    except Exception as exc:
        log.warning("Slack delivery failed: %s", exc)


# ── Public helpers ────────────────────────────────────────────────────────────
def add_report_job(app, upload_id: int, cron: str, email: str = "", slack_webhook: str = "") -> int:
    """
    Persist a new ReportSchedule to DB and register the cron job.
    Returns the new schedule ID.
    """
    from dataforge.models import db, ReportSchedule
    sched = ReportSchedule(
        upload_id     = upload_id,
        cron_expression = cron,
        email         = email,
        slack_webhook = slack_webhook,
        enabled       = True,
    )
    db.session.add(sched)
    db.session.commit()
    _register_job(app, sched)
    return sched.id


def remove_report_job(schedule_id: int):
    """Disable a schedule and remove the APScheduler job."""
    from dataforge.models import db, ReportSchedule
    sched = db.session.get(ReportSchedule, schedule_id)
    if sched:
        sched.enabled = False
        db.session.commit()
    if scheduler:
        try:
            scheduler.remove_job(f"report_{schedule_id}")
        except Exception:
            pass


def list_jobs() -> list[dict]:
    """Return a list of currently registered APScheduler jobs."""
    if not scheduler:
        return []
    return [
        {"id": j.id, "next_run": str(j.next_run_time)}
        for j in scheduler.get_jobs()
    ]
