from __future__ import annotations

import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


class TestReturnsApiViewSet:
    def test_lookup_with_valid_credentials_returns_articles_url(self) -> None:
        client = APIClient()

        response = client.post(
            "/api/returns/lookup/",
            {
                "order_number": "RMA-1001",
                "identifier": "alex@example.com",
            },
            format="json",
        )

        assert response.status_code == 200
        assert response.data["order_number"] == "RMA-1001"
        assert response.data["articles_url"].endswith("/api/returns/RMA-1001/articles/")

    def test_lookup_with_invalid_credentials_returns_400(self) -> None:
        client = APIClient()

        response = client.post(
            "/api/returns/lookup/",
            {
                "order_number": "RMA-1001",
                "identifier": "wrong@example.com",
            },
            format="json",
        )

        assert response.status_code == 400
        assert "not found" in response.data["detail"].lower()

    def test_lookup_is_throttled_after_repeated_failures(self) -> None:
        client = APIClient()

        for _ in range(4):
            response = client.post(
                "/api/returns/lookup/",
                {
                    "order_number": "RMA-1001",
                    "identifier": "wrong@example.com",
                },
                format="json",
            )
            assert response.status_code == 400

        response = client.post(
            "/api/returns/lookup/",
            {
                "order_number": "RMA-1001",
                "identifier": "wrong@example.com",
            },
            format="json",
        )

        assert response.status_code == 429
        assert response.headers["Retry-After"] == "60"
        assert "too many failed lookup attempts" in response.data["detail"].lower()

    def test_successful_lookup_resets_failed_attempt_counter(self) -> None:
        client = APIClient()

        for _ in range(4):
            response = client.post(
                "/api/returns/lookup/",
                {
                    "order_number": "RMA-1001",
                    "identifier": "wrong@example.com",
                },
                format="json",
            )
            assert response.status_code == 400

        success_response = client.post(
            "/api/returns/lookup/",
            {
                "order_number": "RMA-1001",
                "identifier": "alex@example.com",
            },
            format="json",
        )
        assert success_response.status_code == 200

        failure_response = client.post(
            "/api/returns/lookup/",
            {
                "order_number": "RMA-1001",
                "identifier": "wrong@example.com",
            },
            format="json",
        )

        assert failure_response.status_code == 400

    def test_articles_requires_prior_lookup(self) -> None:
        client = APIClient()

        response = client.get("/api/returns/RMA-1001/articles/")

        assert response.status_code == 403

    def test_articles_after_lookup_returns_order_and_eligibility(self) -> None:
        client = APIClient()
        lookup_response = client.post(
            "/api/returns/lookup/",
            {
                "order_number": "RMA-1001",
                "identifier": "alex@example.com",
            },
            format="json",
        )
        assert lookup_response.status_code == 200

        response = client.get("/api/returns/RMA-1001/articles/")

        assert response.status_code == 200
        assert response.data["order"]["order_number"] == "RMA-1001"
        assert len(response.data["results"]) == 2

        first = response.data["results"][0]
        second = response.data["results"][1]
        assert first["article"]["sku"] == "TSHIRT-BLK-M"
        assert first["selectable"] is True
        assert first["quantity_options"] == [1]

        assert second["article"]["sku"] == "EBOOK-RETURNS"
        assert second["returnable"] is False
        assert second["selectable"] is False

    def test_articles_rejects_different_order_than_authenticated_session(self) -> None:
        client = APIClient()

        lookup_response = client.post(
            "/api/returns/lookup/",
            {
                "order_number": "RMA-1001",
                "identifier": "alex@example.com",
            },
            format="json",
        )
        assert lookup_response.status_code == 200

        response = client.get("/api/returns/RMA-1002/articles/")

        assert response.status_code == 403
        assert "lookup is required" in response.data["detail"].lower()
