import pytest
from fastapi.testclient import TestClient
from backend.api_service.main import app
from backend.chainsentry_common.db import init_db
from backend.ingestion_svc.connectors.blockchain import LiveBlockchainConnector

@pytest.fixture(scope="module", autouse=True)
def setup_database():
    init_db()

@pytest.fixture
def auth_headers(client):
    resp = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "chainsentry2026!"}
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_get_wallets_endpoint(client, auth_headers):
    resp = client.get("/api/graph/wallets?limit=10", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)
    assert data["limit"] == 10

def test_get_transactions_endpoint(client, auth_headers):
    resp = client.get("/api/graph/transactions?limit=10", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)
    assert data["limit"] == 10

def test_blockchain_connector_script_type_detection():
    connector = LiveBlockchainConnector()
    assert connector._determine_script_type("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa") == "P2PKH"
    assert connector._determine_script_type("3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy") == "P2SH"
    assert connector._determine_script_type("bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq") == "P2WPKH"
    assert connector._determine_script_type("bc1p5d7rx65gnslx2e2vsbqqwhcc0t0cvwwgtac0alvv") == "P2TR"
