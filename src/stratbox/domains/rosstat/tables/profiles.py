"""Reviewed KEP2 notebook scope; selectors are exact and named, never fuzzy."""
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class KepIndicator:
    id: str
    label: str
    titles: tuple[str, ...]
    absolute: bool = True
    parent: str | None = None
    quantity_kind: str = "flow"


KEP2_INDICATORS = (
    KepIndicator("investment", "Инвестиции в основной капитал", ("Инвестиции в основной капитал",)),
    KepIndicator("wages", "Заработная плата", ("Заработная плата", "Среднемесячная номинальная начисленная заработная плата работников организаций"), quantity_kind="ratio"),
    KepIndicator("construction", "Строительство", ('Объем работ по виду деятельности "Строительство"',)),
    KepIndicator("freight_turnover", "Грузооборот", ("Грузооборот транспорта, включая коммерческий и некоммерческий грузооборот",)),
    KepIndicator("retail", "Розничная торговля", ("Оборот розничной торговли",)),
    KepIndicator("retail_food", "Продовольственная розничная торговля", ("пищевые продукты, включая напитки, и табачные изделия", "пищевые продукты, включая напитки, и таб"), parent="retail"),
    KepIndicator("retail_nonfood", "Непродовольственная розничная торговля", ("непродовольственные товары",), parent="retail"),
    KepIndicator("catering", "Оборот общественного питания", ("Оборот общественного питания",), parent="retail"),
    KepIndicator("wholesale", "Оптовая торговля", ("Оборот оптовой торговли",)),
    KepIndicator("paid_services", "Платные услуги", ("Объем платных услуг населению",)),
    KepIndicator("agriculture", "Сельское хозяйство", ("Индекс производства продукции сельского хозяйства в хозяйствах всех категорий",), absolute=False, quantity_kind="index"),
)
KEP2_PROFILE_ID = "rosstat.kep2.v1"
KEP2_MEASURES = (
    ("absolute", "Абсолютные значения", None),
    ("year_on_year_index", "% г/г", "в % к соответствующему периоду предыдущего года"),
    ("previous_period_index", "% к предыдущему периоду", "в % к предыдущему периоду"),
)
