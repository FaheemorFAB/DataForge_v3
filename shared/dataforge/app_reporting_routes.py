"""
app_reporting_routes.py
═══════════════════════
New routes for the automated reporting engine.
Paste these into app.py (after existing routes, before `if __name__ == "__main__"`).

Also add to app.py imports section:
    from dataforge.insight_engine    import detect_schema, run_insights, summarise_with_gemini
    from dataforge.report_generator  import generate_html_report
    from dataforge.alert_engine      import AlertEngine
    from dataforge.scheduler         import init_scheduler, add_report_job, remove_report_job, list_jobs
    from dataforge.models            import (db, User, Upload, Analysis,
                                           InsightRecord, Report, Alert,
                                           ReportSchedule, DataSource)

And after db.create_all():
    init_scheduler(app)

And add to .env:
    SMTP_HOST=smtp.gmail.com
    SMTP_PORT=587
    SMTP_USER=you@gmail.com
    SMTP_PASS=your_app_password
    GOOGLE_SERVICE_ACCOUNT_JSON=/path/to/sa.json   # optional
"""

import json as _json
from datetime import datetime


# ══════════════════════════════════════════════════════════════════════════════
# API: INSIGHT ENGINE  — POST /api/insights/run
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/api/insights/run", methods=["POST"])
@login_required
@_require_df
def api_insights_run():
    """
    Run the full insight pipeline on the current session's dataset.
    Optionally accepts { "top_n": 6, "use_gemini": true } in the request body.
    Returns insights list + AI summary + detected schema.
    """
    body     = request.get_json(force=True) or {}
    top_n    = int(body.get("top_n", 6))
    use_gem  = bool(body.get("use_gemini", True))

    df_clean = _load("df_clean")
    df_raw   = _load("df_raw")
    df       = df_clean if df_clean is not None else df_raw

    # Pull feature importance from AutoML if available
    automl_meta = _load("automl_result")
    fi = {}
    if automl_meta and isinstance(automl_meta, dict):
        fi = automl_meta.get("feature_importance", {})

    schema   = detect_schema(df, feature_importance=fi)
    insights = run_insights(df, schema, top_n=top_n)

    # Gemini narrative
    gemini_fn = None
    if use_gem and gemini_available():
        try:
            from dataforge.gemini_pipeline import _call_gemini
            gemini_fn = _call_gemini
        except Exception:
            pass

    filename = session.get("filename", "Dataset")
    summary  = summarise_with_gemini(
        insights,
        dataset_name  = filename,
        dataset_type  = schema["dataset_type"],
        gemini_fn     = gemini_fn,
    )

    # Persist insight records to DB
    upload_id = session.get("db_upload_id")
    if upload_id and current_user.is_authenticated:
        _persist_insights(upload_id, current_user.id, insights)
        _save("last_insights", insights)
        _save("last_schema",   schema)
        _save("last_summary",  summary)

    _db_log_analysis("insights", f"{len(insights)} insights · {schema['dataset_type']}")

    # Serialise chart_data safely
    safe_insights = []
    for ins in insights:
        row = dict(ins)
        if row.get("chart_data"):
            row["chart_data"] = row["chart_data"]  # already JSON-serialisable
        safe_insights.append(row)

    return jsonify({
        "ok":           True,
        "insights":     safe_insights,
        "summary":      summary,
        "schema":       {
            "date":         schema.get("date"),
            "metrics":      schema.get("metrics", []),
            "dimensions":   schema.get("dimensions", []),
            "dataset_type": schema.get("dataset_type"),
        },
    })


def _persist_insights(upload_id: int, user_id: int, insights: list):
    """Save insight records to DB, replacing any previous run for this upload."""
    try:
        InsightRecord.query.filter_by(upload_id=upload_id).delete()
        for ins in insights:
            rec = InsightRecord(
                upload_id   = upload_id,
                user_id     = user_id,
                type        = ins.get("type", ""),
                title       = ins.get("title", ""),
                description = ins.get("description", ""),
                importance  = ins.get("importance", 0.0),
                chart_type  = ins.get("chart"),
                chart_data  = _json.dumps(ins.get("chart_data")) if ins.get("chart_data") else None,
                metric      = ins.get("metric", ""),
            )
            db.session.add(rec)
        db.session.commit()
    except Exception:
        db.session.rollback()


