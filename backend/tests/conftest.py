import os
import pytest
from dataforge.api.config import get_settings

# Force fail-closed authentication and safe defaults during test runs
os.environ["ENABLE_DEV_AUTH"] = "false"
os.environ["ALLOW_LOCAL_DATABASE"] = "true"

settings = get_settings()
settings.ENABLE_DEV_AUTH = False
get_settings.cache_clear()


@pytest.fixture(autouse=True)
def enforce_fail_closed_test_auth(monkeypatch):
    """Ensure every test runs with fail-closed authentication unless explicitly overridden."""
    monkeypatch.setenv("ENABLE_DEV_AUTH", "false")
    s = get_settings()
    monkeypatch.setattr(s, "ENABLE_DEV_AUTH", False)
