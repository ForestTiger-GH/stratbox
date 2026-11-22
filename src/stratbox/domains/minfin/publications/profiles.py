"""Typed publisher-layout and asset-identity profiles.

No arbitrary Python refs in YAML; logical source identity survives file renames.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class PublicationProfile:
    profile_id: str
    layout: Literal["document_cards"]
    method_version: int = 1


@dataclass(frozen=True, slots=True)
class AssetRule:
    slot: str
    asset_id: str
    prefix: str
    suffix: str
    document_id: str | None
    format: str

    def matches_filename(self, filename: str) -> bool:
        name = filename.casefold()
        return name.startswith(self.prefix.casefold()) and name.endswith(self.suffix.casefold())


@dataclass(frozen=True, slots=True)
class IdentificationProfile:
    profile_id: str
    rules: tuple[AssetRule, ...]
    method_version: int = 1

    def __post_init__(self) -> None:
        if not self.rules or len({rule.slot for rule in self.rules}) != len(self.rules):
            raise ValueError("minfin.profile.duplicate_slot")
        keys = [rule.document_id for rule in self.rules if rule.document_id is not None]
        if len(keys) != len(set(keys)):
            raise ValueError("minfin.profile.duplicate_document")

    @property
    def formats(self) -> frozenset[str]:
        return frozenset(rule.format for rule in self.rules)

    def rule(self, slot: str) -> AssetRule:
        for item in self.rules:
            if item.slot == slot:
                return item
        raise ValueError("minfin.profile.slot_unknown")

    def identify(self, document_id: str | None, filename: str, fmt: str) -> tuple[str | None, str]:
        """Document identity prevails over a rename; contradictory evidence fails closed."""
        by_document = [r for r in self.rules if document_id is not None and r.document_id == document_id]
        by_filename = [r for r in self.rules if r.format == fmt and r.matches_filename(filename)]
        if len(by_document) > 1 or len(by_filename) > 1:
            return None, "conflicted"
        documented = by_document[0] if by_document else None
        named = by_filename[0] if by_filename else None
        if documented is not None:
            if documented.format != fmt or (named is not None and named.slot != documented.slot):
                return None, "conflicted"
            return documented.slot, "registered_variant"
        if named is not None:
            return named.slot, "registered_variant"
        return None, "unclassified"


_PUBLICATIONS = {"minfin.document_cards.v1": PublicationProfile("minfin.document_cards.v1", "document_cards")}


def _budget(profile_id: str, annex: str, doc_ids: tuple[str, str, str], prefix: str,
            suffixes: tuple[str, str, str]) -> IdentificationProfile:
    return IdentificationProfile(profile_id, tuple(
        AssetRule(slot, annex + "_" + slot, prefix, suffix, document, "xlsx")
        for slot, suffix, document in zip(("monthly", "quarterly", "annual"), suffixes, doc_ids)
    ))


_IDENTIFICATIONS = {
    "minfin.fedbud_assets.v1": _budget(
        "minfin.fedbud_assets.v1", "annex3", ("id_57:80042", "id_57:80039", "id_57:80041"),
        "Prilozhenie_3_dannye_109-111_", ("_mes.xlsx", "_kvartal.xlsx", "_god.xlsx")),
    "minfin.conbud_assets.v1": _budget(
        "minfin.conbud_assets.v1", "annex8", ("id_57:93447", "id_57:93448", "id_57:93449"),
        "Prilozhenie_8_dannye_115-117_", ("_mesyats.xlsx", "_kvartal.xlsx", "_god.xlsx")),
    "minfin.subbud_assets.v1": _budget(
        "minfin.subbud_assets.v1", "annex6", ("id_57:88391", "id_57:90142", "id_57:90143"),
        "Prilozhenie_6_dannye_112-114_", ("_mes.xlsx", "_Kvartal.xlsx", "_god.xlsx")),
    "minfin.nwf_assets.v1": IdentificationProfile("minfin.nwf_assets.v1", (
        AssetRule("monthly", "movement_workbook", "Dannye_", ".xlsx", "id_57:93488", "xlsx"),
        AssetRule("veb_deposits", "veb_deposits", "Svedeniya_o_razmeshchenii_sredstv_FNB_na_depozitakh_v_VEB", ".doc", "id_4:117699", "doc"),
        AssetRule("volume_report", "volume_report", "Obem_na_", ".docx", "id_4:27068", "docx"),
        AssetRule("preferred_shares", "preferred_shares", "Svedeniya_na_", ".docx", "id_4:300002", "docx"),
    )),
}


def publication_profile(profile_id: str) -> PublicationProfile:
    try:
        return _PUBLICATIONS[profile_id]
    except (KeyError, TypeError):
        raise ValueError("minfin.profile.publication_unknown") from None


def identification_profile(profile_id: str) -> IdentificationProfile:
    try:
        return _IDENTIFICATIONS[profile_id]
    except (KeyError, TypeError):
        raise ValueError("minfin.profile.identification_unknown") from None


__all__ = ("PublicationProfile", "AssetRule", "IdentificationProfile",
           "publication_profile", "identification_profile")