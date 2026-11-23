"""Statically registered economic calculation profiles; references are stable IDs."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable

from ..tables.contracts import FlakeTable
from .contracts import HeadlineMetric
from .indicators import budget_metrics, nwf_metrics


@dataclass(frozen=True, slots=True)
class HeadlineProfile:
    profile_id: str
    accepted_basis: frozenset[str]
    periods: frozenset[str]
    calculator: Callable[[FlakeTable, int, int | None], tuple[HeadlineMetric, ...]]
    method_version: int = 2


_METRICS = {
    "minfin.budget_headlines.v1": HeadlineProfile("minfin.budget_headlines.v1",
        frozenset({"ytd", "annual"}), frozenset({"monthly", "quarterly", "annual"}), budget_metrics),
    "minfin.nwf_headlines.v1": HeadlineProfile("minfin.nwf_headlines.v1",
        frozenset({"stock"}), frozenset({"monthly"}), nwf_metrics),
}


def headline_profile(profile_id: str) -> HeadlineProfile:
    try:
        return _METRICS[profile_id]
    except (KeyError, TypeError):
        raise ValueError("minfin.profile.headlines_unknown") from None


__all__ = ("HeadlineProfile", "headline_profile")