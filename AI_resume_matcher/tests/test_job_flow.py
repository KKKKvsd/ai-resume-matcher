import uuid
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_create_and_get_job():
    unique_id = uuid.uuid4().hex[:8]

    register_payload = {
        "username": f"pytest_job_user_{unique_id}",
        "email": f"pytest_job_user_{unique_id}@example.com",
        "password": "12345678"
    }

    register_response = client.post("/api/v1/users/register", json=register_payload)
    assert register_response.status_code == 200

    login_response = client.post(
        "/api/v1/users/login",
        json={
            "email": register_payload["email"],
            "password": register_payload["password"]
        }
    )
    assert login_response.status_code == 200

    access_token = login_response.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    create_job_payload = {
        "title": "AI开发工程师",
        "company_name": "字节跳动",
        "content": "负责大模型应用开发，熟悉python、FastAPI、RAG、Agent",
        "source": "pytest"
    }

    create_job_response = client.post(
        "/api/v1/jobs",
        json=create_job_payload,
        headers=headers
    )
    assert create_job_response.status_code == 200

    create_job_body = create_job_response.json()
    assert create_job_body["code"] == 0
    assert create_job_body["message"] == "Success"
    assert create_job_body["data"]["title"] == create_job_payload["title"]
    assert create_job_body["data"]["company_name"] == create_job_payload["company_name"]

    job_id = create_job_body["data"]["id"]

    list_job_response = client.get("/api/v1/jobs", headers=headers)
    assert list_job_response.status_code == 200

    list_job_body = list_job_response.json()
    assert list_job_body["code"] == 0
    assert list_job_body["message"] == "Success"
    assert len(list_job_body["data"]) >= 1

    detail_job_response = client.get(f"/api/v1/jobs/{job_id}", headers=headers)
    assert detail_job_response.status_code == 200

    detail_job_body = detail_job_response.json()
    assert detail_job_body["code"] == 0
    assert detail_job_body["message"] == "Success"
    assert detail_job_body["data"]["id"] == job_id
    assert detail_job_body["data"]["title"] == create_job_payload["title"]
    assert detail_job_body["data"]["content"] == create_job_payload["content"]