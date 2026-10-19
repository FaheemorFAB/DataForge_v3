"""
backend/tests/test_sharing_and_paddle.py
────────────────────────────────────────
Verifies Google Sheets-style dataset sharing, email collaborator invitations,
granular user-level RBAC (Viewer, Analyst, Editor, Admin, Owner),
general link access modes (Restricted vs Anyone with link),
and Paddle SaaS billing checkout & webhook processing.
"""

import json
import time
import pytest
from fastapi.testclient import TestClient

from dataforge.api.app import create_app
from dataforge.api.deps import get_current_user
from dataforge.api.services.auth import User
from dataforge.api.services.entitlements import EntitlementService
from dataforge.api.services.payments import PaddlePaymentProvider, get_payment_provider
from dataforge.api.services.sharing import DatasetSharingService, ROLE_RANKS
from dataforge.api.storage.manager import save


@pytest.fixture
def test_setup():
    app = create_app()

    owner_user = User(id=101, email="owner@dataforge.test", name="Dataset Owner")
    collab_user = User(id=102, email="collab@dataforge.test", name="Collaborator")
    stranger_user = User(id=103, email="stranger@dataforge.test", name="Stranger")

    # Dependency override helper
    current_active_user = {"user": owner_user}
    app.dependency_overrides[get_current_user] = lambda: current_active_user["user"]

    client = TestClient(app)

    # Seed test dataset 8888
    import pandas as pd
    df = pd.DataFrame({"col_a": [1, 2, 3], "col_b": ["x", "y", "z"]})
    save("8888", "df_raw", df)
    save("8888", "df_clean", df)
    save("8888", "meta", {"user_id": 101, "filename": "financial_records.csv"})

    # Ensure clean shares manifest
    sh_path = DatasetSharingService._shares_path("8888")
    if sh_path.exists():
        try:
            sh_path.unlink()
        except Exception:
            pass
    DatasetSharingService.get_shares("8888", owner_id=101, owner_email="owner@dataforge.test")

    from dataforge.api.repositories.upload import upload_repo
    orig_get_by_id = upload_repo.get_by_id
    upload_repo.get_by_id = lambda uid: {"id": uid, "user_id": 101, "filename": "financial_records.csv"} if str(uid) == "8888" else None

    from dataforge.api.services.entitlements import EntitlementService
    orig_get_subscription = EntitlementService.get_subscription
    EntitlementService.get_subscription = lambda uid, email=None: {
        "plan": "team",
        "has_team_collaboration": True,
        "status": "active",
        "max_rows": 5_000_000,
    }

    try:
        yield {
            "client": client,
            "owner": owner_user,
            "collab": collab_user,
            "stranger": stranger_user,
            "active_user_ref": current_active_user,
        }
    finally:
        app.dependency_overrides.clear()
        upload_repo.get_by_id = orig_get_by_id
        EntitlementService.get_subscription = orig_get_subscription


def test_dataset_sharing_lifecycle(test_setup):
    client = test_setup["client"]
    owner = test_setup["owner"]
    collab = test_setup["collab"]
    stranger = test_setup["stranger"]
    active_ref = test_setup["active_user_ref"]

    # 1. Owner gets initial share settings
    active_ref["user"] = owner
    res = client.get("/api/workspace/8888/share")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["current_user_role"] == "Owner"
    assert data["shares"]["general_access"] == "restricted"

    # 2. Stranger attempts to access restricted dataset -> 403 Forbidden
    active_ref["user"] = stranger
    res = client.get("/api/workspace/state?upload_id=8888")
    assert res.status_code == 403
    assert "Access denied" in res.json()["detail"]

    # 3. Owner invites collaborator with Viewer role
    active_ref["user"] = owner
    res = client.post(
        "/api/workspace/8888/share/invite",
        json={"email": "collab@dataforge.test", "role": "Viewer"},
    )
    assert res.status_code == 200
    assert len(res.json()["shares"]["collaborators"]) == 1

    # 4. Collaborator can now view state as Viewer
    active_ref["user"] = collab
    res = client.get("/api/workspace/state?upload_id=8888")
    assert res.status_code == 200

    # 5. Collaborator as Viewer attempts to run cleaning (requires Analyst) -> 403
    res = client.post("/api/clean", json={"upload_id": "8888"})
    assert res.status_code == 403
    assert "requires 'Analyst' permission" in res.json()["detail"]

    # 6. Owner upgrades Collaborator to Analyst
    active_ref["user"] = owner
    res = client.post(
        "/api/workspace/8888/share/invite",
        json={"email": "collab@dataforge.test", "role": "Analyst"},
    )
    assert res.status_code == 200

    # 7. Collaborator as Analyst can now execute cleaning
    active_ref["user"] = collab
    res = client.post("/api/clean", json={"upload_id": "8888"})
    assert res.status_code == 200

    # 8. Test Link Sharing: Update to 'anyone_with_link' as Viewer
    active_ref["user"] = owner
    res = client.post(
        "/api/workspace/8888/share/general",
        json={"general_access": "anyone_with_link", "link_role": "Viewer"},
    )
    assert res.status_code == 200
    assert res.json()["shares"]["general_access"] == "anyone_with_link"

    # 9. Stranger can now view dataset via general link access
    active_ref["user"] = stranger
    res = client.get("/api/workspace/state?upload_id=8888")
    assert res.status_code == 200

    # 10. But Stranger cannot clean (only has Viewer link role) -> 403
    res = client.post("/api/clean", json={"upload_id": "8888"})
    assert res.status_code == 403

    # 11. Remove collaborator
    active_ref["user"] = owner
    res = client.request(
        "DELETE",
        "/api/workspace/8888/share/collaborators",
        json={"email": "collab@dataforge.test"},
    )
    assert res.status_code == 200
    assert len(res.json()["shares"]["collaborators"]) == 0


def test_paddle_payment_provider_integration():
    provider = PaddlePaymentProvider(
        vendor_id="test_vendor_99",
        webhook_secret="test_paddle_secret_12345",
    )

    # 1. Create checkout session
    checkout = provider.create_checkout_session(
        user_id=42,
        user_email="buyer@dataforge.test",
        plan_key="pro",
        return_url="http://localhost:3000/billing",
    )
    assert checkout["provider"] == "paddle"
    assert "https://buy.paddle.com/checkout/pro" in checkout["checkout_url"]
    assert "test_vendor_99" in checkout["checkout_url"]
    assert checkout["plan"] == "pro"

    # 2. Webhook verification and upgrade
    payload = {
        "event_id": f"pdl_evt_{int(time.time() * 1000)}",
        "event_type": "subscription.activated",
        "data": {
            "custom_data": {"user_id": 42, "plan": "pro"},
            "customer": {"email": "buyer@dataforge.test"},
        },
    }
    payload_bytes = json.dumps(payload).encode("utf-8")

    import hashlib
    import hmac
    sig = hmac.new("test_paddle_secret_12345".encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()

    verified = provider.verify_webhook_signature(payload_bytes, sig)
    assert verified["event_id"] == payload["event_id"]

    # 3. Handle activation event
    res = provider.handle_event(verified)
    assert res["ok"] is True
    assert EntitlementService.get_user_plan(42) == "pro"

    # 4. Handle cancellation event
    cancel_payload = {
        "event_id": f"pdl_evt_cancel_{int(time.time() * 1000)}",
        "event_type": "subscription.canceled",
        "data": {
            "custom_data": {"user_id": 42},
        },
    }
    provider.handle_event(cancel_payload)
    assert EntitlementService.get_user_plan(42) == "free"
