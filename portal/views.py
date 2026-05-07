from __future__ import annotations

from typing import Any

from django.http import HttpRequest, HttpResponse, QueryDict
from django.shortcuts import redirect, render
from django.views import View

from portal.forms import LookupForm
from portal.services.eligibility import evaluate_eligibility
from portal.services.order_store import find_order, get_order
from portal.types import ArticleEligibility, Order

_HX_REQUEST_HEADER = "HX-Request"


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


def _render_articles(
    request: HttpRequest,
    *,
    order: Order,
    selected_skus: set[str] | None = None,
    selected_quantities: dict[str, int] | None = None,
    show_returnable_only: bool = False,
) -> HttpResponse:
    context = {
        "order": order,
        "article_rows": _build_article_rows(
            order,
            selected_skus=selected_skus,
            selected_quantities=selected_quantities,
            show_returnable_only=show_returnable_only,
        ),
        "error_message": "",
        "show_returnable_only": show_returnable_only,
    }

    template_name = (
        "returns/_article_selection_panel.html"
        if _is_hx_request(request)
        else "returns/articles.html"
    )
    return render(request, template_name, context)


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
                return redirect("articles", order_number=order.order_number)

        return render(request, "returns/lookup.html", {"form": form})


class ArticlesView(View):
    """Articles page – shows items in the order with eligibility info."""

    def get(self, request: HttpRequest, order_number: str) -> HttpResponse:
        if request.session.get("order_number") != order_number:
            return redirect("lookup")

        order = get_order(order_number)
        if order is None:
            return redirect("lookup")

        return _render_articles(
            request,
            order=order,
            selected_skus=_selected_skus(request.GET),
            selected_quantities=_selected_quantities(request.GET),
            show_returnable_only=_show_returnable_only(request.GET),
        )
