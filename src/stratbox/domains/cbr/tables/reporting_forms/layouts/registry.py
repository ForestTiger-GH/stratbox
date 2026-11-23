"""Reviewed physical projections; source availability is independent of these layouts."""
from dataclasses import dataclass
from importlib import import_module
from types import MappingProxyType

@dataclass(frozen=True, slots=True)
class FormLayout:
    code: str
    edition: str = "cbr.forms.layout.v1"

    @property
    def spec(self):
        return import_module(f"{__package__}.form{self.code}").DEFAULT_SPEC

LAYOUT_REGISTRY = MappingProxyType({code: FormLayout(code) for code in ("101", "102", "123", "135", "802", "805")})
