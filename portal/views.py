from __future__ import annotations

import secrets
from typing import Any

from django.http import HttpRequest, HttpResponse, QueryDict
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View

from portal.forms import LookupForm
from portal.services.eligibility import evaluate_eligibility
from portal.services.order_store import find_order, get_order
from portal.types import Article, ArticleEligibility, Order

_HX_REQUEST_HEADER = "HX-Request"
_PENDING_RETURN_SESSION_KEY = "pending_return"
_COMPLETED_RETURN_SESSION_KEY = "completed_return"


def _is_hx_request(request: HttpRequest) -> bool:
    return request.headers.get(_HX_REQUEST_HEADER, "").lower() == "true"


def _show_returnable_only(data: QueryDict) -> bool:
    return data.get("show_returnable_only") == "1"


def _selected_skus(data: QueryDict) -> set[str]:
    return set(data.getlist("selected_skus"))


def _selected_quantities(data: QueryDict) -> dict[str, int]:
    quantities: dict[str, int] = {}
    for key in data:
        if not key.startswith("qty__"):
            continue

        value = data.get(key)
        if value is None:
            continue

        sku = key.removeprefix("qty__")
        try:
            parsed_quantity = int(value)
        except ValueError:
            continue

        if parsed_quantity > 0:
            quantities[sku] = parsed_quantity

    return quantities


def _article_row(
    result: ArticleEligibility,
    *,
    selected_skus: set[str],
    selected_quantities: dict[str, int],
) -> dict[str, Any]:
    remaining_qty = max(
        result.article.quantity - result.article.quantity_returned,
        0,
    )
    quantity_options = list(range(1, remaining_qty + 1))
    selectable = result.returnable and remaining_qty > 0
    selected_quantity = selected_quantities.get(result.article.sku, 1)
    if quantity_options and selected_quantity not in quantity_options:
        selected_quantity = quantity_options[0]

    return {
        "result": result,
        "remaining_qty": remaining_qty,
        "quantity_options": quantity_options,
        "selectable": selectable,
        "selected": selectable and result.article.sku in selected_skus,
        "selected_quantity": selected_quantity,
    }


def _build_article_rows(
    order: Order,
    *,
    selected_skus: set[str] | None = None,
    selected_quantities: dict[str, int] | None = None,
    show_returnable_only: bool = False,
) -> list[dict[str, Any]]:
    selected_skus = selected_skus or set()
    selected_quantities = selected_quantities or {}

    article_rows = [
        _article_row(
            result,
            selected_skus=selected_skus,
            selected_quantities=selected_quantities,
        )
        for result in evaluate_eligibility(order)
    ]

    if show_returnable_only:
        return [row for row in article_rows if bool(row["selectable"])]

    return article_rows


def _get_authenticated_order(
    request: HttpRequest,
    order_number: str,
) -> Order | None:
    if request.session.get("order_number") != order_number:
        return None
    return get_order(order_number)


def _render_articles(
    request: HttpRequest,
    *,
    order: Order,
    error_message: str = "",
    selected_skus: set[str] | None = None,
    selected_quantities: dict[str, int] | None = None,
    show_returnable_only: bool = False,
    status_code: int = 200,
) -> HttpResponse:
    context = {
        "order": order,
        "article_rows": _build_article_rows(
            order,
            selected_skus=selected_skus,
            selected_quantities=selected_quantities,
            show_returnable_only=show_returnable_only,
        ),
        "error_message": error_message,
        "show_returnable_only": show_returnable_only,
    }

    template_name = (
        "returns/_article_selection_panel.html"
        if _is_hx_request(request)
        else "returns/articles.html"
    )
    return render(request, template_name, context, status=status_code)


def _build_selected_return_items(
    order: Order,
    *,
    selected_skus: set[str],
    selected_quantities: dict[str, int],
) -> list[dict[str, Any]]:
    rows_by_sku = {
        row["result"].article.sku: row
        for row in _build_article_rows(
            order,
            selected_skus=selected_skus,
            selected_quantities=selected_quantities,
        )
    }

    selected_items: list[dict[str, Any]] = []
    for sku in selected_skus:
        row = rows_by_sku.get(sku)
        if row is None or not bool(row["selectable"]):
            continue

        article = row["result"].article
        quantity_options = row["quantity_options"]
        quantity = selected_quantities.get(article.sku, 1)
        if quantity not in quantity_options:
            continue

        selected_items.append(_serialize_selected_item(article, quantity))

    return sorted(selected_items, key=lambda item: str(item["sku"]))


def _serialize_selected_item(article: Article, quantity: int) -> dict[str, Any]:
    line_total = round(article.price * quantity, 2)
    return {
        "sku": article.sku,
        "name": article.name,
        "quantity": quantity,
        "unit_price": article.price,
        "line_total": line_total,
    }


