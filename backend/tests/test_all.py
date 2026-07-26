"""
Unified test runner for DataForge backend API and AutoML test suites.
Run:
  python backend/tests/test_all.py
"""
import sys
from pathlib import Path

_backend_dir = Path(__file__).resolve().parents[1]
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

print("\n============================================================")
print("          DATAFORGE V3 UNIFIED TEST SUITE RUNNER            ")
print("============================================================\n")

# Run workspace API tests
import tests.test_workspace_api as tw
tw.test_workspace_endpoints()

# Run dashboard API tests
import tests.test_dashboard_api as td
td.test_dashboard_endpoints()

# Run AutoML integration unit tests
import tests.run_integration_test

print("\n============================================================")
print("     ALL DATAFORGE V3 TEST SUITES PASSED SUCCESSFULLY      ")
print("============================================================\n")
