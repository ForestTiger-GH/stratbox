"""Fund stock treatment and the reviewed same-date liquid-assets formula."""
from stratbox.capabilities.model.domains import CalculationSpec
from stratbox.shared.data.values import FormulaSpec

FUND_LIQUID_ASSETS = CalculationSpec("minfin.nwf.liquid_assets", commands={},
    settings=FormulaSpec("total - other", {"total": "nwf.total", "other": "nwf.other_assets"},
        "nwf.liquid", "RUB"),
    semantics={"required_measure_kind": "stock", "same_period_and_perimeter": True})
FUND_CHANGES = CalculationSpec("minfin.nwf.changes", commands={},
    semantics={"required_measure_kind": "stock", "same_asset_perimeter": True},
    settings={"mode": "absolute", "required_measure_kind": "stock"})
