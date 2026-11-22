"""Typed delivery, recognition, selection and output naming methods."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re
from typing import Callable, Literal

_ID = re.compile(r"[a-z][a-z0-9_.-]{2,127}\Z")
_FORMATS = frozenset({"xlsx", "xlsm", "xls", "xlsb"})


def _profile_identity(identity, method_version):
    if not isinstance(identity, str) or not _ID.fullmatch(identity):
        raise ValueError("frg.profile.invalid_identity")
    if type(method_version) is not int or method_version < 1:
        raise ValueError("frg.profile.invalid_method_version")


def _discover_directory(request, store, invocation=None):
    from .discovery import discover_directory
    return discover_directory(request, store, invocation=invocation)


def _select_latest(inventory, *, source_ids):
    from .selection import select_latest
    return select_latest(inventory, source_ids=source_ids)


def _build_name(period, rule, *, format, profile):
    from .naming import _canonical_filename
    return _canonical_filename(period, rule, format=format, profile=profile)


@dataclass(frozen=True, slots=True)
class DiscoveryProfile:
    profile_id: str
    discover: Callable
    method_version: int = 1

    def __post_init__(self):
        _profile_identity(self.profile_id, self.method_version)
        if not callable(self.discover):
            raise ValueError("frg.profile.invalid_callback")


@dataclass(frozen=True, slots=True)
class RecognitionRule:
    slot: str
    canonical_label: str
    periodicity: Literal["snapshot", "month_week"]
    priority: int
    tokens_all: tuple[str, ...]
    tokens_any: tuple[str, ...] = ()
    tokens_none: tuple[str, ...] = ()
    requires_q_marker: bool = False
    min_period_date: date | None = None

    def __post_init__(self):
        if not isinstance(self.slot, str) or not _ID.fullmatch(self.slot):
            raise ValueError("frg.profile.invalid_slot")
        if not isinstance(self.canonical_label, str) or not self.canonical_label.strip():
            raise ValueError("frg.profile.invalid_label")
        if self.periodicity not in ("snapshot", "month_week") or type(self.priority) is not int or self.priority < 0:
            raise ValueError("frg.profile.invalid_rule")
        for tokens in (self.tokens_all, self.tokens_any, self.tokens_none):
            if not isinstance(tokens, tuple) or any(not isinstance(item, str) or not item.strip() for item in tokens):
                raise ValueError("frg.profile.invalid_tokens")
        if not self.tokens_all or type(self.requires_q_marker) is not bool:
            raise ValueError("frg.profile.invalid_rule")
        if self.min_period_date is not None and type(self.min_period_date) is not date:
            raise ValueError("frg.profile.invalid_cutoff")


@dataclass(frozen=True, slots=True)
class IdentificationProfile:
    profile_id: str
    rules: tuple[RecognitionRule, ...]
    admitted_formats: frozenset[str] = _FORMATS
    method_version: int = 1

    def __post_init__(self):
        _profile_identity(self.profile_id, self.method_version)
        if not isinstance(self.rules, tuple) or not self.rules or any(not isinstance(item, RecognitionRule) for item in self.rules):
            raise ValueError("frg.profile.invalid_rules")
        if len({item.slot for item in self.rules}) != len(self.rules):
            raise ValueError("frg.profile.duplicate_slot")
        if len({item.canonical_label.casefold() for item in self.rules}) != len(self.rules):
            raise ValueError("frg.profile.duplicate_label")
        if not isinstance(self.admitted_formats, frozenset) or not self.admitted_formats or not self.admitted_formats <= _FORMATS:
            raise ValueError("frg.profile.invalid_formats")

    def rule(self, slot: str) -> RecognitionRule:
        for item in self.rules:
            if item.slot == slot:
                return item
        raise ValueError("frg.profile.unknown_slot")


@dataclass(frozen=True, slots=True)
class SelectionProfile:
    profile_id: str
    select: Callable
    method_version: int = 1

    def __post_init__(self):
        _profile_identity(self.profile_id, self.method_version)
        if not callable(self.select):
            raise ValueError("frg.profile.invalid_callback")


@dataclass(frozen=True, slots=True)
class NamingProfile:
    profile_id: str
    build: Callable
    method_version: int = 1
    prefix: str = ""
    separator: str = "_"

    def __post_init__(self):
        _profile_identity(self.profile_id, self.method_version)
        if not callable(self.build):
            raise ValueError("frg.profile.invalid_callback")
        if self.prefix != "" or self.separator != "_":
            raise ValueError("frg.profile.naming_scheme_unsupported")


_REGIONAL_START = date(2026, 4, 1)
_DISCOVERY = DiscoveryProfile("frg.directory.v1", _discover_directory)
_SELECTION = SelectionProfile("frg.latest_period.v1", _select_latest)
_NAMING = NamingProfile("frg.canonical.v1", _build_name)

_IDENTIFICATION = (
    IdentificationProfile("frg.identification.express.v1", (
        RecognitionRule("issuance_weekly", "Экспресс выдачи — Weekly", "month_week", 60,
                        ("экспресс-мониторинг рынка", "выдачи"), tokens_none=("кредитные карты", "региональные данные")),
        RecognitionRule("passives", "Экспресс — Пассивы", "snapshot", 70,
                        ("экспресс-мониторинг рынка", "пассивы")),
        RecognitionRule("issuance_cards", "Экспресс выдачи — Карты", "snapshot", 80,
                        ("кредитные карты", "экспресс-мониторинг рынка", "выдачи")),
        RecognitionRule("issuance", "Экспресс выдачи", "snapshot", 90,
                        ("экспресс-мониторинг рынка", "выдачи"), tokens_none=("кредитные карты", "региональные данные", "недел")),
        RecognitionRule("portfolios", "Экспресс портфели", "snapshot", 100,
                        ("экспресс-мониторинг рынка", "портфели"), tokens_none=("региональные данные",)),
    )),
    IdentificationProfile("frg.identification.regional.v1", (
        RecognitionRule("issuance_mortgage", "Региональные выдачи — Ипотека", "snapshot", 10,
                        ("региональные данные", "выдачи", "ипотека"), tokens_none=("кредитные карты",), min_period_date=_REGIONAL_START),
        RecognitionRule("portfolios_mortgage", "Региональные портфели — Ипотека", "snapshot", 20,
                        ("региональные данные", "портфели", "ипотека"), min_period_date=_REGIONAL_START),
        RecognitionRule("issuance_cards", "Региональные выдачи — Карты", "snapshot", 30,
                        ("региональные данные", "выдачи", "кредитные карты"), min_period_date=_REGIONAL_START),
        RecognitionRule("issuance", "Региональные выдачи", "snapshot", 40,
                        ("региональные данные", "выдачи"), tokens_none=("ипотека", "кредитные карты"), min_period_date=_REGIONAL_START),
        RecognitionRule("portfolios", "Региональные портфели", "snapshot", 50,
                        ("региональные данные", "портфели"), tokens_none=("ипотека", "кредитные карты"), min_period_date=_REGIONAL_START),
    )),
    IdentificationProfile("frg.identification.rbm.v1", (
        RecognitionRule("volumes_q", "Выдачи — Q", "snapshot", 110,
                        ("retail banking market", "volumes"), tokens_none=("cards volumes",), requires_q_marker=True),
        RecognitionRule("portfolios_q", "Портфели — Q", "snapshot", 120,
                        ("retail banking market", "portfolios"), requires_q_marker=True),
        RecognitionRule("volumes_cards_q", "Выдачи — Карты — Q", "snapshot", 130,
                        ("cards volumes",), requires_q_marker=True),
    )),
    IdentificationProfile("frg.identification.special.v1", (
        RecognitionRule("mortgage_refinancing", "Рефинансирование ипотеки", "snapshot", 140,
                        ("рефинансирование ипотеки",)),
    )),
)


def discovery_profile(profile_id: str) -> DiscoveryProfile:
    if profile_id == _DISCOVERY.profile_id:
        return _DISCOVERY
    raise ValueError("frg.profile.unknown_discovery")


def identification_profile(profile_id: str) -> IdentificationProfile:
    for item in _IDENTIFICATION:
        if item.profile_id == profile_id:
            return item
    raise ValueError("frg.profile.unknown_identification")


def selection_profile(profile_id: str) -> SelectionProfile:
    if profile_id == _SELECTION.profile_id:
        return _SELECTION
    raise ValueError("frg.profile.unknown_selection")


def naming_profile(profile_id: str) -> NamingProfile:
    if profile_id == _NAMING.profile_id:
        return _NAMING
    raise ValueError("frg.profile.unknown_naming")


__all__ = ("DiscoveryProfile", "RecognitionRule", "IdentificationProfile", "SelectionProfile",
           "NamingProfile", "discovery_profile", "identification_profile", "selection_profile", "naming_profile")