# ══════════════════════════════════════════════════════════════════════════════
# API: REPORTS  — generate, list, fetch
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/api/reports/generate", methods=["POST"])
@login_required
@_require_df
def api_report_generate():
    """
    Generate and save a full HTML report for the current dataset.
    Runs insight engine if not already done this session.
    """
    df_clean = _load("df_clean")
    df_raw   = _load("df_raw")
    df       = df_clean if df_clean is not None else df_raw

    insights  = _load("last_insights")
    schema    = _load("last_schema")
    summary   = _load("last_summary")

    # Run insights if not cached
    if not insights:
        fi = {}
        automl_meta = _load("automl_result")
        if automl_meta and isinstance(automl_meta, dict):
            fi = automl_meta.get("feature_importance", {})
        schema   = detect_schema(df, feature_importance=fi)
        insights = run_insights(df, schema, top_n=6)
        summary  = summarise_with_gemini(insights,
                                         dataset_name  = session.get("filename", "Dataset"),
                                         dataset_type  = schema["dataset_type"])

    profile   = _load("profile") or {}
    filename  = session.get("filename", "Dataset")
    html      = generate_html_report(
        insights     = insights,
        summary_text = summary or "",
        dataset_name = filename,
        dataset_type = (schema or {}).get("dataset_type", "general"),
        profile      = profile,
    )

    # Persist to DB
    upload_id = session.get("db_upload_id")
    report_id = None
    if upload_id and current_user.is_authenticated:
        report_json = _json.dumps({
            "summary":  summary,
            "insights": [{k: v for k, v in i.items() if k != "chart_data"} for i in insights],
        }, default=str)
        rep = Report(
            upload_id    = upload_id,
            user_id      = current_user.id,
            report_html  = html,
            report_json  = report_json,
            triggered_by = "manual",
        )
        db.session.add(rep)
        try:
            db.session.commit()
            report_id = rep.id
        except Exception:
            db.session.rollback()

    _save("report_html", html)
    return jsonify({"ok": True, "report_id": report_id})


@app.route("/api/reports/<int:report_id>")
@login_required
def api_report_view(report_id: int):
    """Serve the stored HTML for a report."""
    rep = db.session.get(Report, report_id)
    if not rep or rep.user_id != current_user.id:
        return Response("Report not found", status=404, mimetype="text/plain")
    return Response(rep.report_html, mimetype="text/html")


@app.route("/api/reports/current")
@login_required
def api_report_current():
    """Serve the most recently generated report for the current session."""
    html = _load("report_html")
    if not html:
        return Response("No report yet — run insights first.", status=404, mimetype="text/plain")
    return Response(html, mimetype="text/html")


@app.route("/api/reports")
@login_required
def api_reports_list():
    """List all reports for the current user."""
    reps = (
        Report.query
        .filter_by(user_id=current_user.id)
        .order_by(Report.created_at.desc())
        .limit(50)
        .all()
    )
    return jsonify([{
        "id":           r.id,
        "upload_id":    r.upload_id,
        "filename":     r.upload.filename if r.upload else "",
        "triggered_by": r.triggered_by,
        "created_at":   r.created_at.isoformat(),
    } for r in reps])


# ══════════════════════════════════════════════════════════════════════════════
# API: ALERTS
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/api/alerts")
@login_required
def api_alerts_list():
    """List all unresolved alerts for the current user."""
    alerts = (
        Alert.query
        .filter_by(user_id=current_user.id, resolved=False)
        .order_by(Alert.triggered_at.desc())
        .limit(100)
        .all()
    )
    return jsonify([{
        "id":           a.id,
        "upload_id":    a.upload_id,
        "filename":     a.upload.filename if a.upload else "",
        "rule":         a.rule,
        "message":      a.message,
        "severity":     a.severity,
        "colour":       a.severity_colour,
        "metric":       a.metric,
        "pct_change":   a.pct_change,
        "triggered_at": a.triggered_at.isoformat(),
    } for a in alerts])


