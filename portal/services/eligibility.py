"""Return eligibility engine."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from portal.types import Article, ArticleEligibility, Order

_RULES_PATH = Path(__file__).resolve().parent.parent / "data" / "eligibility_rules.yaml"


@dataclass(frozen=True)
class EligibilityRules:
    default_return_window_days: int
    category_return_window_days: dict[str, int]
    reasons: dict[str, str]


def _as_dict(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_int(value: object, *, default: int) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return default
    return default


def _as_str(value: object, *, default: str = "") -> str:
    return value if isinstance(value, str) else default


@lru_cache(maxsize=1)
def load_eligibility_rules() -> EligibilityRules:
    with _RULES_PATH.open(encoding="utf-8") as rules_file:
        loaded: object = yaml.safe_load(rules_file)

    raw_config = _as_dict(loaded)
    category_windows_raw = _as_dict(raw_config.get("category_return_window_days"))
    reasons_raw = _as_dict(raw_config.get("reasons"))

    category_windows = {
        category.strip().lower(): _as_int(days, default=30)
        for category, days in category_windows_raw.items()
        if isinstance(category, str)
    }
    reasons = {
        rule_id: _as_str(reason)
        for rule_id, reason in reasons_raw.items()
        if isinstance(rule_id, str)
    }

    return EligibilityRules(
        default_return_window_days=_as_int(
            raw_config.get("default_return_window_days"),
            default=30,
        ),
        category_return_window_days=category_windows,
        reasons=reasons,
    )


def _window_days_for(article: Article, rules: EligibilityRules) -> int:
    category = article.category.strip().lower()
    if category and category in rules.category_return_window_days:
        return rules.category_return_window_days[category]
    return rules.default_return_window_days


def _non_returnable(
    article: Article,
    *,
    reason: str,
    matched_rule: str,
) -> ArticleEligibility:
    return ArticleEligibility(
        article=article,
        returnable=False,
        reason=reason,
        matched_rule=matched_rule,
    )


def _is_window_expired(
    *,
    delivery_date: datetime,
    window_days: int,
    now: datetime,
) -> bool:
    return now > delivery_date + timedelta(days=window_days)


def evaluate_eligibility(order: Order) -> list[ArticleEligibility]:
    """Evaluate return eligibility for every article in *order*.

    Returns:
        A list of :class:`ArticleEligibility`, one per article in the order.
    """
    rules = load_eligibility_rules()
    now = datetime.now()
    results: list[ArticleEligibility] = []

    for article in order.articles:
        if article.quantity_returned >= article.quantity:
            results.append(
                _non_returnable(
                    article,
                    reason=rules.reasons["fully_returned"],
                    matched_rule="fully_returned",
                )
            )
            continue

        if article.is_digital:
            results.append(
                _non_returnable(
                    article,
                    reason=rules.reasons["digital_item"],
                    matched_rule="digital_item",
                )
            )
            continue

        if article.is_final_sale:
            results.append(
                _non_returnable(
                    article,
                    reason=rules.reasons["final_sale"],
                    matched_rule="final_sale",
                )
            )
            continue

        window_days = _window_days_for(article, rules)
        if _is_window_expired(
            delivery_date=order.delivery_date,
            window_days=window_days,
            now=now,
        ):
            results.append(
                _non_returnable(
                    article,
                    reason=rules.reasons["return_window_expired"],
                    matched_rule="return_window_expired",
                )
            )
            continue

        results.append(
            ArticleEligibility(
                article=article,
                returnable=True,
                reason="",
                matched_rule="",
            )
        )

    return results
