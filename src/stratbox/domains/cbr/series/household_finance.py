"""Explicit Bank of Russia household_finance source records and action settings."""
from types import MappingProxyType
from stratbox.capabilities.model.domains import SeriesSpec, CommandSpec, Applicability
from stratbox.capabilities.model.methods import MethodRef
from stratbox.domains.cbr.common.contracts import Publication, Semantics, StatisticalSettings, TableVariant, FormSettings, FamilySettings, SourceRequirement, MappingRules
from stratbox.domains.cbr.common.publications import SORS_INDEX, FORMS_INDEX, ESCROW_INDEX, OFFICES_PAGE, TERRITORIAL_INDEX

FAMILY_ID = 'cbr.household_finance'

HOUSEHOLDS_BM_PUBLICATION = Publication(
    'cbr.household_finance.households_bm', FAMILY_ID, 'Household financial assets and liabilities: balances',
    'rolling', ('xlsx',), 'fixed', 'https://cbr.ru/vfs/statistics/households/households_bm.xlsx', None,
)
HOUSEHOLDS_BM_TABLE = StatisticalSettings(
    HOUSEHOLDS_BM_PUBLICATION.series_id, (
        TableVariant('methodology', 'Методологический\\ комментарий', 'metadata', None, 'mixed_source_periods', ('source_hierarchy', 'instrument', 'seasonal_adjustment'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Balances and transactions remain separate; seasonal adjustment and methodology sheets are preserved. Published transactions are not differences of balances.'),
        TableVariant('balances', 'Балансы', 'statistics', 'stock', 'as_of', ('source_hierarchy', 'instrument', 'seasonal_adjustment'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Balances and transactions remain separate; seasonal adjustment and methodology sheets are preserved. Published transactions are not differences of balances.'),
        TableVariant('balances_sa', 'Балансы\\ \\(с\\.к\\.\\)', 'statistics', 'stock', 'as_of', ('source_hierarchy', 'instrument', 'seasonal_adjustment'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Balances and transactions remain separate; seasonal adjustment and methodology sheets are preserved. Published transactions are not differences of balances.'),
        TableVariant('seasonal_metadata', 'Метаданные', 'metadata', None, 'mixed_source_periods', ('source_hierarchy', 'instrument', 'seasonal_adjustment'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Balances and transactions remain separate; seasonal adjustment and methodology sheets are preserved. Published transactions are not differences of balances.'),
    ),
)
HOUSEHOLDS_BM = SeriesSpec(
    id=HOUSEHOLDS_BM_PUBLICATION.series_id,
    publication=HOUSEHOLDS_BM_PUBLICATION,
    semantics=Semantics('publisher_defined', ('publication', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            HOUSEHOLDS_BM_PUBLICATION, Applicability(source_ids=frozenset({HOUSEHOLDS_BM_PUBLICATION.series_id})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            HOUSEHOLDS_BM_PUBLICATION, Applicability(source_ids=frozenset({HOUSEHOLDS_BM_PUBLICATION.series_id})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            HOUSEHOLDS_BM_PUBLICATION, Applicability(source_ids=frozenset({HOUSEHOLDS_BM_PUBLICATION.series_id})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            HOUSEHOLDS_BM_PUBLICATION, Applicability(source_ids=frozenset({HOUSEHOLDS_BM_PUBLICATION.series_id})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement(HOUSEHOLDS_BM_PUBLICATION.series_id, HOUSEHOLDS_BM_PUBLICATION.formats, issue_required=HOUSEHOLDS_BM_PUBLICATION.issue_model == 'dated'), Applicability(source_ids=frozenset({HOUSEHOLDS_BM_PUBLICATION.series_id})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement(HOUSEHOLDS_BM_PUBLICATION.series_id, HOUSEHOLDS_BM_PUBLICATION.formats, issue_required=HOUSEHOLDS_BM_PUBLICATION.issue_model == 'dated'), Applicability(source_ids=frozenset({HOUSEHOLDS_BM_PUBLICATION.series_id})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules(HOUSEHOLDS_BM_PUBLICATION.series_id), Applicability(source_ids=frozenset({HOUSEHOLDS_BM_PUBLICATION.series_id})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            HOUSEHOLDS_BM_TABLE, Applicability(source_ids=frozenset({HOUSEHOLDS_BM_PUBLICATION.series_id})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            HOUSEHOLDS_BM_TABLE, Applicability(source_ids=frozenset({HOUSEHOLDS_BM_PUBLICATION.series_id})),
        ),
    }),
)

HOUSEHOLDS_OM_PUBLICATION = Publication(
    'cbr.household_finance.households_om', FAMILY_ID, 'Household financial assets and liabilities: transactions',
    'rolling', ('xlsx',), 'fixed', 'https://cbr.ru/vfs/statistics/households/households_om.xlsx', None,
)
HOUSEHOLDS_OM_TABLE = StatisticalSettings(
    HOUSEHOLDS_OM_PUBLICATION.series_id, (
        TableVariant('methodology', 'Методологический\\ комментарий', 'metadata', None, 'mixed_source_periods', ('source_hierarchy', 'instrument', 'seasonal_adjustment'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Balances and transactions remain separate; seasonal adjustment and methodology sheets are preserved. Published transactions are not differences of balances.'),
        TableVariant('reported_transactions', 'Операции', 'statistics', 'flow', 'source_interval', ('source_hierarchy', 'instrument', 'seasonal_adjustment'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Balances and transactions remain separate; seasonal adjustment and methodology sheets are preserved. Published transactions are not differences of balances.'),
        TableVariant('reported_transactions_sa', 'Операции\\ \\(с\\.к\\.\\)', 'statistics', 'flow', 'source_interval', ('source_hierarchy', 'instrument', 'seasonal_adjustment'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Balances and transactions remain separate; seasonal adjustment and methodology sheets are preserved. Published transactions are not differences of balances.'),
        TableVariant('seasonal_metadata', 'Метаданные', 'metadata', None, 'mixed_source_periods', ('source_hierarchy', 'instrument', 'seasonal_adjustment'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Balances and transactions remain separate; seasonal adjustment and methodology sheets are preserved. Published transactions are not differences of balances.'),
    ),
)
HOUSEHOLDS_OM = SeriesSpec(
    id=HOUSEHOLDS_OM_PUBLICATION.series_id,
    publication=HOUSEHOLDS_OM_PUBLICATION,
    semantics=Semantics('publisher_defined', ('publication', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            HOUSEHOLDS_OM_PUBLICATION, Applicability(source_ids=frozenset({HOUSEHOLDS_OM_PUBLICATION.series_id})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            HOUSEHOLDS_OM_PUBLICATION, Applicability(source_ids=frozenset({HOUSEHOLDS_OM_PUBLICATION.series_id})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            HOUSEHOLDS_OM_PUBLICATION, Applicability(source_ids=frozenset({HOUSEHOLDS_OM_PUBLICATION.series_id})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            HOUSEHOLDS_OM_PUBLICATION, Applicability(source_ids=frozenset({HOUSEHOLDS_OM_PUBLICATION.series_id})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement(HOUSEHOLDS_OM_PUBLICATION.series_id, HOUSEHOLDS_OM_PUBLICATION.formats, issue_required=HOUSEHOLDS_OM_PUBLICATION.issue_model == 'dated'), Applicability(source_ids=frozenset({HOUSEHOLDS_OM_PUBLICATION.series_id})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement(HOUSEHOLDS_OM_PUBLICATION.series_id, HOUSEHOLDS_OM_PUBLICATION.formats, issue_required=HOUSEHOLDS_OM_PUBLICATION.issue_model == 'dated'), Applicability(source_ids=frozenset({HOUSEHOLDS_OM_PUBLICATION.series_id})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules(HOUSEHOLDS_OM_PUBLICATION.series_id), Applicability(source_ids=frozenset({HOUSEHOLDS_OM_PUBLICATION.series_id})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            HOUSEHOLDS_OM_TABLE, Applicability(source_ids=frozenset({HOUSEHOLDS_OM_PUBLICATION.series_id})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            HOUSEHOLDS_OM_TABLE, Applicability(source_ids=frozenset({HOUSEHOLDS_OM_PUBLICATION.series_id})),
        ),
    }),
)

