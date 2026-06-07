from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import ProductParamSpec


def validate_field_value(spec: ProductParamSpec, value: Any) -> None:
    if spec.required and spec.type in {'path_dir', 'path_file', 'text'} and not str(value or '').strip():
        raise ValueError(f'Поле «{spec.title}» обязательно.')
    if spec.type == 'int' and value not in (None, ''):
        try:
            int_value = int(value)
        except Exception as exc:
            raise ValueError(f'Поле «{spec.title}» должно быть числом.') from exc
        if spec.min_value is not None and int_value < spec.min_value:
            raise ValueError(f'Поле «{spec.title}» должно быть не меньше {spec.min_value}.')
        if spec.max_value is not None and int_value > spec.max_value:
            raise ValueError(f'Поле «{spec.title}» должно быть не больше {spec.max_value}.')
    if spec.type in {'path_dir', 'path_file'} and str(value or '').strip():
        Path(str(value)).expanduser()
