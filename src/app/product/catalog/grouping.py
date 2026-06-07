from __future__ import annotations

from collections import defaultdict

from .models import ProductOperationSpec, ProductRegistry


def group_operations(registry: ProductRegistry) -> dict[str, list[ProductOperationSpec]]:
    grouped: dict[str, list[ProductOperationSpec]] = defaultdict(list)
    for operation in sorted(registry.enabled(), key=lambda item: (item.group_order, item.group.lower(), item.order, item.title.lower())):
        grouped[operation.group].append(operation)
    return dict(grouped)
