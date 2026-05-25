"""
Единый реестр семейств файлов Frank RG.

Важно:
- порядок правил задаёт приоритет распознавания;
- более специфичные семейства должны идти раньше более общих.
"""

from __future__ import annotations

from datetime import date

from stratbox.macrobanks.frank_rg.models import FrankFamilyRule


# Новая схема региональных файлов используется начиная с апреля 2026 года.
REGIONAL_NEW_SCHEMA_START = date(2026, 4, 1)


FAMILY_RULES: tuple[FrankFamilyRule, ...] = (
    FrankFamilyRule(
        code="regional_issuance_mortgage",
        title="Региональные данные — выдачи — ипотека",
        parser_group="regional",
        parser_key="regional_issuance_mortgage_stub",
        period_mode="date",
        priority=10,
        tokens_all=("frank rg", "региональные данные", "выдачи", "ипотека"),
        tokens_none=("кредитные карты",),
        min_period_date=REGIONAL_NEW_SCHEMA_START,
        note="Используется только новая региональная схема.",
    ),
    FrankFamilyRule(
        code="regional_portfolios_mortgage",
        title="Региональные данные — портфели — ипотека",
        parser_group="regional",
        parser_key="regional_portfolios_mortgage_stub",
        period_mode="date",
        priority=20,
        tokens_all=("frank rg", "региональные данные", "портфели", "ипотека"),
        min_period_date=REGIONAL_NEW_SCHEMA_START,
        note="Используется только новая региональная схема.",
    ),
    FrankFamilyRule(
        code="regional_issuance_cards",
        title="Региональные данные — выдачи — кредитные карты",
        parser_group="regional",
        parser_key="regional_issuance_cards_stub",
        period_mode="date",
        priority=30,
        tokens_all=("frank rg", "региональные данные", "выдачи", "кредитные карты"),
        min_period_date=REGIONAL_NEW_SCHEMA_START,
        note="Используется только новая региональная схема.",
    ),
    FrankFamilyRule(
        code="regional_issuance",
        title="Региональные данные — выдачи",
        parser_group="regional",
        parser_key="regional_issuance_stub",
        period_mode="date",
        priority=40,
        tokens_all=("frank rg", "региональные данные", "выдачи"),
        tokens_none=("ипотека", "кредитные карты"),
        min_period_date=REGIONAL_NEW_SCHEMA_START,
        note="Используется только новая региональная схема.",
    ),
    FrankFamilyRule(
        code="regional_portfolios",
        title="Региональные данные — портфели",
        parser_group="regional",
        parser_key="regional_portfolios_stub",
        period_mode="date",
        priority=50,
        tokens_all=("frank rg", "региональные данные", "портфели"),
        tokens_none=("ипотека", "кредитные карты"),
        min_period_date=REGIONAL_NEW_SCHEMA_START,
        note="Используется только новая региональная схема.",
    ),
    FrankFamilyRule(
        code="weekly_express_issuance",
        title="Экспресс-мониторинг рынка — выдачи — внутри месяца",
        parser_group="express",
        parser_key="weekly_express_issuance_stub",
        period_mode="weekly",
        priority=60,
        tokens_all=("frank rg", "экспресс-мониторинг рынка", "выдачи"),
        tokens_none=("кредитные карты", "региональные данные"),
        requires_week_marker=True,
    ),
    FrankFamilyRule(
        code="express_passives",
        title="Экспресс-мониторинг рынка — пассивы",
        parser_group="express",
        parser_key="express_passives_stub",
        period_mode="date",
        priority=70,
        tokens_all=("frank rg", "экспресс-мониторинг рынка", "пассивы"),
    ),
    FrankFamilyRule(
        code="cards_express_issuance",
        title="Кредитные карты — экспресс-мониторинг — выдачи",
        parser_group="express",
        parser_key="cards_express_issuance_stub",
        period_mode="date",
        priority=80,
        tokens_all=("frank rg", "кредитные карты", "экспресс-мониторинг рынка", "выдачи"),
    ),
    FrankFamilyRule(
        code="express_issuance",
        title="Экспресс-мониторинг рынка — выдачи",
        parser_group="express",
        parser_key="express_issuance_stub",
        period_mode="date",
        priority=90,
        tokens_all=("frank rg", "экспресс-мониторинг рынка", "выдачи"),
        tokens_none=("кредитные карты", "региональные данные", "недел"),
    ),
    FrankFamilyRule(
        code="express_portfolios",
        title="Экспресс-мониторинг рынка — портфели",
        parser_group="express",
        parser_key="express_portfolios_stub",
        period_mode="date",
        priority=100,
        tokens_all=("frank rg", "экспресс-мониторинг рынка", "портфели"),
        tokens_none=("региональные данные",),
    ),
    FrankFamilyRule(
        code="rbm_volumes_q",
        title="Retail Banking Market — Volumes — Q",
        parser_group="rbm",
        parser_key="rbm_volumes_q_stub",
        period_mode="date",
        priority=110,
        tokens_all=("frank rg", "retail banking market", "volumes"),
        requires_q_marker=True,
    ),
    FrankFamilyRule(
        code="rbm_portfolios_q",
        title="Retail Banking Market — Portfolios — Q",
        parser_group="rbm",
        parser_key="rbm_portfolios_q_stub",
        period_mode="date",
        priority=120,
        tokens_all=("frank rg", "retail banking market", "portfolios"),
        requires_q_marker=True,
    ),
    FrankFamilyRule(
        code="cards_volumes_q",
        title="Cards volumes — Q",
        parser_group="rbm",
        parser_key="cards_volumes_q_stub",
        period_mode="date",
        priority=130,
        tokens_all=("frank rg", "cards volumes"),
        requires_q_marker=True,
    ),
    FrankFamilyRule(
        code="mortgage_refinancing",
        title="Рефинансирование ипотеки",
        parser_group="special",
        parser_key="mortgage_refinancing_stub",
        period_mode="date",
        priority=140,
        tokens_all=("frank rg", "рефинансирование ипотеки"),
    ),
)


def get_family_rules() -> tuple[FrankFamilyRule, ...]:
    """Возвращает все правила реестра в порядке приоритета."""
    return FAMILY_RULES


def get_family_rule_map() -> dict[str, FrankFamilyRule]:
    """Возвращает словарь правил по внутреннему коду семейства."""
    return {rule.code: rule for rule in FAMILY_RULES}