@app.route("/api/alerts/<int:alert_id>/resolve", methods=["POST"])
@login_required
def api_alert_resolve(alert_id: int):
    a = db.session.get(Alert, alert_id)
    if not a or a.user_id != current_user.id:
        return jsonify({"error": "Not found"}), 404
    a.resolved    = True
    a.resolved_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"ok": True})


@app.route("/api/alerts/check", methods=["POST"])
@login_required
@_require_df
def api_alerts_check():
    """
    Run alert checks on the current session dataset vs its stored baseline.
    """
    df_clean = _load("df_clean")
    df_raw   = _load("df_raw")
    df       = df_clean if df_clean is not None else df_raw

    upload_id = session.get("db_upload_id")
    if not upload_id:
        return jsonify({"ok": True, "alerts": []})

    schema = _load("last_schema") or detect_schema(df)
    engine = AlertEngine()
    alerts = engine.check(upload_id, df, schema)

    # Persist fired alerts
    if alerts and current_user.is_authenticated:
        for a in alerts:
            row = Alert(
                upload_id  = upload_id,
                user_id    = current_user.id,
                rule       = a["rule"],
                message    = a["message"],
                severity   = a["severity"],
                metric     = a.get("metric", ""),
                pct_change = a.get("pct_change"),
            )
            db.session.add(row)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()

    return jsonify({"ok": True, "alerts": alerts, "count": len(alerts)})


# ══════════════════════════════════════════════════════════════════════════════
# API: SCHEDULES
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/api/schedules", methods=["GET"])
@login_required
def api_schedules_list():
    scheds = (
        ReportSchedule.query
        .filter_by(user_id=current_user.id, enabled=True)
        .order_by(ReportSchedule.created_at.desc())
        .all()
    )
    return jsonify([{
        "id":         s.id,
        "upload_id":  s.upload_id,
        "filename":   s.upload.filename if s.upload else "",
        "cron":       s.cron_expression,
        "cron_human": s.cron_human,
        "email":      s.email,
        "enabled":    s.enabled,
        "last_run":   s.last_run_at.isoformat() if s.last_run_at else None,
    } for s in scheds])


@app.route("/api/schedules", methods=["POST"])
@login_required
def api_schedules_create():
    """
    Create a new report schedule.
    Body: { upload_id, cron, email, slack_webhook }
    Common cron presets:
      "0 9 * * 1"   Every Monday 9AM UTC
      "0 9 * * *"   Every day 9AM UTC
      "0 9 1 * *"   Monthly (1st of month)
    """
    body = request.get_json(force=True) or {}
    upload_id     = body.get("upload_id") or session.get("db_upload_id")
    cron          = body.get("cron", "0 9 * * 1")
    email         = (body.get("email") or "").strip()
    slack_webhook = (body.get("slack_webhook") or "").strip()

    if not upload_id:
        return jsonify({"error": "upload_id required"}), 400

    upload = db.session.get(Upload, upload_id)
    if not upload or upload.user_id != current_user.id:
        return jsonify({"error": "Upload not found"}), 404

    sched = ReportSchedule(
        upload_id       = upload_id,
        user_id         = current_user.id,
        cron_expression = cron,
        email           = email,
        slack_webhook   = slack_webhook,
        enabled         = True,
    )
    db.session.add(sched)
    db.session.commit()

    # Register with scheduler
    try:
        from dataforge.scheduler import _register_job
        _register_job(app, sched)
    except Exception:
        pass

    return jsonify({"ok": True, "schedule_id": sched.id, "cron_human": sched.cron_human})


@app.route("/api/schedules/<int:schedule_id>", methods=["DELETE"])
@login_required
def api_schedules_delete(schedule_id: int):
    from dataforge.scheduler import remove_report_job
    sched = db.session.get(ReportSchedule, schedule_id)
    if not sched or sched.user_id != current_user.id:
        return jsonify({"error": "Not found"}), 404
    remove_report_job(schedule_id)
    return jsonify({"ok": True})


# ══════════════════════════════════════════════════════════════════════════════
# API: DATA SOURCES
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/api/sources", methods=["GET"])
@login_required
def api_sources_list():
    sources = DataSource.query.filter_by(user_id=current_user.id, enabled=True).all()
    return jsonify([{
        "id":          s.id,
        "name":        s.name,
        "source_type": s.source_type,
        "last_sync":   s.last_sync.isoformat() if s.last_sync else None,
    } for s in sources])


