"""Numerical treatment is separate from publisher processing."""
from stratbox.capabilities.model.domains import CalculationSpec

STOCK_CHANGE = CalculationSpec("fns.stock_change", commands={},
    semantics={"required_measure_kind": "stock", "net_change_is_not_entries_or_exits": True},
    settings={"mode": "absolute", "required_measure_kind": "stock"})
STOCK_SHARE = CalculationSpec("fns.stock_share", commands={},
    semantics={"required_measure_kind": "stock", "same_period_and_perimeter": True},
    settings={"zero_policy": "undefined", "multiplier": 1, "required_measure_kind": "stock"})
