"""Budget calculation eligibility and explicit numerical treatment."""
from stratbox.capabilities.model.domains import CalculationSpec

BUDGET_CHANGES = CalculationSpec("minfin.budget.changes", commands={},
    semantics={"same_accumulation_window": True, "same_budget_perimeter": True},
    settings={"mode": "absolute", "required_measure_kind": "flow", "same_accumulation_window": True})
BUDGET_PERIOD_FLOWS = CalculationSpec("minfin.budget.period_flows", commands={},
    semantics={"required_measure_kind": "flow", "required_value_basis": "ytd"},
    settings={"reset": "calendar_year"})
BUDGET_RATIOS = CalculationSpec("minfin.budget.ratios", commands={},
    semantics={"same_period_and_perimeter": True},
    settings={"zero_policy": "undefined", "multiplier": 1})
