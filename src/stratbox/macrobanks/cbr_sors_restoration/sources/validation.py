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


def _record(rows: list[dict[str, object]], *, check_id: str, check_group: str,
            status: str, message: str, severity: str | None = None,
            source_series: str | None = None, geography: str | None = None,
            activity: str | None = None, metric: str | None = None,
            expected: object = None, actual: object = None,
            difference: object = None, observation_ids: object = None) -> None:
    rows.append({
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
    })


def _validate_structure(bundle: SorsSourceBundle, rows: list[dict[str, object]]) -> None:
    expected_rows = {
        '01_05_A': 14976,
        '01_02_A': 156,
        '01_02_C': 486,
        '01_03_C': 256,
        '01_11': 12,
        '01_11_F': 486,
        '01_11_I': 486,
        '01_12_A': 256,
        '01_13_F': 576,
        '01_13_I': 576,
    }
    actual = bundle.source_manifest_grid.set_index('source_series')['rows'].astype(int).to_dict()
    for series, expected in expected_rows.items():
        got = actual.get(series)
        _record(rows, check_id=f'structure:{series}:rows', check_group='STRUCTURE',
                status='PASS' if got == expected else 'ERROR', source_series=series,
                expected=expected, actual=got,
                message=f'{series}: expected {expected} rows, got {got}')
    if not bundle.regional_totals_history_grid.empty:
        got = len(bundle.regional_totals_history_grid)
        _record(rows, check_id='structure:01_05_D:rows', check_group='STRUCTURE',
                status='PASS' if got == 576 else 'ERROR', source_series='01_05_D',
                expected=576, actual=got,
                message=f'01_05_D: expected 576 rows, got {got}')
    for name, got, expected in (
        ('atomic_regions', len(bundle.atomic_regions_grid), 85),
        ('geography_nodes', len(bundle.geography_nodes_grid), 96),
        ('okved2_classes', len(bundle.okved2_classes_grid), 88),
    ):
        _record(rows, check_id=f'structure:{name}', check_group='STRUCTURE',
                status='PASS' if got == expected else 'ERROR', expected=expected,
                actual=got, message=f'{name}: expected {expected}, got {got}')
    dates = sorted(set(bundle.source_grid['as_of_date'].dropna().astype(str)))
    scopes = sorted(set(bundle.source_grid['portfolio_scope'].dropna().astype(str)))
    _record(rows, check_id='structure:common_date', check_group='STRUCTURE',
            status='PASS' if len(dates) == 1 else 'ERROR', expected='one common date',
            actual=dates, message=f'SORS sources contain reporting dates {dates}')
    _record(rows, check_id='structure:portfolio_scopes', check_group='STRUCTURE',
            status='PASS' if set(scopes) == {'CORPORATE_TOTAL', 'SME', 'SME_IE'} else 'ERROR',
            expected=('CORPORATE_TOTAL', 'SME', 'SME_IE'), actual=scopes,
            message=f'SORS source bundle portfolio scopes are {scopes}')


def _validate_duplicates(bundle: SorsSourceBundle, rows: list[dict[str, object]]) -> None:
    frames = (
        (bundle.regional_traditional_grid, ['as_of_date','geography_node_id','activity_code','metric'], '01_05_A'),
        (bundle.national_traditional_grid, ['as_of_date','activity_code','metric'], '01_02_A'),
        (bundle.national_okved2_grid, ['as_of_date','activity_code','metric'], '01_02_C'),
        (bundle.federal_district_okved2_grid, ['as_of_date','geography_node_id','activity_code','metric'], '01_03_C'),
        (bundle.sme_national_totals_grid, ['as_of_date','portfolio_scope','activity_code','metric'], '01_11'),
        (bundle.sme_national_okved2_grid, ['as_of_date','activity_code','metric'], '01_11_F'),
        (bundle.sme_ie_national_okved2_grid, ['as_of_date','activity_code','metric'], '01_11_I'),
        (bundle.sme_federal_district_okved2_grid, ['as_of_date','geography_node_id','activity_code','metric'], '01_12_A'),
        (bundle.sme_regional_totals_grid, ['as_of_date','geography_node_id','activity_code','metric'], '01_13_F'),
        (bundle.sme_ie_regional_totals_grid, ['as_of_date','geography_node_id','activity_code','metric'], '01_13_I'),
    )
    for frame, keys, series in frames:
        count = int(frame.duplicated(keys, keep=False).sum())
        _record(rows, check_id=f'duplicates:{series}', check_group='UNIQUENESS',
                status='PASS' if count == 0 else 'ERROR', source_series=series,
                expected=0, actual=count,
                message=f'{series} contains {count} duplicate observations')


