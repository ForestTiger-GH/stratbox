from __future__ import annotations

from dataclasses import replace

import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.contracts import SorsSourceBundle


class SorsSourceValidationError(ValueError):
    def __init__(self, validation_grid: pd.DataFrame):
        failures = validation_grid[validation_grid['status'].eq('ERROR')]
        preview = '; '.join(failures['message'].astype(str).head(5))
        super().__init__(f'SORS source validation failed: {preview}')
        self.validation_grid = validation_grid


def _overlap(lower_a: float, upper_a: float, lower_b: float, upper_b: float) -> bool:
    return max(lower_a, lower_b) <= min(upper_a, upper_b) + 1e-8


def _record(
    rows: list[dict[str, object]],
    *,
    check_id: str,
    check_group: str,
    status: str,
    message: str,
    severity: str | None = None,
    source_series: str | None = None,
    geography: str | None = None,
    activity: str | None = None,
    metric: str | None = None,
    expected: object = None,
    actual: object = None,
    difference: object = None,
    observation_ids: object = None,
) -> None:
    rows.append(
        {
            'check_id': check_id,
            'check_group': check_group,
            'severity': severity or ('ERROR' if status == 'ERROR' else status),
            'status': status,
            'source_series': source_series,
            'observation_ids': observation_ids,
            'geography': geography,
            'activity': activity,
            'metric': metric,
            'expected': expected,
            'actual': actual,
            'difference': difference,
            'message': message,
        }
    )


def _validate_structure(bundle: SorsSourceBundle, rows: list[dict[str, object]]) -> None:
    expected_rows = {
        '01_05_A': 14976,
        '01_02_A': 156,
        '01_02_C': 486,
        '01_03_C': 256,
    }
    actual = bundle.source_manifest_grid.set_index('source_series')['rows'].astype(int).to_dict()
    for series, expected in expected_rows.items():
        got = actual.get(series)
        _record(
            rows,
            check_id=f'structure:{series}:rows',
            check_group='STRUCTURE',
            status='PASS' if got == expected else 'ERROR',
            source_series=series,
            expected=expected,
            actual=got,
            message=f'{series}: expected {expected} rows, got {got}',
        )
    if not bundle.regional_totals_history_grid.empty:
        got = len(bundle.regional_totals_history_grid)
        _record(
            rows,
            check_id='structure:01_05_D:rows',
            check_group='STRUCTURE',
            status='PASS' if got == 576 else 'ERROR',
            source_series='01_05_D',
            expected=576,
            actual=got,
            message=f'01_05_D: expected 576 rows, got {got}',
        )
    for name, got, expected in (
        ('atomic_regions', len(bundle.atomic_regions_grid), 85),
        ('geography_nodes', len(bundle.geography_nodes_grid), 96),
        ('okved2_classes', len(bundle.okved2_classes_grid), 88),
    ):
        _record(
            rows,
            check_id=f'structure:{name}',
            check_group='STRUCTURE',
            status='PASS' if got == expected else 'ERROR',
            expected=expected,
            actual=got,
            message=f'{name}: expected {expected}, got {got}',
        )
    dates = sorted(set(bundle.source_grid['as_of_date'].dropna().astype(str)))
    _record(
        rows,
        check_id='structure:common_date',
        check_group='STRUCTURE',
        status='PASS' if len(dates) == 1 else 'ERROR',
        expected='one common date',
        actual=dates,
        message=f'SORS sources contain reporting dates {dates}',
    )


def _validate_duplicates(bundle: SorsSourceBundle, rows: list[dict[str, object]]) -> None:
    frames = (
        (
            bundle.regional_traditional_grid,
            ['as_of_date', 'geography_node_id', 'activity_code', 'metric'],
            '01_05_A',
        ),
        (
            bundle.national_traditional_grid,
            ['as_of_date', 'activity_code', 'metric'],
            '01_02_A',
        ),
        (
            bundle.national_okved2_grid,
            ['as_of_date', 'activity_code', 'metric'],
            '01_02_C',
        ),
        (
            bundle.federal_district_okved2_grid,
            ['as_of_date', 'geography_node_id', 'activity_code', 'metric'],
            '01_03_C',
        ),
    )
    for frame, keys, series in frames:
        count = int(frame.duplicated(keys, keep=False).sum())
        _record(
            rows,
            check_id=f'duplicates:{series}',
            check_group='UNIQUENESS',
            status='PASS' if count == 0 else 'ERROR',
            source_series=series,
            expected=0,
            actual=count,
            message=f'{series} contains {count} duplicate observations',
        )


