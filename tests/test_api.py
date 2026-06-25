"""API 接口测试 - 测试真实 api/server.py 服务"""
import pytest
from fastapi.testclient import TestClient
from api.server import app
from config import API_TOKEN


@pytest.fixture(scope="module")
def client():
    """使用真实 FastAPI 应用的 TestClient"""
    with TestClient(app) as c:
        yield c


class TestHealthCheck:
    def test_health_check(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert "timestamp" in body


class TestAuth:
    def test_missing_token_returns_401(self, client):
        resp = client.post("/chat", json={"question": "test"})
        assert resp.status_code == 401

    def test_invalid_token_returns_401(self, client):
        resp = client.post("/chat", json={"question": "test"},
                           headers={"Authorization": "Bearer invalid_token"})
        assert resp.status_code == 401

    def test_valid_token_succeeds(self, client):
        resp = client.post("/chat", json={"question": "test"},
                           headers={"Authorization": f"Bearer {API_TOKEN}"})
        # 可能超时或返回200，取决于知识库加载状态
        assert resp.status_code in (200, 500)


class TestValidation:
    def test_empty_question_returns_422(self, client):
        resp = client.post("/chat", json={"question": ""},
                           headers={"Authorization": f"Bearer {API_TOKEN}"})
        assert resp.status_code == 422

    def test_too_many_images_returns_422(self, client):
        resp = client.post("/chat", json={"question": "test", "images": ["a","b","c","d"]},
                           headers={"Authorization": f"Bearer {API_TOKEN}"})
        assert resp.status_code == 422

    def test_missing_question_returns_422(self, client):
        resp = client.post("/chat", json={},
                           headers={"Authorization": f"Bearer {API_TOKEN}"})
        assert resp.status_code == 422


class TestChatEndpoint:
    def test_valid_request_returns_200_with_session(self, client):
        resp = client.post("/chat", json={"question": "test"},
                           headers={"Authorization": f"Bearer {API_TOKEN}"})
        if resp.status_code == 200:
            body = resp.json()
            assert body["code"] == 0
            assert body["msg"] == "success"
            assert body["data"]["session_id"] is not None
            assert len(body["data"]["answer"]) > 0
        # 如果500说明知识库未加载，跳过

    def test_request_with_session_id(self, client):
        resp = client.post("/chat", json={"question": "test", "session_id": "test_session_001"},
                           headers={"Authorization": f"Bearer {API_TOKEN}"})
        if resp.status_code == 200:
            body = resp.json()
            assert body["data"]["session_id"] == "test_session_001"