def _validate_metric_arithmetic(frame: pd.DataFrame, keys: list[str], series: str,
                                rows: list[dict[str, object]]) -> None:
    lower = frame.pivot(index=keys, columns='metric', values='published_lower')
    upper = frame.pivot(index=keys, columns='metric', values='published_upper')
    required = {'debt_rub','debt_fx','debt_total','overdue_rub','overdue_fx','overdue_total'}
    missing = sorted(required - set(lower.columns))
    if missing:
        failures = overdue_failures = len(lower)
    else:
        debt_overlap = (
            (lower['debt_rub'] + lower['debt_fx'] <= upper['debt_total'] + 1e-8)
            & (lower['debt_total'] <= upper['debt_rub'] + upper['debt_fx'] + 1e-8)
        )
        overdue_overlap = (
            (lower['overdue_rub'] + lower['overdue_fx'] <= upper['overdue_total'] + 1e-8)
            & (lower['overdue_total'] <= upper['overdue_rub'] + upper['overdue_fx'] + 1e-8)
        )
        failures = int((~debt_overlap).sum() + (~overdue_overlap).sum())
        overdue_ok = (
            (lower['overdue_rub'] <= upper['debt_rub'] + 1e-8)
            & (lower['overdue_fx'] <= upper['debt_fx'] + 1e-8)
            & (lower['overdue_total'] <= upper['debt_total'] + 1e-8)
        )
        overdue_failures = int((~overdue_ok).sum())
    _record(rows, check_id=f'arithmetic:{series}:currency_totals', check_group='ARITHMETIC',
            status='PASS' if failures == 0 else 'ERROR', source_series=series,
            expected=0, actual=failures,
            message=f'{series}: {failures} currency-total interval conflicts')
    _record(rows, check_id=f'arithmetic:{series}:overdue_le_debt', check_group='ARITHMETIC',
            status='PASS' if overdue_failures == 0 else 'ERROR', source_series=series,
            expected=0, actual=overdue_failures,
            message=f'{series}: {overdue_failures} overdue/debt conflicts')


def _compare_same_metric_frames(left: pd.DataFrame, right: pd.DataFrame, keys: list[str],
                                series: str, rows: list[dict[str, object]]) -> None:
    merged = left.merge(right, on=keys, suffixes=('_left','_right'), how='inner')
    incompatible = ~merged.apply(
        lambda r: _overlap(float(r.published_lower_left), float(r.published_upper_left),
                           float(r.published_lower_right), float(r.published_upper_right)),
        axis=1,
    )
    count = int(incompatible.sum())
    _record(rows, check_id=f'cross:{series}', check_group='CROSS_SOURCE',
            status='PASS' if count == 0 else 'ERROR', source_series=series,
            expected=0, actual=count,
            message=f'{series}: {count} incompatible duplicate aggregate intervals')


def _validate_cross_source_totals(bundle: SorsSourceBundle, rows: list[dict[str, object]]) -> None:
    regional = bundle.regional_traditional_grid
    country_node = str(bundle.geography_nodes_grid.loc[
        bundle.geography_nodes_grid['geography_kind'].eq('country_total'), 'geography_node_id'
    ].iloc[0])
    a = regional[
        regional['geography_node_id'].astype(str).eq(country_node)
        & regional['activity_code'].astype(str).eq('total')
    ].set_index('metric')
    b = bundle.national_traditional_grid[
        bundle.national_traditional_grid['activity_code'].astype(str).eq('total')
    ].set_index('metric')
    for metric in sorted(set(a.index) & set(b.index)):
        left, right = a.loc[metric], b.loc[metric]
        compatible = _overlap(float(left.published_lower), float(left.published_upper),
                              float(right.published_lower), float(right.published_upper))
        _record(rows, check_id=f'cross:01_05_A:01_02_A:{metric}', check_group='CROSS_SOURCE',
                status='PASS' if compatible else 'ERROR', source_series='01_05_A|01_02_A',
                metric=metric, expected=float(left.value), actual=float(right.value),
                difference=float(right.value)-float(left.value),
                observation_ids=(left.observation_id,right.observation_id),
                message=f'National traditional total comparison for {metric}')

    national_segments = bundle.sme_national_totals_grid[
        bundle.sme_national_totals_grid['activity_code'].astype(str).eq('total')
    ]
    for scope, regional_frame, series in (
        ('SME', bundle.sme_regional_totals_grid, '01_11|01_13_F'),
        ('SME_IE', bundle.sme_ie_regional_totals_grid, '01_11|01_13_I'),
    ):
        left = national_segments[national_segments['portfolio_scope'].eq(scope)]
        right = regional_frame[regional_frame['geography_node_id'].astype(str).eq(country_node)]
        _compare_same_metric_frames(left, right, ['metric'], series, rows)

    history = bundle.regional_totals_history_grid
    if not history.empty:
        current = regional[regional['activity_code'].astype(str).eq('total')]
        merged = current.merge(history, on=['as_of_date','geography_node_id','metric'],
                               suffixes=('_a','_d'), validate='one_to_one')
        mismatches = int((merged['value_a'].astype(float) != merged['value_d'].astype(float)).sum())
        _record(rows, check_id='cross:01_05_A:01_05_D', check_group='CROSS_SOURCE',
                status='PASS' if mismatches == 0 else 'ERROR', source_series='01_05_A|01_05_D',
                expected=0, actual=mismatches,
                message=f'01_05_A and 01_05_D regional totals differ in {mismatches} cells')


