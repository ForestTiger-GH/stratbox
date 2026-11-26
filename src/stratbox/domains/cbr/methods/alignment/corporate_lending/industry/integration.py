"""Integrate validated source-local flakes without rereading source workbooks."""
from datetime import date

from stratbox.core.execution import OperationFailure



def reference_period(day):
    parsed = date.fromisoformat(day)
    if parsed.day != 1:
        raise ValueError("industry.release_date_invalid")
    return f"{parsed.year - (parsed.month == 1):04d}-{parsed.month - 1 if parsed.month > 1 else 12:02d}"


def assemble_flakes(original, expected, *, family, normalize_geography, result_factory,
                    failures=(), stop_reason=None):
    """Build the same history from independent or internally completed flakes."""
    from stratbox.domains.cbr.methods.tables.corporate_lending.industry.streams import concat_industry_streams

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
        geography_reference=latest.geography_reference)
    parameters = {
        "quantity_kind": "stock" if family == "0105a" else "flow",
        "period_basis": "as_of" if family == "0105a" else "reference_month", "unit": "million_rubles",
        "selected": tuple(sorted(expected)), "accepted": dates, "missing": missing,
        "industries": selection.industry_codes, "revision_policy": "unique_release",
        "geography_reference": latest.geography_reference,
    }
    return result_factory(tuple(original), shared), parameters
