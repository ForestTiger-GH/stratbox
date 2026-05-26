"""Группа заглушек парсеров первого этапа FRG."""

from stratbox.macrobanks.frg.parsers.express import (
    parse_cards_express_issuance_stub,
    parse_express_issuance_cards_stub,
    parse_express_issuance_stub,
    parse_express_issuance_weekly_stub,
    parse_express_passives_stub,
    parse_express_portfolios_stub,
    parse_weekly_express_issuance_stub,
)
from stratbox.macrobanks.frg.parsers.rbm import (
    parse_cards_volumes_q_stub,
    parse_rbm_portfolios_q_stub,
    parse_rbm_volumes_q_stub,
    parse_volumes_cards_q_stub,
)
from stratbox.macrobanks.frg.parsers.regional import (
    parse_regional_issuance_cards_stub,
    parse_regional_issuance_mortgage_stub,
    parse_regional_issuance_stub,
    parse_regional_portfolios_mortgage_stub,
    parse_regional_portfolios_stub,
)
from stratbox.macrobanks.frg.parsers.special import parse_mortgage_refinancing_stub

__all__ = [
    "parse_cards_express_issuance_stub",
    "parse_express_issuance_cards_stub",
    "parse_express_issuance_stub",
    "parse_express_issuance_weekly_stub",
    "parse_express_passives_stub",
    "parse_express_portfolios_stub",
    "parse_weekly_express_issuance_stub",
    "parse_cards_volumes_q_stub",
    "parse_rbm_portfolios_q_stub",
    "parse_rbm_volumes_q_stub",
    "parse_volumes_cards_q_stub",
    "parse_regional_issuance_cards_stub",
    "parse_regional_issuance_mortgage_stub",
    "parse_regional_issuance_stub",
    "parse_regional_portfolios_mortgage_stub",
    "parse_regional_portfolios_stub",
    "parse_mortgage_refinancing_stub",
]
