"""Explicit Bank of Russia household_finance source records and action settings."""
from types import MappingProxyType
from stratbox.capabilities.model.domains import SeriesSpec, CommandSpec, Applicability
from stratbox.capabilities.model.methods import MethodRef
from stratbox.domains.cbr.common.contracts import Publication, Semantics, StatisticalSettings, TableVariant, FormSettings, FamilySettings, SourceRequirement, MappingRules
from stratbox.domains.cbr.common.publications import SORS_INDEX, FORMS_INDEX, ESCROW_INDEX, OFFICES_PAGE, TERRITORIAL_INDEX

HOUSEHOLDS_BM_PUBLICATION = Publication(
    'cbr.household_finance.households_bm', 'cbr.household_finance', 'Household financial assets and liabilities: balances',
    'rolling', ('xlsx',), 'fixed', 'https://cbr.ru/vfs/statistics/households/households_bm.xlsx', None,
)
HOUSEHOLDS_BM_TABLE = StatisticalSettings(
    'cbr.household_finance.households_bm', (
        TableVariant('methodology', 'Методологический\\ комментарий', 'metadata', None, 'mixed_source_periods', ('source_hierarchy', 'instrument', 'seasonal_adjustment'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Balances and transactions remain separate; seasonal adjustment and methodology sheets are preserved. Published transactions are not differences of balances.'),
        TableVariant('balances', 'Балансы', 'statistics', 'stock', 'as_of', ('source_hierarchy', 'instrument', 'seasonal_adjustment'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Balances and transactions remain separate; seasonal adjustment and methodology sheets are preserved. Published transactions are not differences of balances.'),
        TableVariant('balances_sa', 'Балансы\\ \\(с\\.к\\.\\)', 'statistics', 'stock', 'as_of', ('source_hierarchy', 'instrument', 'seasonal_adjustment'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Balances and transactions remain separate; seasonal adjustment and methodology sheets are preserved. Published transactions are not differences of balances.'),
        TableVariant('seasonal_metadata', 'Метаданные', 'metadata', None, 'mixed_source_periods', ('source_hierarchy', 'instrument', 'seasonal_adjustment'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Balances and transactions remain separate; seasonal adjustment and methodology sheets are preserved. Published transactions are not differences of balances.'),
    ),
)
HOUSEHOLDS_BM = SeriesSpec(
    id='cbr.household_finance.households_bm',
    publication=HOUSEHOLDS_BM_PUBLICATION,
    semantics=Semantics('publisher_defined', ('publication', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            HOUSEHOLDS_BM_PUBLICATION, Applicability(source_ids=frozenset({'cbr.household_finance.households_bm'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            HOUSEHOLDS_BM_PUBLICATION, Applicability(source_ids=frozenset({'cbr.household_finance.households_bm'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            HOUSEHOLDS_BM_PUBLICATION, Applicability(source_ids=frozenset({'cbr.household_finance.households_bm'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            HOUSEHOLDS_BM_PUBLICATION, Applicability(source_ids=frozenset({'cbr.household_finance.households_bm'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.household_finance.households_bm', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.household_finance.households_bm'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.household_finance.households_bm', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.household_finance.households_bm'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.household_finance.households_bm'), Applicability(source_ids=frozenset({'cbr.household_finance.households_bm'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            HOUSEHOLDS_BM_TABLE, Applicability(source_ids=frozenset({'cbr.household_finance.households_bm'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            HOUSEHOLDS_BM_TABLE, Applicability(source_ids=frozenset({'cbr.household_finance.households_bm'})),
        ),
    }),
)

HOUSEHOLDS_OM_PUBLICATION = Publication(
    'cbr.household_finance.households_om', 'cbr.household_finance', 'Household financial assets and liabilities: transactions',
    'rolling', ('xlsx',), 'fixed', 'https://cbr.ru/vfs/statistics/households/households_om.xlsx', None,
)
HOUSEHOLDS_OM_TABLE = StatisticalSettings(
    'cbr.household_finance.households_om', (
        TableVariant('methodology', 'Методологический\\ комментарий', 'metadata', None, 'mixed_source_periods', ('source_hierarchy', 'instrument', 'seasonal_adjustment'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Balances and transactions remain separate; seasonal adjustment and methodology sheets are preserved. Published transactions are not differences of balances.'),
        TableVariant('reported_transactions', 'Операции', 'statistics', 'flow', 'source_interval', ('source_hierarchy', 'instrument', 'seasonal_adjustment'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Balances and transactions remain separate; seasonal adjustment and methodology sheets are preserved. Published transactions are not differences of balances.'),
        TableVariant('reported_transactions_sa', 'Операции\\ \\(с\\.к\\.\\)', 'statistics', 'flow', 'source_interval', ('source_hierarchy', 'instrument', 'seasonal_adjustment'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Balances and transactions remain separate; seasonal adjustment and methodology sheets are preserved. Published transactions are not differences of balances.'),
        TableVariant('seasonal_metadata', 'Метаданные', 'metadata', None, 'mixed_source_periods', ('source_hierarchy', 'instrument', 'seasonal_adjustment'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Balances and transactions remain separate; seasonal adjustment and methodology sheets are preserved. Published transactions are not differences of balances.'),
    ),
)
HOUSEHOLDS_OM = SeriesSpec(
    id='cbr.household_finance.households_om',
    publication=HOUSEHOLDS_OM_PUBLICATION,
    semantics=Semantics('publisher_defined', ('publication', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            HOUSEHOLDS_OM_PUBLICATION, Applicability(source_ids=frozenset({'cbr.household_finance.households_om'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            HOUSEHOLDS_OM_PUBLICATION, Applicability(source_ids=frozenset({'cbr.household_finance.households_om'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            HOUSEHOLDS_OM_PUBLICATION, Applicability(source_ids=frozenset({'cbr.household_finance.households_om'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            HOUSEHOLDS_OM_PUBLICATION, Applicability(source_ids=frozenset({'cbr.household_finance.households_om'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.household_finance.households_om', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.household_finance.households_om'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.household_finance.households_om', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.household_finance.households_om'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.household_finance.households_om'), Applicability(source_ids=frozenset({'cbr.household_finance.households_om'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            HOUSEHOLDS_OM_TABLE, Applicability(source_ids=frozenset({'cbr.household_finance.households_om'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            HOUSEHOLDS_OM_TABLE, Applicability(source_ids=frozenset({'cbr.household_finance.households_om'})),
        ),
    }),
)

