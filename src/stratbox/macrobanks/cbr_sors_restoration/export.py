from __future__ import annotations

import gc
import hashlib
import math
import re
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path
from threading import Lock
from typing import Any

import pandas as pd
import xlsxwriter
import xlsxwriter.workbook as xlsxwriter_workbook
from zipfile import ZipFile

from stratbox.macrobanks.cbr_sors_restoration.contracts import SorsWorkbookRequest
from stratbox.macrobanks.cbr_sors_restoration.pivots import build_sors_pivot
from stratbox.macrobanks.cbr_sors_restoration.results import (
    SorsCrosswalkResult,
    SorsRestorationResult,
    SorsWorkbookResult,
)



_XLSXWRITER_ZIP_LOCK = Lock()


class _FastZipFile(ZipFile):
    """Use fast Deflate for large analytical workbooks."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('compresslevel', 1)
        super().__init__(*args, **kwargs)


_PRIMARY_COLUMNS = (
    'as_of_date', 'region_code', 'class_code', 'metric',
    'value', 'value_precision', 'published_value', 'exact_value',
    'publication_status', 'latent_status', 'evidence_method', 'assumption_tier', 'evidence_strength', 'fact_id',
    'feasibility_confirmed', 'lower_bound', 'upper_bound',
    'lower_attained', 'upper_attained', 'interval_width',
    'identification_status', 'derivation_method', 'is_primary_fact',
    'is_reconstructed', 'bounds_certified', 'value_identified',
    'is_final_accepted', 'is_estimate', 'is_benchmark_estimate',
    'benchmark_value', 'evidence_layer', 'evidence_profile', 'mapping_version',
    'scenario_ids', 'scenario_coverage_complete', 'source_observation_ids',
    'supporting_partition_ids', 'supporting_relation_ids', 'supporting_fact_ids', 'proof_ids', 'is_zero_at_published_precision', 'is_exact_zero',
    'is_lp_certified', 'lp_lower_certified', 'lp_upper_certified',
)


_REGION_COLUMNS = (
    'region_code', 'region_name', 'region_order',
    'federal_district_code', 'federal_district_name',
    'federal_district_order',
)

_CLASS_COLUMNS = (
    'class_code', 'class_name', 'class_order',
    'section_code', 'section_name', 'section_order',
    'publication_category_code', 'is_individually_published',
)

_METRIC_COLUMNS = ('metric', 'metric_name', 'metric_order', 'unit')



def _sheet_name(value: str, used: set[str]) -> str:
    cleaned = re.sub(r'[:\\/?*\[\]]', '_', value).strip() or 'Sheet'
    candidate = cleaned[:31]
    suffix = 2
    while candidate in used:
        tail = f'_{suffix}'
        candidate = f'{cleaned[:31-len(tail)]}{tail}'
        suffix += 1
    used.add(candidate)
    return candidate


def _excel_value(value: Any) -> Any:
    if value is None or value is pd.NA:
        return None
    if isinstance(value, float):
        if math.isnan(value):
            return None
        if math.isinf(value):
            return 'INF' if value > 0 else '-INF'
        return value
    if isinstance(value, (str, int, bool, datetime, date)):
        return value
    if hasattr(value, 'item'):
        try:
            return _excel_value(value.item())
        except Exception:
            pass
    if isinstance(value, (tuple, list, set, dict)):
        return str(value)
    return str(value)


def _widths(frame: pd.DataFrame) -> list[int]:
    sample = frame.head(200)
    widths: list[int] = []
    for column in frame.columns:
        values = sample[column].map(_excel_value).dropna().astype(str)
        maximum = max([len(str(column)), *(len(value) for value in values)], default=len(str(column)))
        widths.append(min(max(maximum + 2, 10), 48))
    return widths


def _write_frame(workbook, frame: pd.DataFrame, sheet: str, header_format) -> None:
    worksheet = workbook.add_worksheet(sheet)
    worksheet.freeze_panes(1, 0)
    worksheet.write_row(0, 0, list(frame.columns), header_format)
    for row_index, row in enumerate(frame.itertuples(index=False, name=None), start=1):
        worksheet.write_row(row_index, 0, [_excel_value(value) for value in row])
    if len(frame.columns):
        worksheet.autofilter(0, 0, max(len(frame), 1), len(frame.columns) - 1)
    for column_index, width in enumerate(_widths(frame)):
        worksheet.set_column(column_index, column_index, width)


def export_sors_workbook(
    result: SorsRestorationResult | SorsCrosswalkResult,
    request: SorsWorkbookRequest,
) -> SorsWorkbookResult:
    output = Path(request.output_path)
    if output.exists() and not request.overwrite:
        raise FileExistsError(f'SORS workbook already exists: {output}')
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()
    used: set[str] = set()
    frames: list[tuple[str, pd.DataFrame]] = []

    def queue(frame: pd.DataFrame, name: str) -> None:
        frames.append((_sheet_name(name, used), frame))

    if request.include_primary_grid:
        columns = [
            column
            for column in _PRIMARY_COLUMNS
            if column in result.regional_okved2_grid
        ]
        primary = result.regional_okved2_grid[columns]
        chunk_size = request.primary_grid_rows_per_sheet
        if chunk_size is None:
            queue(primary, 'Regional_OKVED2')
        else:
            for start in range(0, len(primary), chunk_size):
                part = start // chunk_size + 1
                name = 'Regional_OKVED2' if part == 1 else f'Regional_OKVED2_{part:02d}'
                queue(primary.iloc[start : start + chunk_size], name)
    if request.include_dimensions:
        region_columns = [
            column for column in _REGION_COLUMNS
            if column in result.regional_okved2_grid
        ]
        class_columns = [
            column for column in _CLASS_COLUMNS
            if column in result.regional_okved2_grid
        ]
        metric_columns = [
            column for column in _METRIC_COLUMNS
            if column in result.regional_okved2_grid
        ]
        queue(
            result.regional_okved2_grid[region_columns]
            .drop_duplicates('region_code')
            .sort_values('region_order', kind='stable')
            .reset_index(drop=True),
            'Regions',
        )
        queue(
            result.regional_okved2_grid[class_columns]
            .drop_duplicates('class_code')
            .sort_values('class_order', kind='stable')
            .reset_index(drop=True),
            'OKVED2',
        )
        queue(
            result.regional_okved2_grid[metric_columns]
            .drop_duplicates('metric')
            .sort_values('metric_order', kind='stable')
            .reset_index(drop=True),
            'Metrics',
        )
    strict_source = (
        result
        if isinstance(result, SorsRestorationResult)
        else result._strict_result
    )
    if request.include_restored_facts and strict_source is not None:
        columns = [
            column for column in _PRIMARY_COLUMNS
            if column in strict_source.restored_facts_grid
        ]
        queue(strict_source.restored_facts_grid[columns], 'Restored_Facts')
    if isinstance(result, SorsCrosswalkResult):
        if request.include_crosswalk_facts:
            columns = [
                column for column in _PRIMARY_COLUMNS
                if column in result.crosswalk_facts_grid
            ]
            queue(result.crosswalk_facts_grid[columns], 'Crosswalk_Facts')
        if request.include_crosswalk_bounds:
            queue(result.crosswalk_bounds_grid, 'Crosswalk_Bounds')
            queue(result.scenario_bounds_grid, 'Crosswalk_Scenarios')
        if request.include_crosswalk_mapping:
            queue(result.mapping_edges_grid, 'Crosswalk_Edges')
            queue(result.relations_grid, 'Crosswalk_Relations')
    if request.include_validation and strict_source is not None:
        queue(strict_source.validation_grid, 'Validation')
    if request.include_conflicts:
        queue(result.conflicts_grid, 'Conflicts')
    if request.include_source_grid and strict_source is not None:
        queue(strict_source.source_grid, 'SourceGrid')
    if request.include_components and strict_source is not None:
        queue(strict_source.components_grid, 'Components')
    if request.include_fact_ledger and strict_source is not None:
        queue(strict_source.facts_ledger_grid, 'Fact_Ledger')
        queue(strict_source.current_component_facts_grid, 'Current_Component_Facts')
    if request.include_publication_partitions and strict_source is not None:
        queue(strict_source.publication_partitions_grid, 'Publication_Partitions')
    if request.include_publication_tokens and strict_source is not None:
        queue(strict_source.publication_tokens_grid, 'Publication_Tokens')
    if request.include_inheritance_events and strict_source is not None:
        queue(strict_source.inheritance_events_grid, 'Inheritance_Events')
    if request.include_promotion_events and strict_source is not None:
        queue(strict_source.promotion_events_grid, 'Promotions')
    if request.include_fixed_point_passes and strict_source is not None:
        queue(strict_source.fixed_point_passes_grid, 'Fixed_Point_Passes')
    if request.include_optimization_rounds and strict_source is not None:
        queue(strict_source.optimization_rounds_grid, 'Optimization_Rounds')
    if request.include_target_bounds and strict_source is not None:
        queue(strict_source.target_bounds_grid, 'Target_Bounds')
    if request.include_rounding_profiles and strict_source is not None:
        queue(strict_source.rounding_profiles_grid, 'Rounding_Profiles')
    if request.include_selection_attempts and strict_source is not None:
        queue(strict_source.selection_attempts_grid, 'Selection_Attempts')
    if request.include_derivations:
        queue(result.derivations_grid, 'Derivations')
    if request.include_constraints:
        queue(result.constraints_grid, 'Constraints')
    if request.include_solver_runs:
        queue(result.solver_runs_grid, 'SolverRuns')
    if request.include_metadata_sheet:
        queue(result.audit_grid, 'Audit')
        if strict_source is not None:
            queue(pd.DataFrame([asdict(strict_source.summary)]), 'Parameters')
    for position, pivot_request in enumerate(request.pivots, start=1):
        pivot = build_sors_pivot(result, pivot_request)
        selector = pivot.selected_region_name if pivot.orientation == 'REGION_TO_CLASSES' else pivot.selected_class_code
        queue(pivot.table, f'Pivot_{position}_{selector}')

    workbook = xlsxwriter.Workbook(output, {'constant_memory': True})
    header_format = workbook.add_format(
        {'bold': True, 'bg_color': '#D9EAF7', 'border': 1}
    )
    closed = False
    gc_was_enabled = gc.isenabled()
    if gc_was_enabled:
        gc.disable()
    try:
        for sheet, frame in frames:
            _write_frame(workbook, frame, sheet, header_format)
        with _XLSXWRITER_ZIP_LOCK:
            original_zip_file = xlsxwriter_workbook.ZipFile
            try:
                xlsxwriter_workbook.ZipFile = _FastZipFile
                workbook.close()
                closed = True
            finally:
                xlsxwriter_workbook.ZipFile = original_zip_file
    finally:
        if not closed:
            workbook.close()
        if gc_was_enabled:
            gc.enable()

    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    sheets = tuple(sheet for sheet, _ in frames)
    return SorsWorkbookResult(
        output_path=output,
        sheet_names=sheets,
        sheet_count=len(sheets),
        file_size=output.stat().st_size,
        sha256=digest,
    )
