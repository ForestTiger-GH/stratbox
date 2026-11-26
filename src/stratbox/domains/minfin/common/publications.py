"""Shared publication rules and exact asset recognition facts."""
from dataclasses import dataclass


@dataclass(frozen=True)
class AssetRule:
    source_id: str
    asset_id: str
    document_id: str
    prefix: str
    suffix: str
    format: str


@dataclass(frozen=True)
class SourceRules:
    source_id: str
    family_id: str
    index_url: str
    asset: AssetRule
    siblings: tuple[AssetRule, ...]
    frequency: str
    basis: str
    kind: str = "table"


FEDERAL_ASSETS = (
    AssetRule("minfin.fedbud.annex3.monthly", "annex3_monthly", "id_57:80042", "Prilozhenie_3_dannye_109-111_", "_mes.xlsx", "xlsx"),
    AssetRule("minfin.fedbud.annex3.quarterly", "annex3_quarterly", "id_57:80039", "Prilozhenie_3_dannye_109-111_", "_kvartal.xlsx", "xlsx"),
    AssetRule("minfin.fedbud.annex3.annual", "annex3_annual", "id_57:80041", "Prilozhenie_3_dannye_109-111_", "_god.xlsx", "xlsx"),
)
CONSOLIDATED_ASSETS = (
    AssetRule("minfin.conbud.monthly", "annex8_monthly", "id_57:93447", "Prilozhenie_8_dannye_115-117_", "_mesyats.xlsx", "xlsx"),
    AssetRule("minfin.conbud.quarterly", "annex8_quarterly", "id_57:93448", "Prilozhenie_8_dannye_115-117_", "_kvartal.xlsx", "xlsx"),
    AssetRule("minfin.conbud.annual", "annex8_annual", "id_57:93449", "Prilozhenie_8_dannye_115-117_", "_god.xlsx", "xlsx"),
)
REGIONAL_ASSETS = (
    AssetRule("minfin.subbud.monthly", "annex6_monthly", "id_57:88391", "Prilozhenie_6_dannye_112-114_", "_mes.xlsx", "xlsx"),
    AssetRule("minfin.subbud.quarterly", "annex6_quarterly", "id_57:90142", "Prilozhenie_6_dannye_112-114_", "_Kvartal.xlsx", "xlsx"),
    AssetRule("minfin.subbud.annual", "annex6_annual", "id_57:90143", "Prilozhenie_6_dannye_112-114_", "_god.xlsx", "xlsx"),
)
FUND_ASSETS = (
    AssetRule("minfin.nwf.flows", "movement_workbook", "id_57:93488", "Dannye_", ".xlsx", "xlsx"),
    AssetRule("minfin.nwf.volume", "volume_report", "id_4:27068", "Obem_na_", ".docx", "docx"),
    AssetRule("minfin.nwf.preferred_shares", "preferred_shares", "id_4:300002", "Svedeniya_na_", ".docx", "docx"),
    AssetRule("minfin.nwf.veb_deposits", "veb_deposits", "id_4:117699", "Svedeniya_o_razmeshchenii_sredstv_FNB_na_depozitakh_v_VEB", ".doc", "doc"),
)
