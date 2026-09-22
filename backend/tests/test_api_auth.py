import pytest
from fastapi.testclient import TestClient
from backend.api_service.main import app
from backend.chainsentry_common.db import init_db
from backend.chainsentry_common.security import hash_password, verify_password, create_access_token

@pytest.fixture(scope="module", autouse=True)
def setup_database():
    init_db()

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_password_hashing():
    pwd = "SecretPassWord123!"
    hashed = hash_password(pwd)
    assert hashed != pwd
    assert verify_password(pwd, hashed) is True
    assert verify_password("WrongPassword", hashed) is False

def test_healthcheck(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["service"] == "ChainSentry"

def test_login_flow(client):
    # Login with default admin
    resp = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "chainsentry2026!"}
    )
    assert resp.status_code == 200
    tokens = resp.json()
    assert "access_token" in tokens
    assert tokens["user"]["username"] == "admin"
    assert tokens["user"]["role"] == "admin"

    # Test me endpoint with token
    access_token = tokens["access_token"]
    me_resp = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["username"] == "admin"
