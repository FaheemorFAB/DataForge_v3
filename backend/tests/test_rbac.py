"""
backend/tests/test_rbac.py
─────────────────────────
Security Suite: Role-Based Access Control (RBAC) and Governance.
Tests Admin, Data Engineer, Analyst, and Viewer privilege separation,
role promotion, demotion, and instant revocation upon membership removal.
"""

import pytest
from fastapi.testclient import TestClient

from dataforge.api.app import create_app
from dataforge.api.auth.jwt import create_access_token


@pytest.fixture(scope="module")
def client():
    app = create_app()
    return TestClient(app)


@pytest.fixture
def admin_user():
    return {"id": 101, "email": "admin@enterprise.com", "headers": {"Authorization": f"Bearer {create_access_token(101)}"}}


@pytest.fixture
def viewer_user():
    return {"id": 202, "email": "viewer@enterprise.com", "headers": {"Authorization": f"Bearer {create_access_token(202)}"}}


def test_rbac_organization_governance_lifecycle(client, admin_user, viewer_user):
    """
    1. Admin creates an organization.
    2. Admin invites viewer.
    3. Viewer attempts admin operations (invite, change role, delete member, view audit) and receives 403.
    4. Admin promotes viewer to Admin.
    5. Former viewer can now perform admin operations.
    6. Admin removes user from organization; subsequent calls receive 403.
    """
    # 1. Admin creates team
    res_create = client.post("/api/teams", json={"name": "Acme Analytics", "plan": "Enterprise"}, headers=admin_user["headers"])
    assert res_create.status_code == 200
    org_id = res_create.json()["organization"]["id"]

    # 2. Admin invites viewer
    res_invite = client.post(
        f"/api/teams/{org_id}/invite",
        json={"email": viewer_user["email"], "name": "Jane Viewer", "role": "Viewer"},
        headers=admin_user["headers"],
    )
    assert res_invite.status_code == 200
    viewer_member_id = res_invite.json()["member"]["user_id"]

    # In our mock setup, map viewer_user["id"] (202) into this membership for request testing
    from dataforge.teams.manager import TeamManager, _LOCK
    with _LOCK:
        data = TeamManager._read_data()
        for m in data.get("memberships", []):
            if m.get("org_id") == org_id and m.get("user_email") == viewer_user["email"]:
                m["user_id"] = viewer_user["id"]
        TeamManager._write_data(data)

    # 3. Viewer attempts unauthorized operations -> 403 Forbidden
    # 3a. Viewer tries to invite a user
    res_v_invite = client.post(
        f"/api/teams/{org_id}/invite",
        json={"email": "attacker@evil.com", "role": "Admin"},
        headers=viewer_user["headers"],
    )
    assert res_v_invite.status_code == 403
    assert "operation requires 'Admin' role" in res_v_invite.json()["detail"]

    # 3b. Viewer tries to update admin's role
    res_v_role = client.patch(
        f"/api/teams/{org_id}/members/{admin_user['id']}/role",
        json={"new_role": "Viewer"},
        headers=viewer_user["headers"],
    )
    assert res_v_role.status_code == 403

    # 3c. Viewer tries to remove admin
    res_v_remove = client.delete(
        f"/api/teams/{org_id}/members/{admin_user['id']}",
        headers=viewer_user["headers"],
    )
    assert res_v_remove.status_code == 403

    # 3d. Viewer tries to read audit logs (requires Data Engineer or Admin)
    res_v_audit = client.get(
        f"/api/teams/{org_id}/audit-logs",
        headers=viewer_user["headers"],
    )
    assert res_v_audit.status_code == 403

    # 4. Admin promotes Viewer to Admin
    res_promote = client.patch(
        f"/api/teams/{org_id}/members/{viewer_user['id']}/role",
        json={"new_role": "Admin"},
        headers=admin_user["headers"],
    )
    assert res_promote.status_code == 200
    assert res_promote.json()["member"]["role"] == "Admin"

    # 5. Promoted user can now invite a new colleague
    res_promoted_invite = client.post(
        f"/api/teams/{org_id}/invite",
        json={"email": "colleague@enterprise.com", "name": "Bob Analyst", "role": "Analyst"},
        headers=viewer_user["headers"],
    )
    assert res_promoted_invite.status_code == 200

    # 6. Admin removes user from team -> Immediate revocation
    res_del = client.delete(
        f"/api/teams/{org_id}/members/{viewer_user['id']}",
        headers=admin_user["headers"],
    )
    assert res_del.status_code == 200

    # User is no longer a member -> 403 Forbidden
    res_revoked = client.get(
        f"/api/teams/{org_id}/members",
        headers=viewer_user["headers"],
    )
    assert res_revoked.status_code == 403
    assert "not a member" in res_revoked.json()["detail"]
