from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

ParamType = Literal['text', 'int', 'bool', 'select', 'path_dir', 'path_file']
FieldSection = Literal['basic', 'advanced']


@dataclass(frozen=True, slots=True)
class ProductParamSpec:
    name: str
    title: str
    type: ParamType = 'text'
    default: Any = None
    description: str = ''
    required: bool = False
    options: tuple[tuple[str, str], ...] = ()
    section: FieldSection = 'basic'
    placeholder: str = ''
    min_value: int | None = None
    max_value: int | None = None