def _pending_return_context(
    order: Order,
    selected_items: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "order_number": order.order_number,
        "items": selected_items,
        "item_count": sum(int(item["quantity"]) for item in selected_items),
        "total_amount": round(
            sum(float(item["line_total"]) for item in selected_items),
            2,
        ),
    }


def _get_session_return(
    request: HttpRequest,
    *,
    key: str,
    order_number: str,
) -> dict[str, Any] | None:
    session_value = request.session.get(key)
    if not isinstance(session_value, dict):
        return None

    if session_value.get("order_number") != order_number:
        return None

    return session_value


class LookupView(View):
    """Order lookup page – validates order number + email / zip."""

    def get(self, request: HttpRequest) -> HttpResponse:
        return render(request, "returns/lookup.html", {"form": LookupForm()})

    def post(self, request: HttpRequest) -> HttpResponse:
        form = LookupForm(request.POST)
        if form.is_valid():
            order = find_order(
                form.cleaned_data["order_number"],
                form.cleaned_data["identifier"],
            )
            if order is None:
                form.add_error(None, "Order not found or credentials do not match.")
            else:
                request.session["order_number"] = order.order_number
                request.session.pop(_PENDING_RETURN_SESSION_KEY, None)
                request.session.pop(_COMPLETED_RETURN_SESSION_KEY, None)
                return redirect("articles", order_number=order.order_number)

        return render(request, "returns/lookup.html", {"form": form})


class ArticlesView(View):
    """Articles page – shows items in the order with eligibility info."""

    def get(self, request: HttpRequest, order_number: str) -> HttpResponse:
        order = _get_authenticated_order(request, order_number)
        if order is None:
            return redirect("lookup")

        return _render_articles(
            request,
            order=order,
            selected_skus=_selected_skus(request.GET),
            selected_quantities=_selected_quantities(request.GET),
            show_returnable_only=_show_returnable_only(request.GET),
        )


class ReturnConfirmationView(View):
    """Preview the selected return before submission."""

    def get(self, request: HttpRequest, order_number: str) -> HttpResponse:
        order = _get_authenticated_order(request, order_number)
        if order is None:
            return redirect("lookup")

        pending_return = _get_session_return(
            request,
            key=_PENDING_RETURN_SESSION_KEY,
            order_number=order_number,
        )
        if pending_return is None:
            return redirect("articles", order_number=order_number)

        return render(
            request,
            "returns/confirm.html",
            {
                "order": order,
                "pending_return": pending_return,
            },
        )

    def post(self, request: HttpRequest, order_number: str) -> HttpResponse:
        order = _get_authenticated_order(request, order_number)
        if order is None:
            return redirect("lookup")

        selected_skus = _selected_skus(request.POST)
        selected_quantities = _selected_quantities(request.POST)
        show_returnable_only = _show_returnable_only(request.POST)
        selected_items = _build_selected_return_items(
            order,
            selected_skus=selected_skus,
            selected_quantities=selected_quantities,
        )
        if not selected_items:
            return _render_articles(
                request,
                order=order,
                error_message="Select at least one returnable item to continue.",
                selected_skus=selected_skus,
                selected_quantities=selected_quantities,
                show_returnable_only=show_returnable_only,
                status_code=400,
            )

        request.session[_PENDING_RETURN_SESSION_KEY] = _pending_return_context(
            order,
            selected_items,
        )
        request.session.pop(_COMPLETED_RETURN_SESSION_KEY, None)
        return redirect("return-confirmation", order_number=order_number)


class ReturnSubmitView(View):
    """Submit the pending return request."""

    def post(self, request: HttpRequest, order_number: str) -> HttpResponse:
        order = _get_authenticated_order(request, order_number)
        if order is None:
            return redirect("lookup")

        pending_return = _get_session_return(
            request,
            key=_PENDING_RETURN_SESSION_KEY,
            order_number=order_number,
        )
        if pending_return is None:
            return redirect("articles", order_number=order_number)

        request.session.pop(_PENDING_RETURN_SESSION_KEY, None)
        request.session[_COMPLETED_RETURN_SESSION_KEY] = {
            **pending_return,
            "reference": (
                f"RET-{order.order_number.removeprefix('RMA-')}-{secrets.token_hex(3).upper()}"
            ),
        }
        return redirect("return-success", order_number=order_number)


class ReturnSuccessView(View):
    """Display the submitted return confirmation."""

    def get(self, request: HttpRequest, order_number: str) -> HttpResponse:
        order = _get_authenticated_order(request, order_number)
        if order is None:
            return redirect("lookup")

        completed_return = _get_session_return(
            request,
            key=_COMPLETED_RETURN_SESSION_KEY,
            order_number=order_number,
        )
        if completed_return is None:
            return redirect("articles", order_number=order_number)

        return render(
            request,
            "returns/success.html",
            {
                "order": order,
                "completed_return": completed_return,
                "articles_url": reverse("articles", kwargs={"order_number": order_number}),
            },
        )
