from __future__ import annotations

import hashlib

import pandas as pd

from stratbox.shared.evidence import SourcePayload

from stratbox.domains.cbr.analytics.corporate_lending.sors.metrics import source_metric
from stratbox.domains.cbr.analytics.corporate_lending.sors.publication import RoundingPolicy
from stratbox.domains.cbr.analytics.corporate_lending.sors.schema import normalize_text



def source_dataset(value, publisher_code, *, period=None):
    from stratbox.domains.cbr.tables.corporate_lending.observations import CorporateSourceDataset, PROFILES, extract_observations
    from stratbox.domains.cbr.tables.corporate_lending.observation_snapshots import validate
    from stratbox.domains.cbr.tables.statistics.contracts import WorkbookFlake
    if isinstance(value, CorporateSourceDataset):
        validate(value)
        result = value
    else:
        if isinstance(value, SourcePayload):
            from stratbox.domains.cbr.tables.statistics.extraction import extract_workbook_value
            from stratbox.domains.cbr.publications.contracts import IdentifiedOriginal
            from stratbox.shared.source_publications import SourceAssetIdentity
            from stratbox.shared.evidence import UsedInputReceipt
            profile = next((item for item in PROFILES if item.publisher_code == publisher_code), None)
            if profile is None:
                raise ValueError("sors.source_profile_unsupported")
            # The caller supplied bytes without an independently qualified issue.
            # This content key asserts no publication or observation date.
            asset = SourceAssetIdentity(profile.series_id, "supplied." + value.identity.sha256, "main")
            value = extract_workbook_value(IdentifiedOriginal(asset, value, "xlsx",
                lineage=(UsedInputReceipt.for_payload(value, "original"),)))
        if not isinstance(value, WorkbookFlake):
            raise ValueError("sors.source_flake_required")
        result = extract_observations(value, periods=(period,) if period is not None else None)
    profile = next((item for item in PROFILES if item.publisher_code == publisher_code), None)
    if profile is None or result.series_id != profile.series_id:
        raise ValueError("sors.source_series_mismatch")
    if result.asset_id != "main":
        raise ValueError("sors.source_asset_unsupported")
    return result


def source_records(value, as_of_date, publisher_code):
    dataset = source_dataset(value, publisher_code, period=as_of_date)
    frame = dataset.observations.loc[dataset.observations["period"].eq(as_of_date)
        & dataset.observations["measure"].isin(("debt", "overdue"))].copy()
    if frame.empty:
        raise ValueError("sors.source_period_missing")
    if not frame["status"].isin(("numeric", "numeric_text", "formula_cached")).all():
        raise ValueError("sors.source_observation_missing_or_unresolved")
    actual_name = next((item.source_id for item in dataset.lineage if item.source_id), dataset.series_id)
    out = frame.rename(columns={"period": "as_of_date", "sheet": "source_sheet", "row": "source_row", "column": "source_column"})
    out["source_series"] = publisher_code
    out["source_file_actual"] = actual_name
    out["source_file_logical"] = dataset.series_id
    out["source_sha256"] = dataset.source_identity.sha256
    out["source_value"] = out["value"]
    # Solver arithmetic uses floating point; the exact reported value and lexical
    # cell evidence remain separate columns and in the reusable source dataset.
    out["value"] = out["value"].map(float)
    return out


def stable_observation_id(
    source_series: str,
    source_sheet: object,
    source_row: object,
    source_column: object,
    as_of_date: str,
) -> str:
    raw = '|'.join(
        map(str, (source_series, source_sheet, source_row, source_column, as_of_date))
    )
    digest = hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]
    return f'{source_series}:{digest}'


def canonicalize_observations(
    frame: pd.DataFrame,
    policy: RoundingPolicy,
    *,
    source_role: str,
) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    out = frame.copy()
    intervals = out['value'].astype(float).map(policy.interval)
    out['published_lower'] = [item.lower for item in intervals]
    out['published_upper'] = [item.upper for item in intervals]
    out['published_lower_attained'] = [item.lower_attained for item in intervals]
    out['published_upper_attained'] = [item.upper_attained for item in intervals]
    out['metric'] = [
        source_metric(measure, currency)
        for measure, currency in zip(out['measure'], out['currency'], strict=True)
    ]
    out['unit'] = 'million_rubles'
    out['source_role'] = source_role
    out['record_origin'] = 'PUBLISHED'
    out['observation_id'] = [
        stable_observation_id(
            str(row.source_series),
            row.source_sheet,
            row.source_row,
            row.source_column,
            str(row.as_of_date),
        )
        for row in out.itertuples(index=False)
    ]
    return out


def source_manifest_record(
    source_series: str,
    source: SourcePayload,
    rows: int,
    *,
    required: bool,
    role: str,
) -> dict[str, object]:
    from stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.dependencies import original_input
    receipt = original_input(source, source_series)
    return {
        'source_series': source_series,
        'source_role': role,
        'required': bool(required),
        'source_file_actual': receipt.source_id or source_series,
        'sha256': receipt.identity.sha256,
        'size_bytes': receipt.identity.size,
        'rows': int(rows),
    }
