"""Legacy chatbot.thelearningproject.in → Rovr landing redirect."""

from fastapi.testclient import TestClient

from backend.main import app


def test_legacy_host_root_redirects_to_frontend():
    client = TestClient(app)
    response = client.get(
        "/",
        headers={"Host": "chatbot.thelearningproject.in"},
        follow_redirects=False,
    )
    assert response.status_code == 301
    assert response.headers["location"] == "https://thelearningproject.in/tools/rovr/"


def test_legacy_host_deep_path_redirects_to_landing():
    client = TestClient(app)
    response = client.get(
        "/login",
        headers={"Host": "chatbot.thelearningproject.in"},
        follow_redirects=False,
    )
    assert response.status_code == 301
    assert response.headers["location"].endswith("/tools/rovr/")


def test_legacy_host_api_health_not_redirected():
    client = TestClient(app)
    response = client.get(
        "/api/health",
        headers={"Host": "chatbot.thelearningproject.in"},
        follow_redirects=False,
    )
    assert response.status_code != 301


def test_main_site_host_not_redirected():
    client = TestClient(app)
    response = client.get(
        "/",
        headers={"Host": "experienceleaguechatbotaws-production.up.railway.app"},
        follow_redirects=False,
    )
    assert response.status_code != 301