def _validate_scope_nesting(bundle: SorsSourceBundle, rows: list[dict[str, object]]) -> None:
    """Check that published intervals do not contradict SME_IE <= SME <= corporate.

    Independent rounding means representatives need not obey the inequality exactly;
    a contradiction exists only when the child's *lower* publication bound exceeds
    the parent's *upper* bound on the same support and metric.
    """
    comparisons = [
        (bundle.sme_ie_national_okved2_grid, bundle.sme_national_okved2_grid,
         ['activity_code','metric'], '01_11_I<=01_11_F'),
        (bundle.sme_ie_regional_totals_grid, bundle.sme_regional_totals_grid,
         ['geography_node_id','metric'], '01_13_I<=01_13_F'),
        (bundle.sme_national_okved2_grid, bundle.national_okved2_grid,
         ['activity_code','metric'], '01_11_F<=01_02_C'),
        (bundle.sme_federal_district_okved2_grid, bundle.federal_district_okved2_grid,
         ['geography_node_id','activity_code','metric'], '01_12_A<=01_03_C'),
    ]
    # Corporate 01_05_A is traditional by activity; only its TOTAL row is comparable
    # with segment regional totals.
    corp_regional = bundle.regional_traditional_grid[
        bundle.regional_traditional_grid['activity_code'].astype(str).eq('total')
    ]
    comparisons.extend([
        (bundle.sme_regional_totals_grid, corp_regional,
         ['geography_node_id','metric'], '01_13_F<=01_05_A_TOTAL'),
    ])
    national_total = bundle.sme_national_totals_grid
    sme_total = national_total[national_total['portfolio_scope'].eq('SME')]
    ie_total = national_total[national_total['portfolio_scope'].eq('SME_IE')]
    comparisons.append((ie_total, sme_total, ['metric'], '01_11_IE<=01_11_SME'))

    for child, parent, keys, label in comparisons:
        merged = child.merge(parent, on=keys, suffixes=('_child','_parent'), how='inner')
        failures = merged[
            merged['published_lower_child'].astype(float)
            > merged['published_upper_parent'].astype(float) + 1e-8
        ]
        _record(rows, check_id=f'nesting:{label}', check_group='PORTFOLIO_NESTING',
                status='PASS' if failures.empty else 'ERROR', source_series=label,
                expected=0, actual=len(failures),
                message=f'{label}: {len(failures)} publication-interval nesting conflicts')


def validate_source_bundle(bundle: SorsSourceBundle, *, raise_on_error: bool = True) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    _validate_structure(bundle, rows)
    _validate_duplicates(bundle, rows)
    for frame, keys, series in (
        (bundle.regional_traditional_grid, ['geography_node_id','activity_code'], '01_05_A'),
        (bundle.national_traditional_grid, ['activity_code'], '01_02_A'),
        (bundle.national_okved2_grid, ['activity_code'], '01_02_C'),
        (bundle.sme_national_totals_grid, ['portfolio_scope','activity_code'], '01_11'),
        (bundle.sme_national_okved2_grid, ['activity_code'], '01_11_F'),
        (bundle.sme_ie_national_okved2_grid, ['activity_code'], '01_11_I'),
        (bundle.sme_regional_totals_grid, ['geography_node_id','activity_code'], '01_13_F'),
        (bundle.sme_ie_regional_totals_grid, ['geography_node_id','activity_code'], '01_13_I'),
    ):
        _validate_metric_arithmetic(frame, keys, series, rows)
    _validate_cross_source_totals(bundle, rows)
    _validate_scope_nesting(bundle, rows)
    result = pd.DataFrame(rows)
    if raise_on_error and result['status'].eq('ERROR').any():
        raise SorsSourceValidationError(result)
    return result


def attach_validation(bundle: SorsSourceBundle) -> SorsSourceBundle:
    validation = validate_source_bundle(bundle, raise_on_error=False)
    return replace(bundle, validation_grid=validation)
