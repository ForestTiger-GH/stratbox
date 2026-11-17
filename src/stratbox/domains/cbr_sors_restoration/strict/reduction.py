from __future__ import annotations

import numpy as np
import pandas as pd


class _UnionFind:
    def __init__(self, size: int):
        self.parent = np.arange(size, dtype=np.int32)
        self.rank = np.zeros(size, dtype=np.int8)

    def find(self, item: int) -> int:
        parent = self.parent
        root = item
        while parent[root] != root:
            root = int(parent[root])
        while parent[item] != item:
            next_item = int(parent[item])
            parent[item] = root
            item = next_item
        return root

    def union(self, left: int, right: int) -> None:
        a, b = self.find(left), self.find(right)
        if a == b:
            return
        if self.rank[a] < self.rank[b]:
            a, b = b, a
        self.parent[b] = a
        if self.rank[a] == self.rank[b]:
            self.rank[a] += 1


def assign_connected_components(
    variables_grid: pd.DataFrame,
    row_columns: list[np.ndarray],
) -> pd.DataFrame:
    out = variables_grid.copy()
    active = out[out['solver_column'].notna()].copy()
    if active.empty:
        out['connected_component_id'] = None
        return out
    size = int(active['solver_column'].max()) + 1
    union_find = _UnionFind(size)
    for columns in row_columns:
        if len(columns) <= 1:
            continue
        first = int(columns[0])
        for column in columns[1:]:
            union_find.union(first, int(column))
    roots = [union_find.find(i) for i in range(size)]
    root_order = {root: position + 1 for position, root in enumerate(sorted(set(roots)))}
    component_by_column = {
        column: f'component:{root_order[root]:04d}'
        for column, root in enumerate(roots)
    }
    out['connected_component_id'] = out['solver_column'].map(component_by_column)
    return out
