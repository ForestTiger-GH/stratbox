"""Explicit Bank of Russia securities source records and action settings."""
from types import MappingProxyType
from stratbox.capabilities.model.domains import SeriesSpec, CommandSpec, Applicability
from stratbox.capabilities.model.methods import MethodRef
from stratbox.domains.cbr.common.contracts import Publication, Semantics, StatisticalSettings, TableVariant, FormSettings, FamilySettings, SourceRequirement, MappingRules
from stratbox.domains.cbr.common.publications import SORS_INDEX, FORMS_INDEX, ESCROW_INDEX, OFFICES_PAGE, TERRITORIAL_INDEX

DEBT_SECURITIES_PUBLICATION = Publication(
    'cbr.securities.debt_securities', 'cbr.securities', 'Domestic debt securities issued: nominal and market value',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/debt_securities/66-debt_securities.xlsx', None,
)
DEBT_SECURITIES_TABLE = StatisticalSettings(
    'cbr.securities.debt_securities', (
        TableVariant('table_1', 'Квартал\\ \\(номинальная\\ стоимость\\)', 'statistics', 'stock', 'as_of', ('source_hierarchy', 'valuation_basis', 'frequency'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Debt securities issued on the domestic market, separate nominal and market valuations and monthly/quarterly tables.'),
        TableVariant('table_2', 'Месяц\\ \\(номинальная\\ стоимость\\)', 'statistics', 'stock', 'as_of', ('source_hierarchy', 'valuation_basis', 'frequency'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Debt securities issued on the domestic market, separate nominal and market valuations and monthly/quarterly tables.'),
        TableVariant('table_3', 'Квартал\\ \\(рыночная\\ стоимость\\)', 'statistics', 'stock', 'as_of', ('source_hierarchy', 'valuation_basis', 'frequency'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Debt securities issued on the domestic market, separate nominal and market valuations and monthly/quarterly tables.'),
        TableVariant('table_4', 'Месяц\\ \\(рыночная\\ стоимость\\)', 'statistics', 'stock', 'as_of', ('source_hierarchy', 'valuation_basis', 'frequency'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Debt securities issued on the domestic market, separate nominal and market valuations and monthly/quarterly tables.'),
    ),
)
DEBT_SECURITIES = SeriesSpec(
    id='cbr.securities.debt_securities',
    publication=DEBT_SECURITIES_PUBLICATION,
    semantics=Semantics('publisher_defined', ('publication', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            DEBT_SECURITIES_PUBLICATION, Applicability(source_ids=frozenset({'cbr.securities.debt_securities'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            DEBT_SECURITIES_PUBLICATION, Applicability(source_ids=frozenset({'cbr.securities.debt_securities'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            DEBT_SECURITIES_PUBLICATION, Applicability(source_ids=frozenset({'cbr.securities.debt_securities'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            DEBT_SECURITIES_PUBLICATION, Applicability(source_ids=frozenset({'cbr.securities.debt_securities'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.securities.debt_securities', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.securities.debt_securities'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.securities.debt_securities', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.securities.debt_securities'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.securities.debt_securities'), Applicability(source_ids=frozenset({'cbr.securities.debt_securities'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            DEBT_SECURITIES_TABLE, Applicability(source_ids=frozenset({'cbr.securities.debt_securities'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            DEBT_SECURITIES_TABLE, Applicability(source_ids=frozenset({'cbr.securities.debt_securities'})),
        ),
    }),
)

