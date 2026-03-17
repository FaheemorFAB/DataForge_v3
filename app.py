"""
Entry point shim.
The main web service now lives in services/web/app.py.
"""

from services.web.app import app, socketio


if __name__ == "__main__":
    socketio.run(
        app,
        debug=True,
        host="0.0.0.0",
        port=5000,
        use_reloader=False,
        allow_unsafe_werkzeug=True,
    )
