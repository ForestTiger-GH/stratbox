"""Fiscal products are declared content, not their own execution pipelines."""
from stratbox.capabilities.model.domains import ProductSpec

BUDGET_OVERVIEW = ProductSpec("minfin.budget.overview", commands={},
    settings={"format": "csv", "filters": {"metric": ("budget.revenue", "budget.expenditure", "budget.balance")}})
FUND_OVERVIEW = ProductSpec("minfin.nwf.overview", commands={},
    settings={"format": "csv", "filters": {"metric": ("nwf.total", "nwf.other_assets", "nwf.liquid")}})
