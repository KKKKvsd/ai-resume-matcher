import uuid
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_full_match_flow():
    unique_id = uuid.uuid4().hex[:8]

    # 1. 注册
    register_payload = {
        "username": f"pytest_match_user_{unique_id}",
        "email": f"pytest_match_user_{unique_id}@example.com",
        "password": "12345678"
    }

    register_response = client.post("/api/v1/users/register", json=register_payload)
    assert register_response.status_code == 200

    # 2. 登录
    login_response = client.post(
        "/api/v1/users/login",
        json={
            "email": register_payload["email"],
            "password": register_payload["password"]
        }
    )
    assert login_response.status_code == 200

    login_body = login_response.json()
    assert login_body["code"] == 0
    access_token = login_body["data"]["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # 3. 新建岗位
    create_job_payload = {
        "title": "AI开发工程师",
        "company_name": "测试公司",
        "content": "负责大模型应用开发，熟悉 Python、FastAPI、RAG、Agent、MySQL。",
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
    job_id = create_job_body["data"]["id"]

    # 4. 上传简历
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
    resume_id = upload_body["data"]["id"]

    # 5. 发起分析
    analyze_payload = {
        "resume_id": resume_id,
        "job_id": job_id
    }

    analyze_response = client.post(
        "/api/v1/match/analyze",
        json=analyze_payload,
        headers=headers
    )
    assert analyze_response.status_code == 200

    analyze_body = analyze_response.json()
    assert analyze_body["code"] == 0
    assert analyze_body["message"] == "Success"
    assert analyze_body["data"]["resume_id"] == resume_id
    assert analyze_body["data"]["job_id"] == job_id
    assert analyze_body["data"]["status"] == "success"

    result_id = analyze_body["data"]["id"]

    # 6. 查询分析结果列表
    result_list_response = client.get("/api/v1/match/results", headers=headers)
    assert result_list_response.status_code == 200

    result_list_body = result_list_response.json()
    assert result_list_body["code"] == 0
    assert len(result_list_body["data"]) >= 1

    # 7. 查询分析结果详情
    result_detail_response = client.get(f"/api/v1/match/results/{result_id}", headers=headers)
    assert result_detail_response.status_code == 200

    result_detail_body = result_detail_response.json()
    assert result_detail_body["code"] == 0
    assert result_detail_body["data"]["id"] == result_id
    assert result_detail_body["data"]["resume_id"] == resume_id
    assert result_detail_body["data"]["job_id"] == job_id
    assert "summary" in result_detail_body["data"]
    assert "strengths" in result_detail_body["data"]
    assert "weaknesses" in result_detail_body["data"]
    assert "suggestions" in result_detail_body["data"]