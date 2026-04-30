"""DataForge monolith entry point."""

import os

from dataforge.web.app import app, socketio


if __name__ == "__main__":
    socketio.run(
        app,
        debug=True,
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        use_reloader=False,
        allow_unsafe_werkzeug=True,
    )
