"""Tests for health check API."""


def test_health_check(client):
    """Test health endpoint returns 200 and valid system details."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "AI-API-Doc-Agent"
    assert "uptime_seconds" in data
    assert "llm_provider" in data
    assert "python_version" in data
