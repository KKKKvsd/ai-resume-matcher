import uuid
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_register_and_login_user():
    unique_id = uuid.uuid4().hex[:8]

    register_payload = {
        "username": f"pytest_user_{unique_id}",
        "email": f"pytest_user_{unique_id}@example.com",
        "password": "12345678"
    }

    register_response = client.post("/api/v1/users/register", json=register_payload)

    assert register_response.status_code == 200
    register_body = register_response.json()

    assert register_body["code"] == 0
    assert register_body["message"] == "Success"
    assert register_body["data"]["username"] == register_payload["username"]
    assert register_body["data"]["email"] == register_payload["email"]

    login_payload = {
        "email": register_payload["email"],
        "password": register_payload["password"]
    }

    login_response = client.post("/api/v1/users/login", json=login_payload)
    assert login_response.status_code == 200

    login_body = login_response.json()
    assert login_body["code"] == 0
    assert login_body["message"] == "Success"
    assert "access_token" in login_body["data"]
    assert login_body["data"]["token_type"] == "bearer"

    access_token = login_body["data"]["access_token"]

    me_response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert me_response.status_code == 200

    me_body = me_response.json()
    assert me_body["code"] == 0
    assert me_body["message"] == "Success"
    assert me_body["data"]["username"] == register_payload["username"]
    assert me_body["data"]["email"] == register_payload["email"]


