"""Pure graph validation helpers shared by authoring and plan models."""
from types import MappingProxyType
from typing import Mapping
import re

class CompositionError(ValueError):
    @property
    def code(self):
        return self.args[0]


def _name(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]*", value):
        raise CompositionError("composition.invalid_name")


def _mapping(value):
    if not isinstance(value, Mapping) or any(not isinstance(k, str) for k in value):
        raise CompositionError("composition.invalid_mapping")
    return MappingProxyType(dict(value))


