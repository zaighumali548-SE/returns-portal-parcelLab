"""Tests for the Django views."""

import pytest
from django.test import Client

pytestmark = pytest.mark.django_db


@pytest.fixture()
def client() -> Client:
    return Client()


class TestLookupView:
    def test_get_returns_200(self, client: Client) -> None:
        response = client.get("/returns/")
        assert response.status_code == 200

    def test_get_contains_form(self, client: Client) -> None:
        response = client.get("/returns/")
        assert b"order_number" in response.content

    def test_valid_email_redirects(self, client: Client) -> None:
        response = client.post(
            "/returns/",
            {
                "order_number": "RMA-1001",
                "identifier": "alex@example.com",
            },
        )
        assert response.status_code == 302
        assert "/articles/" in response.headers["Location"]

    def test_valid_zip_redirects(self, client: Client) -> None:
        response = client.post(
            "/returns/",
            {
                "order_number": "RMA-1001",
                "identifier": "10115",
            },
        )
        assert response.status_code == 302

    def test_invalid_credentials_shows_error(self, client: Client) -> None:
        response = client.post(
            "/returns/",
            {
                "order_number": "RMA-1001",
                "identifier": "wrong@example.com",
            },
        )
        assert response.status_code == 200
        assert b"not found" in response.content.lower()

    def test_empty_fields_returns_form(self, client: Client) -> None:
        response = client.post(
            "/returns/",
            {
                "order_number": "",
                "identifier": "",
            },
        )
        assert response.status_code == 200


class TestArticlesView:
    def test_unauthenticated_redirects(self, client: Client) -> None:
        response = client.get("/returns/RMA-1001/articles/")
        assert response.status_code == 302

    def test_authenticated_shows_articles(self, client: Client) -> None:
        # Log in first
        client.post(
            "/returns/",
            {
                "order_number": "RMA-1001",
                "identifier": "alex@example.com",
            },
        )
        response = client.get("/returns/RMA-1001/articles/")
        assert response.status_code == 200
        assert b"TSHIRT-BLK-M" in response.content

    def test_returnable_only_filter_uses_htmx_partial(self, client: Client) -> None:
        client.post(
            "/returns/",
            {
                "order_number": "RMA-1001",
                "identifier": "alex@example.com",
            },
        )

        response = client.get(
            "/returns/RMA-1001/articles/",
            {"show_returnable_only": "1"},
            HTTP_HX_REQUEST="true",
        )

        assert response.status_code == 200
        assert b"TSHIRT-BLK-M" in response.content
        assert b"EBOOK-RETURNS" not in response.content
        assert b"Order RMA-1001" not in response.content

    def test_continue_without_selection_shows_error(self, client: Client) -> None:
        client.post(
            "/returns/",
            {
                "order_number": "RMA-1001",
                "identifier": "alex@example.com",
            },
        )

        response = client.post("/returns/RMA-1001/confirm/")

        assert response.status_code == 400
        assert b"Select at least one returnable item" in response.content

    def test_selected_articles_redirect_to_confirmation(self, client: Client) -> None:
        client.post(
            "/returns/",
            {
                "order_number": "RMA-1001",
                "identifier": "alex@example.com",
            },
        )

        response = client.post(
            "/returns/RMA-1001/confirm/",
            {
                "selected_skus": ["TSHIRT-BLK-M"],
                "qty__TSHIRT-BLK-M": "1",
            },
            follow=True,
        )

        assert response.status_code == 200
        assert b"Confirm your return" in response.content
        assert b"Vibe Tee - Bold &amp; Basic with a Twist" in response.content
        assert b"Submit return" in response.content

    def test_submit_return_reaches_success_page(self, client: Client) -> None:
        client.post(
            "/returns/",
            {
                "order_number": "RMA-1001",
                "identifier": "alex@example.com",
            },
        )
        client.post(
            "/returns/RMA-1001/confirm/",
            {
                "selected_skus": ["TSHIRT-BLK-M"],
                "qty__TSHIRT-BLK-M": "1",
            },
        )

        response = client.post("/returns/RMA-1001/submit/", follow=True)

        assert response.status_code == 200
        assert b"Return submitted" in response.content
        assert b"RET-1001-" in response.content
