"""Explicit Excel style selection for workbook renderers."""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from .builtin import DEFAULT_PRESET_NAME, PRESETS
from .models import StyleSpec


@dataclass(frozen=True, slots=True)
class ExcelStylesRegistry:
    presets: Mapping[str, StyleSpec]
    default_preset_name: str

    def __post_init__(self) -> None:
        presets = {key.strip().upper(): value for key, value in self.presets.items()}
        default = self.default_preset_name.strip().upper()
        if not default or default not in presets or len(presets) != len(self.presets):
            raise ValueError("Invalid Excel preset registry")
        object.__setattr__(self, "presets", MappingProxyType(presets))
        object.__setattr__(self, "default_preset_name", default)


BUILTIN_STYLES = ExcelStylesRegistry(PRESETS, DEFAULT_PRESET_NAME)
