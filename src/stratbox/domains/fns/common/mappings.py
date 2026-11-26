"""Dated source facts for legal categories; no component release lifecycle."""

from __future__ import annotations

import csv
from datetime import date
import hashlib
import io
import re





FIRST = date(2012, 1, 1)


A_END = date(2013, 4, 1)


B_END = date(2019, 2, 1)


C1_END = date(2021, 1, 1)


C2_END = date(2023, 1, 1)


KINDS = {
    "1000": "all",
    "1100": "commercial",
    "1110": "general_partnership",
    "1120": "limited_partnership",
    "1130": "limited_liability_company_including_additional",
    "1131": "additional_liability_company",
    "1140": "joint_stock_company",
    "1141": "public_joint_stock_company",
    "1142": "nonpublic_joint_stock_company",
    "1143": "open_joint_stock_company",
    "1144": "closed_joint_stock_company",
    "1150": "production_cooperative",
    "1151": "agricultural_production_cooperative",
    "1160": "peasant_farm_enterprise",
    "1170": "unitary_enterprise",
    "1171": "federal_unitary_enterprise",
    "1172": "regional_unitary_enterprise",
    "1173": "municipal_unitary_enterprise",
    "1174": "federal_treasury_enterprise",
    "1175": "regional_treasury_enterprise",
    "1176": "municipal_treasury_enterprise",
    "1180": "other_commercial",
    "1190": "special_registration_commercial_cbr",
    "1200": "nonprofit",
    "1210": "consumer_cooperative",
    "1220": "real_estate_owners_association",
    "1221": "gardening_nonprofit_association",
    "1222": "homeowners_association",
    "1230": "institution",
    "1231": "federal_institution",
    "1232": "regional_institution",
    "1233": "municipal_institution",
    "1240": "special_registration_nonprofit",
    "1241": "special_registration_nonprofit_justice_ministry",
    "1242": "special_registration_nonprofit_cbr",
    "1250": "other_nonprofit",
    "1251": "personal_foundation",
}


A = {
    "1010": "1000",
    "1020": "1100",
    "1021": "1110",
    "1022": "1120",
    "1023": "1130",  # FNS directly reports LLC together with additional-liability companies
    "1024": "1140",
    "1025": "1150",
    "1026": "1170",
    "1030": "1200",
    "1031": "1210",
    "1032": "1230",
}


B = {
    "1010": "1000",
    "1020": "1100",
    "1021": "1110",
    "1022": "1120",
    # 1023 is LLC *excluding* additional-liability companies: not the modern 1130.
    # B 1023 + B 1024 would be a DERIVATION, excluded from the source CSV.
    "1024": "1131",
    "1025": "1140",
    "1026": "1144",
    "1027": "1143",
    "1028": "1150",
    "1029": "1170",
    "1040": "1200",
    "1041": "1210",
    "1042": "1230",
    "1043": "1241",  # FNS reports MinJust special-registered entities within NPO
}


C = {code: code for code in KINDS}


SOURCE_PATTERN = re.compile(r"c([0-9]{2})_([0-9]{4})\Z")


FIELD_PATTERN = re.compile(
    r"le_(not_ceased|bankruptcy_proceedings|ceased_bankruptcy_liquidation)__([a-z][a-z0-9_]*)\Z"
)


GEO = re.compile(r"[0-9]{2}\Z")


PREFIXES = {
    "A": {"c01": "not_ceased", "c11": "ceased_bankruptcy_liquidation"},
    "B": {"c01": "not_ceased", "c11": "ceased_bankruptcy_liquidation"},
    "C1": {"c01": "not_ceased", "c12": "ceased_bankruptcy_liquidation"},
    "C2": {
        "c01": "not_ceased",
        "c09": "bankruptcy_proceedings",
        "c13": "ceased_bankruptcy_liquidation",
    },
    "C3": {
        "c01": "not_ceased",
        "c08": "bankruptcy_proceedings",
        "c12": "ceased_bankruptcy_liquidation",
    },
}


CATEGORY = {"A": A, "B": B, "C1": C, "C2": C, "C3": C}


MEASURE_ORDER = (
    "not_ceased",
    "bankruptcy_proceedings",
    "ceased_bankruptcy_liquidation",
)


KIND_ORDER = list(KINDS)


class SchemaError(ValueError):
    """Unreviewed source layout, ambiguous mapping, or non-faithful conversion."""


def epoch(d):
    if isinstance(d, str):
        d = date.fromisoformat(d)
    if d < FIRST:
        raise SchemaError("DATE_BEFORE_REVIEWED_HISTORY")
    if d <= A_END:
        return "A"
    if d <= B_END:
        return "B"
    if d <= C1_END:
        return "C1"
    if d <= C2_END:
        return "C2"
    return "C3"


def mapping(d, original_column):
    """Return (canonical_column, disposition). Never invent a source field."""
    e = epoch(d)
    m = SOURCE_PATTERN.fullmatch(original_column)
    if m is None:
        raise SchemaError("UNEXPECTED_SOURCE_COLUMN:" + original_column)
    indicator, kind = ("c" + m.group(1)), m.group(2)
    construct = PREFIXES[e].get(indicator)
    if construct is None:
        raise SchemaError("UNREVIEWED_SOURCE_INDICATOR:" + original_column)
    aligned_kind = CATEGORY[e].get(kind)
    if aligned_kind is None:
        return None, "omitted_no_reported_modern_equivalent"
    target = "le_" + construct + "__" + KINDS[aligned_kind]
    return target, "reported_value_alias"


