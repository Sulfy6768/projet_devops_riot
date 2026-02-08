"""
Tests for health check endpoint.
"""


class TestHealthCheck:
    """Tests for /health endpoint."""

    def test_health_check_returns_200(self, client):
        """Health check should return 200 OK."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_check_response_format(self, client):
        """Health check should return correct format."""
        response = client.get("/health")
        data = response.json()

        assert "status" in data
        assert "service" in data
        assert data["status"] == "healthy"
        assert data["service"] == "riot-api"


class TestMetricsEndpoint:
    """Tests for /metrics endpoint."""

    def test_metrics_endpoint_exists(self, client):
        """Metrics endpoint should be accessible."""
        response = client.get("/metrics")
        assert response.status_code == 200

    def test_metrics_contains_prometheus_format(self, client):
        """Metrics should be in Prometheus format."""
        response = client.get("/metrics")
        content = response.text

        # Should contain HELP and TYPE comments (Prometheus format)
        assert "# HELP" in content or "http_requests" in content.lower()
