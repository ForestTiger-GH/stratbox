from __future__ import annotations

import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.contracts import SorsPivotRequest
from stratbox.macrobanks.cbr_sors_restoration.results import (
    SorsCrosswalkResult,
    SorsPivotResult,
    SorsRestorationResult,
)


def _resolve_region(frame: pd.DataFrame, request: SorsPivotRequest) -> tuple[str, str]:
    if request.region_code:
        matches = frame[frame['region_code'].astype(str).eq(str(request.region_code))]
    else:
        matches = frame[frame['region_name'].astype(str).eq(str(request.region_name))]
    if matches.empty:
        selector = request.region_code or request.region_name
        raise ValueError(f'Unknown SORS region selector: {selector!r}')
    identities = matches[['region_code', 'region_name']].drop_duplicates()
    if len(identities) != 1:
        raise ValueError('Region selector is ambiguous')
    row = identities.iloc[0]
    return str(row.region_code), str(row.region_name)


def _flatten_measure_columns(table: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(table.columns, pd.MultiIndex):
        return table
    table = table.copy()
    table.columns = [
        str(metric) if field == 'value' else f'{metric}__{field}'
        for field, metric in table.columns
    ]
    return table


def build_sors_pivot(
    result: SorsRestorationResult | SorsCrosswalkResult,
    request: SorsPivotRequest,
) -> SorsPivotResult:
    frame = result.regional_okved2_grid
    if request.evidence_layer != 'PRIMARY':
        frame = frame[
            frame['evidence_layer'].astype(str).eq(request.evidence_layer)
        ].copy()
    frame = frame[frame['metric'].astype(str).isin(request.metrics)]
    selected_region_code: str | None = None
    selected_region_name: str | None = None
    selected_class_code: str | None = None

    if request.class_code is None:
        selected_region_code, selected_region_name = _resolve_region(frame, request)
        selected = frame[frame['region_code'].astype(str).eq(selected_region_code)].copy()
        orientation = 'REGION_TO_CLASSES'
        index_columns = [
            'section_order', 'section_code', 'section_name',
            'class_order', 'class_code', 'class_name',
        ]
    else:
        selected_class_code = str(request.class_code)
        selected = frame[frame['class_code'].astype(str).eq(selected_class_code)].copy()
        if selected.empty:
            raise ValueError(f'Unknown SORS class code: {selected_class_code!r}')
        orientation = 'CLASS_TO_REGIONS'
        index_columns = [
            'federal_district_order', 'federal_district_code',
            'federal_district_name', 'region_order', 'region_code', 'region_name',
        ]

    if not request.include_unidentified:
        accepted_column = (
            'is_final_accepted'
            if 'is_final_accepted' in selected.columns
            else 'is_strict_fact'
        )
        selected = selected[selected[accepted_column].astype(bool)]
    source_rows = len(selected)
    identified_cells = int(selected['value'].notna().sum())
    unidentified_cells = int(selected['value'].isna().sum())

    value_fields = ['value']
    if request.include_bounds:
        value_fields.extend(['lower_bound', 'upper_bound'])
    if request.include_status:
        value_fields.append('identification_status')

    duplicate_keys = selected.duplicated(index_columns + ['metric'])
    if duplicate_keys.any():
        raise ValueError('SORS pivot source contains duplicate region/class/metric rows')
    table = selected.set_index(index_columns + ['metric'])[value_fields].unstack('metric')
    table = _flatten_measure_columns(table).reset_index()
    order_columns = [column for column in index_columns if column.endswith('_order')]
    if order_columns:
        table = table.sort_values(order_columns, kind='stable')
    table = table.drop(columns=order_columns, errors='ignore').reset_index(drop=True)

    return SorsPivotResult(
        table=table,
        orientation=orientation,
        selected_region_code=selected_region_code,
        selected_region_name=selected_region_name,
        selected_class_code=selected_class_code,
        metrics=tuple(request.metrics),
        source_rows=source_rows,
        output_rows=len(table),
        identified_cells=identified_cells,
        unidentified_cells=unidentified_cells,
    )
