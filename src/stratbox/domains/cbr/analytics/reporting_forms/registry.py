"""Explicit financial-model editions and the source layouts they admit."""
from dataclasses import dataclass
from types import MappingProxyType

@dataclass(frozen=True, slots=True)
class FinancialModel:
    form: str
    edition: str
    resource: str

MODEL_REGISTRY = MappingProxyType({code: FinancialModel(code, f"cbr.forms.model.{code}.v1", f"form{code}.csv")
    for code in ("101", "102", "123", "135", "802", "805")})
