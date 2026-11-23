"""Cross-release geography normalization for the shared industry layout."""
from __future__ import annotations
from dataclasses import replace
from stratbox.domains.cbr.tables.corporate_lending.industry.contracts import IndustryRegionSpec as Cbr0105ADebtCorpRegionSpec
from stratbox.domains.cbr.tables.corporate_lending.debt.contracts import ParsedCbr0105ADebtCorpFile
from stratbox.domains.cbr.tables.corporate_lending.industry.geography import CBR_0105A_DEBT_CORP_REGION_LAYOUT

def _validate_layout_compatible(
    current: tuple[Cbr0105ADebtCorpRegionSpec, ...],
    *,
    current_date: str,
) -> None:
    if len(current) != len(CBR_0105A_DEBT_CORP_REGION_LAYOUT):
        raise ValueError(
            "01_05_A_Debt_corp geographic layout changed: "
            f"date={current_date}, rows={len(current)}, "
            f"expected={len(CBR_0105A_DEBT_CORP_REGION_LAYOUT)}"
        )
    for actual, reference in zip(current, CBR_0105A_DEBT_CORP_REGION_LAYOUT, strict=True):
        if (
            actual.code != reference.code
            or actual.order != reference.order
            or actual.region_kind != reference.region_kind
        ):
            raise ValueError(
                "01_05_A_Debt_corp geographic structure changed: "
                f"date={current_date}, order={actual.order}, code={actual.code!r}, "
                f"kind={actual.region_kind!r}"
            )


def normalize_cbr_0105a_debt_corp_regions_to_latest(
    parsed_files: list[ParsedCbr0105ADebtCorpFile]
    | tuple[ParsedCbr0105ADebtCorpFile, ...],
) -> tuple[ParsedCbr0105ADebtCorpFile, ...]:
    """Приводит подписи всех книг к конечному виду локального реестра серии.

    Исходная подпись конкретного файла сохраняется в ``region_source_name``.
    """
    if not parsed_files:
        return ()

    canonical_by_code = {
        item.code: item for item in CBR_0105A_DEBT_CORP_REGION_LAYOUT
    }
    normalized_files: list[ParsedCbr0105ADebtCorpFile] = []
    for parsed in parsed_files:
        _validate_layout_compatible(parsed.regions, current_date=parsed.report_date)
        updated_regions = tuple(
            replace(
                region,
                canonical_name=canonical_by_code[region.code].canonical_name,
                federal_district_name=canonical_by_code[region.code].federal_district_name,
            )
            for region in parsed.regions
        )
        canonical_names = {item.code: item.canonical_name for item in updated_regions}
        district_names = {item.code: item.federal_district_name for item in updated_regions}
        stream = parsed.df_stream.copy()
        stream["region_name"] = stream["region_code"].map(canonical_names)
        stream["federal_district_name"] = stream["region_code"].map(district_names)
        normalized_files.append(replace(parsed, regions=updated_regions, df_stream=stream))

    return tuple(sorted(normalized_files, key=lambda item: item.report_date))