def _validate_metric_arithmetic(
    frame: pd.DataFrame,
    keys: list[str],
    series: str,
    rows: list[dict[str, object]],
) -> None:
    lower = frame.pivot(index=keys, columns='metric', values='published_lower')
    upper = frame.pivot(index=keys, columns='metric', values='published_upper')
    required = {
        'debt_rub', 'debt_fx', 'debt_total',
        'overdue_rub', 'overdue_fx', 'overdue_total',
    }
    missing = sorted(required - set(lower.columns))
    if missing:
        failures = len(lower)
        overdue_failures = len(lower)
    else:
        debt_overlap = (
            lower['debt_rub'] + lower['debt_fx']
            <= upper['debt_total'] + 1e-8
        ) & (
            lower['debt_total']
            <= upper['debt_rub'] + upper['debt_fx'] + 1e-8
        )
        overdue_overlap = (
            lower['overdue_rub'] + lower['overdue_fx']
            <= upper['overdue_total'] + 1e-8
        ) & (
            lower['overdue_total']
            <= upper['overdue_rub'] + upper['overdue_fx'] + 1e-8
        )
        failures = int((~debt_overlap).sum() + (~overdue_overlap).sum())
        overdue_ok = (
            (lower['overdue_rub'] <= upper['debt_rub'] + 1e-8)
            & (lower['overdue_fx'] <= upper['debt_fx'] + 1e-8)
            & (lower['overdue_total'] <= upper['debt_total'] + 1e-8)
        )
        overdue_failures = int((~overdue_ok).sum())
    _record(
        rows,
        check_id=f'arithmetic:{series}:currency_totals',
        check_group='ARITHMETIC',
        status='PASS' if failures == 0 else 'ERROR',
        source_series=series,
        expected=0,
        actual=failures,
        message=f'{series}: {failures} currency-total interval conflicts',
    )
    _record(
        rows,
        check_id=f'arithmetic:{series}:overdue_le_debt',
        check_group='ARITHMETIC',
        status='PASS' if overdue_failures == 0 else 'ERROR',
        source_series=series,
        expected=0,
        actual=overdue_failures,
        message=f'{series}: {overdue_failures} overdue/debt conflicts',
    )


def _validate_cross_source_totals(bundle: SorsSourceBundle, rows: list[dict[str, object]]) -> None:
    regional = bundle.regional_traditional_grid
    country_node = bundle.geography_nodes_grid.loc[
        bundle.geography_nodes_grid['geography_kind'].eq('country_total'),
        'geography_node_id',
    ].iloc[0]
    a = regional[
        regional['geography_node_id'].astype(str).eq(str(country_node))
        & regional['activity_code'].astype(str).eq('total')
    ].set_index('metric')
    b = bundle.national_traditional_grid[
        bundle.national_traditional_grid['activity_code'].astype(str).eq('total')
    ].set_index('metric')
    for metric in sorted(set(a.index) & set(b.index)):
        left = a.loc[metric]
        right = b.loc[metric]
        compatible = _overlap(
            float(left.published_lower),
            float(left.published_upper),
            float(right.published_lower),
            float(right.published_upper),
        )
        _record(
            rows,
            check_id=f'cross:01_05_A:01_02_A:{metric}',
            check_group='CROSS_SOURCE',
            status='PASS' if compatible else 'ERROR',
            source_series='01_05_A|01_02_A',
            metric=metric,
            expected=float(left.value),
            actual=float(right.value),
            difference=float(right.value) - float(left.value),
            observation_ids=(left.observation_id, right.observation_id),
            message=f'National traditional total comparison for {metric}',
        )
    history = bundle.regional_totals_history_grid
    if history.empty:
        return
    current = regional[regional['activity_code'].astype(str).eq('total')]
    merged = current.merge(
        history,
        on=['as_of_date', 'geography_node_id', 'metric'],
        suffixes=('_a', '_d'),
        validate='one_to_one',
    )
    mismatches = int((merged['value_a'].astype(float) != merged['value_d'].astype(float)).sum())
    _record(
        rows,
        check_id='cross:01_05_A:01_05_D',
        check_group='CROSS_SOURCE',
        status='PASS' if mismatches == 0 else 'ERROR',
        source_series='01_05_A|01_05_D',
        expected=0,
        actual=mismatches,
        message=f'01_05_A and 01_05_D regional totals differ in {mismatches} cells',
    )


def validate_source_bundle(
    bundle: SorsSourceBundle,
    *,
    raise_on_error: bool = True,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    _validate_structure(bundle, rows)
    _validate_duplicates(bundle, rows)
    _validate_metric_arithmetic(
        bundle.regional_traditional_grid,
        ['geography_node_id', 'activity_code'],
        '01_05_A',
        rows,
    )
    _validate_metric_arithmetic(
        bundle.national_traditional_grid,
        ['activity_code'],
        '01_02_A',
        rows,
    )
    _validate_metric_arithmetic(
        bundle.national_okved2_grid,
        ['activity_code'],
        '01_02_C',
        rows,
    )
    _validate_cross_source_totals(bundle, rows)
    result = pd.DataFrame(rows)
    if raise_on_error and result['status'].eq('ERROR').any():
        raise SorsSourceValidationError(result)
    return result


def attach_validation(bundle: SorsSourceBundle) -> SorsSourceBundle:
    validation = validate_source_bundle(bundle, raise_on_error=False)
    return replace(bundle, validation_grid=validation)
