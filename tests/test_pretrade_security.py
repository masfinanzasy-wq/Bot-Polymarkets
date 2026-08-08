import pytest
from fastapi.testclient import TestClient
from app.api.server import app

client = TestClient(app)

def test_verify_access_key_valid():
    response = client.post("/api/v1/auth/verify-key", json={"key": "polymarket2026"})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "token" in data

def test_verify_access_key_invalid():
    response = client.post("/api/v1/auth/verify-key", json={"key": "wrong_key_123"})
    assert response.status_code == 401

def test_recover_access_key():
    response = client.post("/api/v1/auth/recover-key", json={"email": "trader@example.com"})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "trader@example.com" in data["message"]

def test_pretrade_security_check_paper():
    payload = {
        "position_size_usd": 50.0,
        "execution_mode": "PAPER_TRADING",
        "min_ev_pct": 5.0
    }
    response = client.post("/api/v1/auth/pretrade-security-check", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["passed"] is True

def test_pretrade_security_check_real_without_wallet():
    payload = {
        "position_size_usd": 50.0,
        "execution_mode": "REAL_MAINNET",
        "min_ev_pct": 5.0
    }
    response = client.post("/api/v1/auth/pretrade-security-check", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["passed"] is False
    assert len(data["errors"]) > 0

def test_wallet_balance_live_query():
    response = client.get("/api/v1/wallet/balance/0x742d35Cc6634C0532925a3b844Bc454e4438f44e")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "usdc_balance" in data
    assert "matic_balance" in data

