from __future__ import annotations

from collections import defaultdict

from .models import OperationSpec, OperationRegistry


def group_operations(registry: OperationRegistry) -> dict[str, list[OperationSpec]]:
    grouped: dict[str, list[OperationSpec]] = defaultdict(list)
    for operation in sorted(registry.enabled(), key=lambda item: (item.group_order, item.group.lower(), item.order, item.title.lower())):
        grouped[operation.group].append(operation)
    return dict(grouped)
