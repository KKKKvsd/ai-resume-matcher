import uuid
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_upload_and_get_resume():
    unique_id = uuid.uuid4().hex[:8]

    register_payload = {
        "username": f"pytest_resume_user_{unique_id}",
        "email": f"pytest_resume_user_{unique_id}@example.com",
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

    pdf_path = Path("tests/files/test_resume.pdf")
    assert pdf_path.exists(), "测试 PDF 文件不存在，请确认 tests/files/test_resume.pdf 已创建"

    with open(pdf_path, "rb") as f:
        upload_response = client.post(
            "/api/v1/resumes/upload",
            headers=headers,
            files={"file": ("test_resume.pdf", f, "application/pdf")}
        )

    assert upload_response.status_code == 200

    upload_body = upload_response.json()
    assert upload_body["code"] == 0
    assert upload_body["message"] == "Success"
    assert upload_body["data"]["file_name"] == "test_resume.pdf"
    assert upload_body["data"]["file_type"] == "pdf"

    resume_id = upload_body["data"]["id"]

    list_response = client.get("/api/v1/resumes", headers=headers)
    assert list_response.status_code == 200

    list_body = list_response.json()
    assert list_body["code"] == 0
    assert list_body["message"] == "Success"
    assert len(list_body["data"]) >= 1

    detail_response = client.get(f"/api/v1/resumes/{resume_id}", headers=headers)
    assert detail_response.status_code == 200

    detail_body = detail_response.json()
    assert detail_body["code"] == 0
    assert detail_body["message"] == "Success"
    assert detail_body["data"]["id"] == resume_id
    assert detail_body["data"]["file_name"] == "test_resume.pdf"
    assert detail_body["data"]["file_type"] == "pdf"