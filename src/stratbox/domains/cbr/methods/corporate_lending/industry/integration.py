"""Operation admission and evidence for independent industry flakes."""
from dataclasses import replace
from datetime import date
from stratbox.core.execution import Completion, OperationFailure
from stratbox.core.operations.tables import seal_stream, use_tables
from stratbox.domains.cbr.methods.corporate_lending.industry.snapshot_operations import validate_value
from stratbox.domains.cbr.integration.corporate_lending.industry.integration import assemble_flakes

def integrate(request, *, family, definition, types, normalize_geography, result_factory, invocation=None):

    def work(req, invocation):
        from stratbox.core.runtime.dependencies import require_extra
        require_extra('pandas', 'dataframe')
        invocation.stage('admit_flakes')
        if not req.flakes:
            raise OperationFailure('request.source_selection_empty')
        original = []
        selection = req.flakes[0].selection
        for index, flake in enumerate(req.flakes):
            invocation.check_cancelled()
            try:
                validate_value(flake, family, 'flake', types)
            except (ValueError, TypeError, KeyError):
                raise OperationFailure('industry.flake_invalid') from None
            if any((issue.severity == 'error' for issue in flake.validation_issues)):
                raise OperationFailure('source.validation_failed')
            if flake.selection != selection or flake.source_validation_scope != 'full':
                raise OperationFailure('source.selection_incompatible')
            if flake.geography_reference_version != 'cbr-industry-geography-2026-06-01':
                raise OperationFailure('source.geography_reference_unsupported')
            if flake.evidence is None:
                raise OperationFailure('input.snapshot_required')
            frame, = use_tables(invocation, (('stream', flake.df_stream),), receipt=flake.evidence, role=f'flake_{index}')
            original.append(replace(flake, df_stream=frame))
        dates = tuple(sorted((item.report_date for item in original)))
        if len(set(dates)) != len(dates):
            raise OperationFailure('request.duplicate_release')
        expected = dates if req.expected_report_dates is None else req.expected_report_dates
        try:
            if not isinstance(expected, tuple) or not expected or len(set(expected)) != len(expected) or any((date.fromisoformat(day).isoformat() != day for day in expected)) or (not set(dates) <= set(expected)):
                raise ValueError
        except (TypeError, ValueError):
            raise OperationFailure('request.expected_releases_invalid') from None
        invocation.stage('integrate')
        result, parameters = assemble_flakes(original, expected, family=family, normalize_geography=normalize_geography, result_factory=result_factory)
        result = seal_stream(invocation, result, parameters=parameters)
        if parameters['missing']:
            return Completion(result, 'partial', 'source.selection_incomplete')
        return result
    return work(request, invocation)