@app.route("/api/sources/sheets/load", methods=["POST"])
@login_required
def api_source_sheets_load():
    """
    Load a public Google Sheet into a new DataForge upload.
    Body: { sheet_id: "...", gid: "0", name: "My Sheet" }
    """
    body     = request.get_json(force=True) or {}
    sheet_id = (body.get("sheet_id") or "").strip()
    gid      = str(body.get("gid", "0"))
    name     = (body.get("name") or f"sheets_{sheet_id[:8]}").strip()

    if not sheet_id:
        return jsonify({"error": "sheet_id required"}), 400

    try:
        from dataforge.sheets_connector import SheetsConnector
        conn = SheetsConnector()
        df   = conn.load_public(sheet_id, gid)
    except Exception as e:
        return jsonify({"error": f"Could not load Google Sheet: {str(e)}"}), 400

    _clear_store()
    _save("df_raw", df)
    profile = _df_profile(df, filename=name)
    _save("profile", profile)
    session["filename"] = name

    upload_id = _db_log_upload(profile)

    # Tag the source
    if upload_id:
        src = DataSource(
            user_id     = current_user.id,
            name        = name,
            source_type = "sheets",
            config_json = _json.dumps({"sheet_id": sheet_id, "gid": gid}),
            last_sync   = datetime.utcnow(),
        )
        db.session.add(src)
        try:
            db.session.commit()
            upload = db.session.get(Upload, upload_id)
            if upload:
                upload.source_type = "sheets"
                upload.source_id   = src.id
                db.session.commit()
        except Exception:
            db.session.rollback()

    return jsonify({"ok": True, "profile": profile})


@app.route("/api/sources/db/load", methods=["POST"])
@login_required
def api_source_db_load():
    """
    Load data from a database table or SQL query.
    Body: { connection_string: "postgresql://...", table: "orders" | sql: "SELECT ..." }
    ⚠️  Never log or store the connection_string in plaintext — store hashed/encrypted.
    """
    body    = request.get_json(force=True) or {}
    cs      = (body.get("connection_string") or "").strip()
    table   = (body.get("table") or "").strip()
    sql     = (body.get("sql") or "").strip()
    name    = (body.get("name") or table or "database_import").strip()
    limit   = int(body.get("limit", 50000))

    if not cs:
        return jsonify({"error": "connection_string required"}), 400
    if not table and not sql:
        return jsonify({"error": "Provide table name or sql query"}), 400

    try:
        from dataforge.db_connector import DBConnector
        conn = DBConnector(cs)
        if sql:
            df = conn.query(sql)
            df = df.head(limit)
        else:
            df = conn.load_table(table, limit=limit)
        conn.close()
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 400

    _clear_store()
    _save("df_raw", df)
    profile = _df_profile(df, filename=name)
    _save("profile", profile)
    session["filename"] = name
    _db_log_upload(profile)

    return jsonify({"ok": True, "profile": profile})


@app.route("/api/sources/api/load", methods=["POST"])
@login_required
def api_source_api_load():
    """
    Fetch data from a REST API endpoint.
    Body: { url, headers, data_path, name }
    """
    body      = request.get_json(force=True) or {}
    url       = (body.get("url") or "").strip()
    headers   = body.get("headers") or {}
    data_path = body.get("data_path")
    name      = (body.get("name") or "api_import").strip()

    if not url:
        return jsonify({"error": "url required"}), 400

    # Basic SSRF guard
    blocked = ["localhost", "127.", "0.0.0.0", "169.254", "10.", "192.168.", "::1"]
    if any(b in url for b in blocked):
        return jsonify({"error": "Internal URLs are not allowed"}), 400

    try:
        from dataforge.api_connector import APIConnector
        conn = APIConnector(headers=headers)
        df   = conn.fetch(url, data_path=data_path)
        conn.close()
    except Exception as e:
        return jsonify({"error": f"API error: {str(e)}"}), 400

    _clear_store()
    _save("df_raw", df)
    profile = _df_profile(df, filename=name)
    _save("profile", profile)
    session["filename"] = name
    _db_log_upload(profile)

    return jsonify({"ok": True, "profile": profile})