"""Tests for web interface API endpoints."""
import pytest
from fastapi.testclient import TestClient
from ..web.main import app
from ..core.processor import ImageExtractor

@pytest.fixture
def client():
    return TestClient(app)

def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

def test_get_news_endpoint(client):
    response = client.get("/api/news")
    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]
    
    data = response.json()
    assert "news" in data
    assert isinstance(data["news"], list)
    
    if len(data["news"]) > 0:
        news_item = data["news"][0]
        required_fields = ["title", "description", "link", "timestamp"]
        for field in required_fields:
            assert field in news_item

def test_error_handling(client):
    # Test non-existent endpoint
    response = client.get("/nonexistent")
    assert response.status_code == 404
    
    # Test malformed request
    response = client.post("/api/news")  # POST not allowed
    assert response.status_code in [404, 405]