from fastapi.testclient import TestClient

from taxi_trip_duration.app import app


def test_metrics_endpoint():
    with TestClient(app) as client:
        response = client.get("/metrics")

    assert response.status_code == 200
    assert "http_requests_total" in response.text
