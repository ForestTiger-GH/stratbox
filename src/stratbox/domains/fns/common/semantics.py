"""Reviewed FNS meanings and narrow settings for command methods."""
from dataclasses import dataclass

COUNTERS = ("cnt_total", "cnt_ul_total", "cnt_ip_total", "cnt_ul_micro",
            "cnt_ul_mini", "cnt_ul_normal", "cnt_ip_micro", "cnt_ip_mini",
            "cnt_ip_normal")
COUNTER_ALIASES = (
    ("cnt_total", "total"), ("cnt_ul_total", "ul_total"),
    ("cnt_ip_total", "ip_total"), ("cnt_ul_micro", "ul_micro"),
    ("cnt_ul_mini", "ul_small"), ("cnt_ul_normal", "ul_medium"),
    ("cnt_ip_micro", "ip_micro"), ("cnt_ip_mini", "ip_small"),
    ("cnt_ip_normal", "ip_medium"),
)
IDENTIFIERS = frozenset({"stat_date", "cnt_level", "cnt_name", "ssrf", "name"})


@dataclass(frozen=True)
class SmeRules:
    source_id: str = "fns.sme"
    counters: tuple[str, ...] = COUNTERS
    aliases: tuple[tuple[str, str], ...] = COUNTER_ALIASES
    max_records: int = 10_000


@dataclass(frozen=True)
class LegalRules:
    source_id: str = "fns.1yur"
    section: str = "I"
    fields: tuple[str, ...] = ("not_ceased", "bankruptcy_proceedings",
                               "ceased_bankruptcy_liquidation")


SME_RULES = SmeRules()
LEGAL_RULES = LegalRules()
