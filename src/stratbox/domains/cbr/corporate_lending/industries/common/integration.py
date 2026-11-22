"""Integrate validated source-local flakes without rereading source workbooks."""
from dataclasses import replace
from datetime import date

from stratbox.core.execution import Completion, OperationFailure, run
from stratbox.core.operations.tables import seal_stream, use_tables

from .snapshot_operations import validate_value


def reference_period(day):
    parsed = date.fromisoformat(day)
    if parsed.day != 1:
        raise ValueError("industry.release_date_invalid")
    return f"{parsed.year - (parsed.month == 1):04d}-{parsed.month - 1 if parsed.month > 1 else 12:02d}"


def assemble_flakes(original, expected, *, family, normalize_geography, result_factory,
                    failures=(), stop_reason=None):
    """Build the same history from independent or internally completed flakes."""
    from .streams import concat_industry_streams

    try:
        files = normalize_geography(tuple(original))
    except ValueError:
        raise OperationFailure("source.geography_incompatible") from None
    frame = concat_industry_streams(item.df_stream for item in files).sort_values(
        ["report_date", "sheet_order", "region_order", "industry_order"], kind="stable").reset_index(drop=True)
    latest = max(files, key=lambda item: item.report_date)
    dates = tuple(sorted(item.report_date for item in original))
    selection = original[0].selection
    missing = tuple(sorted(set(expected) - set(dates)))
    shared = dict(failures=failures, parsed_files=tuple(sorted(original, key=lambda item: item.report_date)),
        validation_issues=tuple(issue for item in files for issue in item.validation_issues),
        df_stream=frame, dates=dates, latest_report_date=latest.report_date,
        latest_discovered_report_date=max(expected), region_normalization_date=latest.report_date,
        region_normalization_is_latest_discovered=latest.report_date == max(expected),
        regions=latest.regions, industries=latest.industries, rows_stream=len(frame),
        stop_reason=stop_reason or ("source.selection_incomplete" if missing else None), selection=selection,
        geography_reference_version=latest.geography_reference_version)
    parameters = {
        "quantity_kind": "stock" if family == "0105a" else "flow",
        "period_basis": "as_of" if family == "0105a" else "reference_month", "unit": "million_rubles",
        "selected": tuple(sorted(expected)), "accepted": dates, "missing": missing,
        "industries": selection.industry_codes, "revision_policy": "unique_release",
        "geography_reference": latest.geography_reference_version,
    }
    return result_factory(tuple(original), shared), parameters


def integrate(request, *, family, definition, types, normalize_geography, result_factory, context=None):
    def work(req, invocation):
        from stratbox.core.runtime.dependencies import require_extra
        require_extra("pandas", "dataframe")
        invocation.stage("admit_flakes")
        if not req.flakes:
            raise OperationFailure("request.source_selection_empty")
        original = []
        selection = req.flakes[0].selection
        for index, flake in enumerate(req.flakes):
            invocation.check_cancelled()
            try:
                validate_value(flake, family, "flake", types)
            except (ValueError, TypeError, KeyError):
                raise OperationFailure("industry.flake_invalid") from None
            if any(issue.severity == "error" for issue in flake.validation_issues):
                raise OperationFailure("source.validation_failed")
            if flake.selection != selection or flake.source_validation_scope != "full":
                raise OperationFailure("source.selection_incompatible")
            if flake.geography_reference_version != "cbr-industry-geography-2026-06-01":
                raise OperationFailure("source.geography_reference_unsupported")
            if flake.evidence is None:
                raise OperationFailure("input.snapshot_required")
            frame, = use_tables(invocation, (("stream", flake.df_stream),), receipt=flake.evidence, role=f"flake_{index}")
            original.append(replace(flake, df_stream=frame))
        dates = tuple(sorted(item.report_date for item in original))
        if len(set(dates)) != len(dates):
            raise OperationFailure("request.duplicate_release")
        expected = dates if req.expected_report_dates is None else req.expected_report_dates
        try:
            if (not isinstance(expected, tuple) or not expected or len(set(expected)) != len(expected)
                    or any(date.fromisoformat(day).isoformat() != day for day in expected)
                    or not set(dates) <= set(expected)):
                raise ValueError
        except (TypeError, ValueError):
            raise OperationFailure("request.expected_releases_invalid") from None
        invocation.stage("integrate")
        result, parameters = assemble_flakes(original, expected, family=family,
            normalize_geography=normalize_geography, result_factory=result_factory)
        result = seal_stream(invocation, result, parameters=parameters)
        if parameters["missing"]:
            return Completion(result, "partial", "source.selection_incomplete")
        return result
    return run(definition, request, work, context=context)
