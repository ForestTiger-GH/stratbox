"""Reviewed delivery-name rules for fourteen continuing report identities."""
from datetime import date
from .naming import RecognitionRule

_REGIONAL_START = date(2026, 4, 1)

FRG_EXPRESS_ISSUANCE_WEEKLY = RecognitionRule('frg.express.issuance_weekly', 'Экспресс выдачи — Weekly', 'month_week', 60, ('экспресс-мониторинг рынка', 'выдачи'), tokens_none=('кредитные карты', 'региональные данные'))
FRG_EXPRESS_PASSIVES = RecognitionRule('frg.express.passives', 'Экспресс — Пассивы', 'snapshot', 70, ('экспресс-мониторинг рынка', 'пассивы'))
FRG_EXPRESS_ISSUANCE_CARDS = RecognitionRule('frg.express.issuance_cards', 'Экспресс выдачи — Карты', 'snapshot', 80, ('кредитные карты', 'экспресс-мониторинг рынка', 'выдачи'))
FRG_EXPRESS_ISSUANCE = RecognitionRule('frg.express.issuance', 'Экспресс выдачи', 'snapshot', 90, ('экспресс-мониторинг рынка', 'выдачи'), tokens_none=('кредитные карты', 'региональные данные', 'недел'))
FRG_EXPRESS_PORTFOLIOS = RecognitionRule('frg.express.portfolios', 'Экспресс портфели', 'snapshot', 100, ('экспресс-мониторинг рынка', 'портфели'), tokens_none=('региональные данные',))
FRG_REGIONAL_ISSUANCE_MORTGAGE = RecognitionRule('frg.regional.issuance_mortgage', 'Региональные выдачи — Ипотека', 'snapshot', 10, ('региональные данные', 'выдачи', 'ипотека'), tokens_none=('кредитные карты',), min_period_date=_REGIONAL_START)
FRG_REGIONAL_PORTFOLIOS_MORTGAGE = RecognitionRule('frg.regional.portfolios_mortgage', 'Региональные портфели — Ипотека', 'snapshot', 20, ('региональные данные', 'портфели', 'ипотека'), min_period_date=_REGIONAL_START)
FRG_REGIONAL_ISSUANCE_CARDS = RecognitionRule('frg.regional.issuance_cards', 'Региональные выдачи — Карты', 'snapshot', 30, ('региональные данные', 'выдачи', 'кредитные карты'), min_period_date=_REGIONAL_START)
FRG_REGIONAL_ISSUANCE = RecognitionRule('frg.regional.issuance', 'Региональные выдачи', 'snapshot', 40, ('региональные данные', 'выдачи'), tokens_none=('ипотека', 'кредитные карты'), min_period_date=_REGIONAL_START)
FRG_REGIONAL_PORTFOLIOS = RecognitionRule('frg.regional.portfolios', 'Региональные портфели', 'snapshot', 50, ('региональные данные', 'портфели'), tokens_none=('ипотека', 'кредитные карты'), min_period_date=_REGIONAL_START)
FRG_RBM_VOLUMES_Q = RecognitionRule('frg.rbm.volumes_q', 'Выдачи — Q', 'snapshot', 110, ('retail banking market', 'volumes'), tokens_none=('cards volumes',), requires_q_marker=True)
FRG_RBM_PORTFOLIOS_Q = RecognitionRule('frg.rbm.portfolios_q', 'Портфели — Q', 'snapshot', 120, ('retail banking market', 'portfolios'), requires_q_marker=True)
FRG_RBM_VOLUMES_CARDS_Q = RecognitionRule('frg.rbm.volumes_cards_q', 'Выдачи — Карты — Q', 'snapshot', 130, ('cards volumes',), requires_q_marker=True)
FRG_SPECIAL_MORTGAGE_REFINANCING = RecognitionRule('frg.special.mortgage_refinancing', 'Рефинансирование ипотеки', 'snapshot', 140, ('рефинансирование ипотеки',))

RULES = (
    FRG_EXPRESS_ISSUANCE_WEEKLY,
    FRG_EXPRESS_PASSIVES,
    FRG_EXPRESS_ISSUANCE_CARDS,
    FRG_EXPRESS_ISSUANCE,
    FRG_EXPRESS_PORTFOLIOS,
    FRG_REGIONAL_ISSUANCE_MORTGAGE,
    FRG_REGIONAL_PORTFOLIOS_MORTGAGE,
    FRG_REGIONAL_ISSUANCE_CARDS,
    FRG_REGIONAL_ISSUANCE,
    FRG_REGIONAL_PORTFOLIOS,
    FRG_RBM_VOLUMES_Q,
    FRG_RBM_PORTFOLIOS_Q,
    FRG_RBM_VOLUMES_CARDS_Q,
    FRG_SPECIAL_MORTGAGE_REFINANCING,
)
