from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.strict.quantities import SorsQuantityGraph


@dataclass(frozen=True)
class SorsPublicationGraph:
    """Complete/disjoint publication partitions used by Published Mass Tokens."""

    partitions_grid: pd.DataFrame


def _tuple(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, tuple):
        return tuple(str(item) for item in value)
    if isinstance(value, list):
        return tuple(str(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return tuple(sorted(str(item) for item in value))
    try:
        if pd.isna(value):
            return ()
    except (TypeError, ValueError):
        pass
    return (str(value),)


def _support_record(row) -> dict[str, object]:
    regions = frozenset(_tuple(getattr(row, 'support_region_codes', ())))
    classes = frozenset(_tuple(getattr(row, 'support_class_codes', ())))
    return {
        'quantity_id': str(row.quantity_id),
        'quantity_kind': str(row.quantity_kind),
        'portfolio_scope': getattr(row, 'portfolio_scope', None),
        'metric': str(getattr(row, 'metric', '')),
        'regions': regions,
        'classes': classes,
        'cell_count': len(regions) * len(classes),
        'source_observation_ids': tuple(
            _tuple(getattr(row, 'source_observation_ids', ()))
        ),
    }


def _source_family(quantity_id: str, region_count: int) -> str | None:
    if quantity_id.startswith('publication:geography:') and region_count == 1:
        return 'ATOMIC_GEOGRAPHY'
    if quantity_id.startswith('publication:national_class:'):
        return 'NATIONAL_CLASS'
    if quantity_id.startswith('publication:fd_section:'):
        return 'FD_SECTION'
    return None


def _parent_allowed_families(quantity_id: str, region_count: int) -> tuple[str, ...]:
    if quantity_id.startswith('publication:national_total'):
        return ('ATOMIC_GEOGRAPHY', 'NATIONAL_CLASS', 'FD_SECTION')
    if quantity_id.startswith('publication:geography:'):
        if region_count <= 1:
            return ()
        return ('ATOMIC_GEOGRAPHY', 'FD_SECTION')
    if quantity_id.startswith('publication:national_class:'):
        return ('FD_SECTION',)
    return ()


def _exact_cover_ids(
    parent: dict[str, object],
    candidates: tuple[dict[str, object], ...],
) -> tuple[str, ...]:
    """Select a globally-disjoint family iff its subset exactly covers parent.

    The three publication families are disjoint by registry construction:
    atomic geographies partition geography, national publication categories
    partition classes, and FD×section rectangles partition both dimensions.
    We therefore only need a subset filter plus a cardinality equality instead of
    pairwise O(N²) overlap checks for every parent.
    """

    parent_regions = parent['regions']
    parent_classes = parent['classes']
    assert isinstance(parent_regions, frozenset)
    assert isinstance(parent_classes, frozenset)
    if not parent_regions or not parent_classes:
        return ()
    selected: list[dict[str, object]] = []
    covered = 0
    for child in candidates:
        if child['quantity_id'] == parent['quantity_id']:
            continue
        child_regions = child['regions']
        child_classes = child['classes']
        assert isinstance(child_regions, frozenset)
        assert isinstance(child_classes, frozenset)
        if child_regions.issubset(parent_regions) and child_classes.issubset(parent_classes):
            selected.append(child)
            covered += int(child['cell_count'])
    if len(selected) < 2 or covered != int(parent['cell_count']):
        return ()
    return tuple(str(child['quantity_id']) for child in selected)


def _validate_family_disjointness(
    families: dict[tuple[str, str], tuple[dict[str, object], ...]]
) -> None:
    """One cheap global guard replaces repeated pairwise checks per parent."""

    for (metric, family), records in families.items():
        seen: set[tuple[str, str]] = set()
        for record in records:
            regions = record['regions']
            classes = record['classes']
            assert isinstance(regions, frozenset)
            assert isinstance(classes, frozenset)
            for region in regions:
                for class_code in classes:
                    key = (region, class_code)
                    if key in seen:
                        raise ValueError(
                            'Publication family is not disjoint: '
                            f'metric={metric}, family={family}, cell={key}'
                        )
                    seen.add(key)


def _published_hierarchy_partitions(
    published_records: tuple[dict[str, object], ...]
) -> list[dict[str, object]]:
    families_mut: dict[tuple[str, str], list[dict[str, object]]] = {}
    for record in published_records:
        regions = record['regions']
        assert isinstance(regions, frozenset)
        family = _source_family(str(record['quantity_id']), len(regions))
        if family is not None:
            families_mut.setdefault((str(record['metric']), family), []).append(record)
    families = {
        key: tuple(sorted(records, key=lambda item: str(item['quantity_id'])))
        for key, records in families_mut.items()
    }
    _validate_family_disjointness(families)

    rows: list[dict[str, object]] = []
    for parent in published_records:
        regions = parent['regions']
        assert isinstance(regions, frozenset)
        for family in _parent_allowed_families(str(parent['quantity_id']), len(regions)):
            children = _exact_cover_ids(
                parent,
                families.get((str(parent['metric']), family), ()),
            )
            if not children:
                continue
            rows.append(
                {
                    'partition_id': (
                        f'publication_partition:{parent["quantity_id"]}:{family.lower()}'
                    ),
                    'partition_kind': f'PUBLISHED_{family}',
                    'partition_layer': 'PUBLISHED_HIERARCHY',
                    'parent_quantity_id': str(parent['quantity_id']),
                    'parent_quantity_kind': 'PUBLISHED_AGGREGATE',
                    'portfolio_scope': parent['portfolio_scope'],
                    'metric': str(parent['metric']),
                    'child_quantity_ids': children,
                    'is_complete': True,
                    'is_disjoint': True,
                    'inheritance_enabled': True,
                    'inheritance_semantics': 'EXPLICIT_EQUAL_VALUE_LOCALIZATION',
                    'source_observation_ids': parent['source_observation_ids'],
                }
            )
    return rows


def _relation_is_exact_target_cover(
    parent: dict[str, object],
    child_ids: tuple[str, ...],
    quantity_meta: dict[str, dict[str, object]],
) -> bool:
    """Return True when relation children form an exact same-metric rectangle cover.

    Most production relations use singleton region×class metric targets, but the
    publication layer must not *require* singleton children: deterministic closure
    can expose a coarser quantity (for example ``all regions × one class``) whose
    published bucket is useful for token localization.  The old fast path that
    compared ``len(children)`` with parent cell count silently dropped such valid
    partitions.

    Relation child lists are already sparse and finite.  We therefore validate the
    exact support union directly.  This remains cheap relative to LP construction
    while preserving the semantic invariant needed by inheritance: children are a
    complete, disjoint partition of the parent's region×class support.
    """

    parent_regions = parent['regions']
    parent_classes = parent['classes']
    assert isinstance(parent_regions, frozenset)
    assert isinstance(parent_classes, frozenset)
    expected_count = int(parent['cell_count'])
    if not child_ids or expected_count <= 0:
        return False

    seen: set[tuple[str, str]] = set()
    for child_id in child_ids:
        child = quantity_meta.get(child_id)
        if child is None or child['quantity_kind'] != 'REGIONAL_CLASS_METRIC':
            return False
        if child['metric'] != parent['metric']:
            return False
        regions = child['regions']
        classes = child['classes']
        assert isinstance(regions, frozenset)
        assert isinstance(classes, frozenset)
        if not regions or not classes:
            return False
        if not regions.issubset(parent_regions) or not classes.issubset(parent_classes):
            return False
        for region in regions:
            for class_code in classes:
                key = (region, class_code)
                if key in seen:
                    return False
                seen.add(key)
                if len(seen) > expected_count:
                    return False
    return len(seen) == expected_count



def publication_hierarchy_relations(
    publication_graph: SorsPublicationGraph,
) -> pd.DataFrame:
    """Return exact latent sum relations implied by publication partitions.

    The integer representatives of independently published tables do *not* add
    exactly after rounding.  Their hidden monetary quantities do, however, add
    exactly whenever the publication supports form a complete/disjoint partition
    of the same metric.  Feeding only ``PUBLISHED_HIERARCHY`` partitions to the
    interval engine therefore strengthens deterministic closure without ever
    performing arithmetic on rounded representatives.

    ``LATENT_TARGETS`` partitions are omitted here because those equations already
    exist in the base quantity graph.
    """

    partitions = publication_graph.partitions_grid
    if partitions.empty:
        return pd.DataFrame()
    hierarchy = partitions[
        partitions['partition_layer'].astype(str).eq('PUBLISHED_HIERARCHY')
        & partitions['is_complete'].astype(bool)
        & partitions['is_disjoint'].astype(bool)
    ]
    rows: list[dict[str, object]] = []
    for row in hierarchy.itertuples(index=False):
        rows.append(
            {
                'relation_id': f'latent:{row.partition_id}',
                'relation_kind': 'PUBLICATION_HIERARCHY',
                'parent_quantity_id': str(row.parent_quantity_id),
                'child_quantity_ids': tuple(str(v) for v in row.child_quantity_ids),
                'source_observation_ids': tuple(
                    str(v) for v in (getattr(row, 'source_observation_ids', ()) or ())
                ),
            }
        )
    return pd.DataFrame(rows)

def build_publication_graph(graph: SorsQuantityGraph) -> SorsPublicationGraph:
    """Compile publication partitions without treating rounding as arithmetic.

    ``PUBLISHED_HIERARCHY`` connects official aggregates that exactly partition the
    same metric (Russia→regions, Russia→national classes, FD→regions/sections, ...).
    ``LATENT_TARGETS`` connects an official aggregate to the full region×class
    target rectangle beneath it.  A token may traverse either only when one child
    already has the same published value and every sibling is publication-zero.
    Metric-component algebra is deliberately absent.
    """

    quantities = graph.quantities_grid
    required = {'support_region_codes', 'support_class_codes'}
    missing = sorted(required - set(quantities.columns))
    if missing:
        raise ValueError(f'Quantity graph lacks publication support metadata: {missing}')

    records = tuple(_support_record(row) for row in quantities.itertuples(index=False))
    quantity_meta = {str(record['quantity_id']): record for record in records}
    published_records = tuple(
        record for record in records if record['quantity_kind'] == 'PUBLISHED_AGGREGATE'
    )
    rows = _published_hierarchy_partitions(published_records)

    for relation in graph.relations_grid.itertuples(index=False):
        if str(relation.relation_kind) == 'METRIC_COMPONENT_SUM':
            continue
        parent_id = str(relation.parent_quantity_id)
        parent = quantity_meta.get(parent_id)
        if parent is None or parent['quantity_kind'] != 'PUBLISHED_AGGREGATE':
            continue
        children = tuple(str(value) for value in relation.child_quantity_ids)
        if not children or not _relation_is_exact_target_cover(parent, children, quantity_meta):
            continue
        rows.append(
            {
                'partition_id': f'publication_partition:{relation.relation_id}:targets',
                'partition_kind': str(relation.relation_kind),
                'partition_layer': 'LATENT_TARGETS',
                'parent_quantity_id': parent_id,
                'parent_quantity_kind': 'PUBLISHED_AGGREGATE',
                'portfolio_scope': parent['portfolio_scope'],
                'metric': str(parent['metric']),
                'child_quantity_ids': children,
                'is_complete': True,
                'is_disjoint': True,
                'inheritance_enabled': True,
                'inheritance_semantics': 'EXPLICIT_EQUAL_VALUE_LOCALIZATION',
                'source_observation_ids': tuple(relation.source_observation_ids),
            }
        )

    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame = frame.drop_duplicates('partition_id').sort_values(
            'partition_id', kind='stable'
        ).reset_index(drop=True)
    return SorsPublicationGraph(frame)
