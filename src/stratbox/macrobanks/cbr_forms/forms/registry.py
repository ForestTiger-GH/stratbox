"""Supported reporting forms and presentation profiles."""

from dataclasses import dataclass
from importlib import import_module
from types import MappingProxyType


@dataclass(frozen=True, slots=True)
class CbrFormEntry:
    code: str
    title: str
    excel_profile: str = "standard"

    @property
    def spec(self):
        return import_module(f"{__package__}.form{self.code}").DEFAULT_SPEC


FORM_REGISTRY = MappingProxyType({
    code: CbrFormEntry(code, f"0409{code}", "hierarchical_statement" if code == "802" else "standard")
    for code in ("101", "102", "123", "135", "802", "805")
})
