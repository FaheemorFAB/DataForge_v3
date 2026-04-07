from .shared import (
    build_auth_url,
    build_web_url,
    configure_shared_session,
    get_auth_base_url,
    get_web_base_url,
    google_auth_enabled,
    init_google_oauth,
    init_shared_auth,
    normalize_relative_url,
    register_auth_template_globals,
)

__all__ = [
    "build_auth_url",
    "build_web_url",
    "configure_shared_session",
    "get_auth_base_url",
    "get_web_base_url",
    "google_auth_enabled",
    "init_google_oauth",
    "init_shared_auth",
    "normalize_relative_url",
    "register_auth_template_globals",
]
