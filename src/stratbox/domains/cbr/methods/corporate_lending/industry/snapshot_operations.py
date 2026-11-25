"""Runner integration for portable industry results at each meaningful stage."""
from __future__ import annotations
from stratbox.core.execution import OperationFailure
from stratbox.core.operations.tables import use_stream, use_tables
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.domains.cbr.operations.corporate_lending.industry.operation_helpers import _pivot_metadata
from stratbox.domains.cbr.operations.corporate_lending.industry.operation_helpers import _pivot_tables
from stratbox.domains.cbr.tables.corporate_lending.industry.snapshots import value_from_snapshot
from stratbox.domains.cbr.tables.corporate_lending.industry.snapshots import value_snapshot

def validate_value(value, family, kind, types):
    if type(value) is not types[kind]:
        raise ValueError('industry.snapshot_value_mismatch')
    if kind in {'flake', 'stream', 'calculation'}:
        frame = value.df_stream
        required = {'series_code', 'report_date', 'measure', 'unit', 'region_code', 'industry_code', 'value'}
        if not required <= set(frame.columns):
            raise ValueError('industry.snapshot_stream_invalid')
        series = '01_05_A_Debt_corp' if family == '0105a' else '01_04_A_New_loans_corp'
        if frame.empty or set(frame['series_code'].dropna().astype(str)) != {series}:
            raise ValueError('industry.snapshot_series_mismatch')
        dates = tuple(sorted(frame['report_date'].dropna().astype(str).unique()))
        if kind == 'flake':
            if dates != (value.report_date,) or len(frame) != value.rows_stream:
                raise ValueError('industry.snapshot_period_mismatch')
            for column, expected in (('source_id', value.source_id), ('source_sha256', value.source_sha256)):
                if expected is not None and set(frame[column].dropna().astype(str)) != {expected}:
                    raise ValueError('industry.snapshot_source_mismatch')
        if kind == 'stream' and (dates != tuple(sorted(value.dates)) or len(frame) != value.rows_stream):
            raise ValueError('industry.snapshot_period_mismatch')
        if family == '0104a':
            from stratbox.domains.cbr.integration.corporate_lending.industry.integration import reference_period
            if 'reference_period' not in frame or any((month != reference_period(day) for day, month in frame[['report_date', 'reference_period']].drop_duplicates().itertuples(index=False, name=None))):
                raise ValueError('industry.snapshot_period_mismatch')
            if kind == 'flake' and value.reference_period != reference_period(value.report_date):
                raise ValueError('industry.snapshot_period_mismatch')
            if kind == 'stream' and tuple(value.reference_periods) != tuple((reference_period(day) for day in value.dates)):
                raise ValueError('industry.snapshot_period_mismatch')
        if kind == 'calculation' and (value.rows_added != len(value.df_apk) or not value.df_apk['industry_code'].eq(value.industry.code).all()):
            raise ValueError('industry.snapshot_calculation_invalid')
    if kind == 'view' and (value.table_count != len(value.tables) or any((table.rows != len(table.df_table) or not 0 < table.data_columns <= len(table.df_table.columns) for table in value.tables))):
        raise ValueError('industry.snapshot_view_invalid')

def _use(value, family, kind, invocation, types):
    validate_value(value, family, kind, types)
    if kind == 'view':
        use_tables(invocation, _pivot_tables(value), receipt=value.evidence, role='pivots', metadata=_pivot_metadata(value))
    else:
        use_stream(invocation, value)

def build_snapshot(request, *, family, kind, definition, types, invocation=None):

    def work(req, invocation):
        from stratbox.core.runtime.dependencies import require_extra
        require_extra('pandas', 'dataframe')
        invocation.stage('encode_snapshot')
        try:
            _use(req.value, family, kind, invocation, types)
            result = value_snapshot(req.value, family=family, kind=kind, dataset_id=req.dataset_id, version_id=req.version_id, inputs=tuple(invocation.used_inputs), types=types, checkpoint=invocation.check_cancelled)
            for name, table in result.tables:
                invocation.account_output(table.identity, key=f'snapshot:{name}')
            invocation.account_output(result.identity, key='snapshot:manifest')
            invocation.record(result.identity, parameters={'dataset_id': req.dataset_id, 'version_id': req.version_id, 'profile': result.manifest.contract.schema_id})
            return result
        except (ValueError, TypeError, KeyError, AttributeError, UnicodeError, RecursionError) as exc:
            raise OperationFailure(str(exc) if str(exc).startswith(('industry.', 'dataframe.', 'dataset.', 'material.')) else 'industry.snapshot_invalid') from None
    return work(request, invocation)

def read_snapshot(request, *, family, kind, definition, types, invocation=None):

    def work(req, invocation):
        from stratbox.core.runtime.dependencies import require_extra
        require_extra('pandas', 'dataframe')
        invocation.stage('decode_snapshot')
        try:
            invocation.budget.charge('input_bytes', req.snapshot.identity.size + sum((table.identity.size for _, table in req.snapshot.tables)))
            value = value_from_snapshot(req.snapshot, family=family, kind=kind, types=types, checkpoint=invocation.check_cancelled)
            invocation.use(UsedInputReceipt('snapshot', req.snapshot.identity, 'application/vnd.stratbox.dataset+json', 'inline', req.snapshot.manifest.dataset_id))
            _use(value, family, kind, invocation, types)
            if value.evidence is None:
                raise OperationFailure('input.snapshot_required')
            invocation.record(value.evidence.output, parameters={'profile': req.snapshot.manifest.contract.schema_id})
            return value
        except (ValueError, TypeError, KeyError, AttributeError, UnicodeError, RecursionError) as exc:
            raise OperationFailure(str(exc) if str(exc).startswith(('industry.', 'dataframe.', 'dataset.', 'material.')) else 'industry.snapshot_invalid') from None
    return work(request, invocation)
