"""Explicit Bank of Russia funding source records and action settings."""
from types import MappingProxyType
from stratbox.capabilities.model.domains import SeriesSpec, CommandSpec, Applicability
from stratbox.capabilities.model.methods import MethodRef
from stratbox.domains.cbr.common.contracts import Publication, Semantics, StatisticalSettings, TableVariant, FormSettings, FamilySettings, SourceRequirement, MappingRules
from stratbox.domains.cbr.common.publications import SORS_INDEX, FORMS_INDEX, ESCROW_INDEX, OFFICES_PAGE, TERRITORIAL_INDEX

FAMILY_ID = 'cbr.funding'

BUDGET_ALL_PUBLICATION = Publication(
    'cbr.funding.budget_all', FAMILY_ID, 'Budget funds',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/banksector/borrowings/02_29_Budget_all.xlsx', None,
)
BUDGET_ALL_TABLE = StatisticalSettings(
    BUDGET_ALL_PUBLICATION.series_id, (
        TableVariant('total', 'итого', 'statistics', 'stock', 'as_of', ('source_geography_or_component', 'denomination_group'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published client funds and budget balances; denominations are separate from measurement currency. Source geography and perimeter editions remain explicit.'),
        TableVariant('rub', 'в\\ рублях', 'statistics', 'stock', 'as_of', ('source_geography_or_component', 'denomination_group'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published client funds and budget balances; denominations are separate from measurement currency. Source geography and perimeter editions remain explicit.'),
        TableVariant('fx', 'в\\ инвалюте', 'statistics', 'stock', 'as_of', ('source_geography_or_component', 'denomination_group'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published client funds and budget balances; denominations are separate from measurement currency. Source geography and perimeter editions remain explicit.'),
    ),
)
BUDGET_ALL = SeriesSpec(
    id=BUDGET_ALL_PUBLICATION.series_id,
    publication=BUDGET_ALL_PUBLICATION,
    semantics=Semantics('publisher_defined', ('publication', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            BUDGET_ALL_PUBLICATION, Applicability(source_ids=frozenset({BUDGET_ALL_PUBLICATION.series_id})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            BUDGET_ALL_PUBLICATION, Applicability(source_ids=frozenset({BUDGET_ALL_PUBLICATION.series_id})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            BUDGET_ALL_PUBLICATION, Applicability(source_ids=frozenset({BUDGET_ALL_PUBLICATION.series_id})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            BUDGET_ALL_PUBLICATION, Applicability(source_ids=frozenset({BUDGET_ALL_PUBLICATION.series_id})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement(BUDGET_ALL_PUBLICATION.series_id, BUDGET_ALL_PUBLICATION.formats, issue_required=BUDGET_ALL_PUBLICATION.issue_model == 'dated', locator=BUDGET_ALL_PUBLICATION.locator, filename_pattern=BUDGET_ALL_PUBLICATION.filename_pattern, publication_kind=BUDGET_ALL_PUBLICATION.kind), Applicability(source_ids=frozenset({BUDGET_ALL_PUBLICATION.series_id})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement(BUDGET_ALL_PUBLICATION.series_id, BUDGET_ALL_PUBLICATION.formats, issue_required=BUDGET_ALL_PUBLICATION.issue_model == 'dated', locator=BUDGET_ALL_PUBLICATION.locator, filename_pattern=BUDGET_ALL_PUBLICATION.filename_pattern, publication_kind=BUDGET_ALL_PUBLICATION.kind), Applicability(source_ids=frozenset({BUDGET_ALL_PUBLICATION.series_id})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules(BUDGET_ALL_PUBLICATION.series_id), Applicability(source_ids=frozenset({BUDGET_ALL_PUBLICATION.series_id})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            BUDGET_ALL_TABLE, Applicability(source_ids=frozenset({BUDGET_ALL_PUBLICATION.series_id})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            BUDGET_ALL_TABLE, Applicability(source_ids=frozenset({BUDGET_ALL_PUBLICATION.series_id})),
        ),
    }),
)

DEP_CORP_PUBLICATION = Publication(
    'cbr.funding.dep_corp', FAMILY_ID, 'Corporate deposits excluding individual entrepreneurs',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Borrowings/02_05_Dep_corp.xlsx', None,
)
DEP_CORP_TABLE = StatisticalSettings(
    DEP_CORP_PUBLICATION.series_id, (
        TableVariant('total', 'итого', 'statistics', 'stock', 'as_of', ('source_geography_or_component', 'denomination_group'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published client funds and budget balances; denominations are separate from measurement currency. Source geography and perimeter editions remain explicit.'),
        TableVariant('rub', 'в\\ рублях', 'statistics', 'stock', 'as_of', ('source_geography_or_component', 'denomination_group'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published client funds and budget balances; denominations are separate from measurement currency. Source geography and perimeter editions remain explicit.'),
        TableVariant('fx', 'в\\ инвалюте', 'statistics', 'stock', 'as_of', ('source_geography_or_component', 'denomination_group'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published client funds and budget balances; denominations are separate from measurement currency. Source geography and perimeter editions remain explicit.'),
    ),
)
DEP_CORP = SeriesSpec(
    id=DEP_CORP_PUBLICATION.series_id,
    publication=DEP_CORP_PUBLICATION,
    semantics=Semantics('publisher_defined', ('publication', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            DEP_CORP_PUBLICATION, Applicability(source_ids=frozenset({DEP_CORP_PUBLICATION.series_id})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            DEP_CORP_PUBLICATION, Applicability(source_ids=frozenset({DEP_CORP_PUBLICATION.series_id})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            DEP_CORP_PUBLICATION, Applicability(source_ids=frozenset({DEP_CORP_PUBLICATION.series_id})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            DEP_CORP_PUBLICATION, Applicability(source_ids=frozenset({DEP_CORP_PUBLICATION.series_id})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement(DEP_CORP_PUBLICATION.series_id, DEP_CORP_PUBLICATION.formats, issue_required=DEP_CORP_PUBLICATION.issue_model == 'dated', locator=DEP_CORP_PUBLICATION.locator, filename_pattern=DEP_CORP_PUBLICATION.filename_pattern, publication_kind=DEP_CORP_PUBLICATION.kind), Applicability(source_ids=frozenset({DEP_CORP_PUBLICATION.series_id})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement(DEP_CORP_PUBLICATION.series_id, DEP_CORP_PUBLICATION.formats, issue_required=DEP_CORP_PUBLICATION.issue_model == 'dated', locator=DEP_CORP_PUBLICATION.locator, filename_pattern=DEP_CORP_PUBLICATION.filename_pattern, publication_kind=DEP_CORP_PUBLICATION.kind), Applicability(source_ids=frozenset({DEP_CORP_PUBLICATION.series_id})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules(DEP_CORP_PUBLICATION.series_id), Applicability(source_ids=frozenset({DEP_CORP_PUBLICATION.series_id})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            DEP_CORP_TABLE, Applicability(source_ids=frozenset({DEP_CORP_PUBLICATION.series_id})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            DEP_CORP_TABLE, Applicability(source_ids=frozenset({DEP_CORP_PUBLICATION.series_id})),
        ),
    }),
)

DEP_ENTREPRENEUR_PUBLICATION = Publication(
    'cbr.funding.dep_entrepreneur', FAMILY_ID, 'Individual entrepreneur funds',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Borrowings/02_07_Dep_enterpreneur.xlsx', None,
)
DEP_ENTREPRENEUR_TABLE = StatisticalSettings(
    DEP_ENTREPRENEUR_PUBLICATION.series_id, (
        TableVariant('total', 'итого', 'statistics', 'stock', 'as_of', ('source_geography_or_component', 'denomination_group'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published client funds and budget balances; denominations are separate from measurement currency. Source geography and perimeter editions remain explicit.'),
        TableVariant('rub', 'в\\ рублях', 'statistics', 'stock', 'as_of', ('source_geography_or_component', 'denomination_group'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published client funds and budget balances; denominations are separate from measurement currency. Source geography and perimeter editions remain explicit.'),
        TableVariant('fx', 'в\\ инвалюте', 'statistics', 'stock', 'as_of', ('source_geography_or_component', 'denomination_group'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published client funds and budget balances; denominations are separate from measurement currency. Source geography and perimeter editions remain explicit.'),
    ),
)
DEP_ENTREPRENEUR = SeriesSpec(
    id=DEP_ENTREPRENEUR_PUBLICATION.series_id,
    publication=DEP_ENTREPRENEUR_PUBLICATION,
    semantics=Semantics('publisher_defined', ('publication', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            DEP_ENTREPRENEUR_PUBLICATION, Applicability(source_ids=frozenset({DEP_ENTREPRENEUR_PUBLICATION.series_id})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            DEP_ENTREPRENEUR_PUBLICATION, Applicability(source_ids=frozenset({DEP_ENTREPRENEUR_PUBLICATION.series_id})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            DEP_ENTREPRENEUR_PUBLICATION, Applicability(source_ids=frozenset({DEP_ENTREPRENEUR_PUBLICATION.series_id})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            DEP_ENTREPRENEUR_PUBLICATION, Applicability(source_ids=frozenset({DEP_ENTREPRENEUR_PUBLICATION.series_id})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement(DEP_ENTREPRENEUR_PUBLICATION.series_id, DEP_ENTREPRENEUR_PUBLICATION.formats, issue_required=DEP_ENTREPRENEUR_PUBLICATION.issue_model == 'dated', locator=DEP_ENTREPRENEUR_PUBLICATION.locator, filename_pattern=DEP_ENTREPRENEUR_PUBLICATION.filename_pattern, publication_kind=DEP_ENTREPRENEUR_PUBLICATION.kind), Applicability(source_ids=frozenset({DEP_ENTREPRENEUR_PUBLICATION.series_id})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement(DEP_ENTREPRENEUR_PUBLICATION.series_id, DEP_ENTREPRENEUR_PUBLICATION.formats, issue_required=DEP_ENTREPRENEUR_PUBLICATION.issue_model == 'dated', locator=DEP_ENTREPRENEUR_PUBLICATION.locator, filename_pattern=DEP_ENTREPRENEUR_PUBLICATION.filename_pattern, publication_kind=DEP_ENTREPRENEUR_PUBLICATION.kind), Applicability(source_ids=frozenset({DEP_ENTREPRENEUR_PUBLICATION.series_id})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules(DEP_ENTREPRENEUR_PUBLICATION.series_id), Applicability(source_ids=frozenset({DEP_ENTREPRENEUR_PUBLICATION.series_id})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            DEP_ENTREPRENEUR_TABLE, Applicability(source_ids=frozenset({DEP_ENTREPRENEUR_PUBLICATION.series_id})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            DEP_ENTREPRENEUR_TABLE, Applicability(source_ids=frozenset({DEP_ENTREPRENEUR_PUBLICATION.series_id})),
        ),
    }),
)

DEP_IND_PUBLICATION = Publication(
    'cbr.funding.dep_ind', FAMILY_ID, 'Household deposits and funds including escrow',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Borrowings/02_06_Dep_ind.xlsx', None,
)
DEP_IND_TABLE = StatisticalSettings(
    DEP_IND_PUBLICATION.series_id, (
        TableVariant('total', 'итого', 'statistics', 'stock', 'as_of', ('source_geography_or_component', 'denomination_group'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published client funds and budget balances; denominations are separate from measurement currency. Source geography and perimeter editions remain explicit.'),
        TableVariant('rub', 'в\\ рублях', 'statistics', 'stock', 'as_of', ('source_geography_or_component', 'denomination_group'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published client funds and budget balances; denominations are separate from measurement currency. Source geography and perimeter editions remain explicit.'),
        TableVariant('fx', 'в\\ инвалюте', 'statistics', 'stock', 'as_of', ('source_geography_or_component', 'denomination_group'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published client funds and budget balances; denominations are separate from measurement currency. Source geography and perimeter editions remain explicit.'),
    ),
)
DEP_IND = SeriesSpec(
    id=DEP_IND_PUBLICATION.series_id,
    publication=DEP_IND_PUBLICATION,
    semantics=Semantics('publisher_defined', ('publication', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            DEP_IND_PUBLICATION, Applicability(source_ids=frozenset({DEP_IND_PUBLICATION.series_id})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            DEP_IND_PUBLICATION, Applicability(source_ids=frozenset({DEP_IND_PUBLICATION.series_id})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            DEP_IND_PUBLICATION, Applicability(source_ids=frozenset({DEP_IND_PUBLICATION.series_id})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            DEP_IND_PUBLICATION, Applicability(source_ids=frozenset({DEP_IND_PUBLICATION.series_id})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement(DEP_IND_PUBLICATION.series_id, DEP_IND_PUBLICATION.formats, issue_required=DEP_IND_PUBLICATION.issue_model == 'dated', locator=DEP_IND_PUBLICATION.locator, filename_pattern=DEP_IND_PUBLICATION.filename_pattern, publication_kind=DEP_IND_PUBLICATION.kind), Applicability(source_ids=frozenset({DEP_IND_PUBLICATION.series_id})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement(DEP_IND_PUBLICATION.series_id, DEP_IND_PUBLICATION.formats, issue_required=DEP_IND_PUBLICATION.issue_model == 'dated', locator=DEP_IND_PUBLICATION.locator, filename_pattern=DEP_IND_PUBLICATION.filename_pattern, publication_kind=DEP_IND_PUBLICATION.kind), Applicability(source_ids=frozenset({DEP_IND_PUBLICATION.series_id})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules(DEP_IND_PUBLICATION.series_id), Applicability(source_ids=frozenset({DEP_IND_PUBLICATION.series_id})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            DEP_IND_TABLE, Applicability(source_ids=frozenset({DEP_IND_PUBLICATION.series_id})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            DEP_IND_TABLE, Applicability(source_ids=frozenset({DEP_IND_PUBLICATION.series_id})),
        ),
    }),
)

DEP_IND_NO_ESCROW_PUBLICATION = Publication(
    'cbr.funding.dep_ind_no_escrow', FAMILY_ID, 'Household deposits excluding escrow',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/banksector/borrowings/02_27_Dep_ind_excluding_escrow.xlsx', None,
)
DEP_IND_NO_ESCROW_TABLE = StatisticalSettings(
    DEP_IND_NO_ESCROW_PUBLICATION.series_id, (
        TableVariant('total', 'итого', 'statistics', 'stock', 'as_of', ('source_geography_or_component', 'denomination_group'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published client funds and budget balances; denominations are separate from measurement currency. Source geography and perimeter editions remain explicit.'),
        TableVariant('rub', 'в\\ рублях', 'statistics', 'stock', 'as_of', ('source_geography_or_component', 'denomination_group'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published client funds and budget balances; denominations are separate from measurement currency. Source geography and perimeter editions remain explicit.'),
        TableVariant('fx', 'в\\ инвалюте', 'statistics', 'stock', 'as_of', ('source_geography_or_component', 'denomination_group'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published client funds and budget balances; denominations are separate from measurement currency. Source geography and perimeter editions remain explicit.'),
    ),
)
DEP_IND_NO_ESCROW = SeriesSpec(
    id=DEP_IND_NO_ESCROW_PUBLICATION.series_id,
    publication=DEP_IND_NO_ESCROW_PUBLICATION,
    semantics=Semantics('publisher_defined', ('publication', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            DEP_IND_NO_ESCROW_PUBLICATION, Applicability(source_ids=frozenset({DEP_IND_NO_ESCROW_PUBLICATION.series_id})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            DEP_IND_NO_ESCROW_PUBLICATION, Applicability(source_ids=frozenset({DEP_IND_NO_ESCROW_PUBLICATION.series_id})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            DEP_IND_NO_ESCROW_PUBLICATION, Applicability(source_ids=frozenset({DEP_IND_NO_ESCROW_PUBLICATION.series_id})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            DEP_IND_NO_ESCROW_PUBLICATION, Applicability(source_ids=frozenset({DEP_IND_NO_ESCROW_PUBLICATION.series_id})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement(DEP_IND_NO_ESCROW_PUBLICATION.series_id, DEP_IND_NO_ESCROW_PUBLICATION.formats, issue_required=DEP_IND_NO_ESCROW_PUBLICATION.issue_model == 'dated', locator=DEP_IND_NO_ESCROW_PUBLICATION.locator, filename_pattern=DEP_IND_NO_ESCROW_PUBLICATION.filename_pattern, publication_kind=DEP_IND_NO_ESCROW_PUBLICATION.kind), Applicability(source_ids=frozenset({DEP_IND_NO_ESCROW_PUBLICATION.series_id})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement(DEP_IND_NO_ESCROW_PUBLICATION.series_id, DEP_IND_NO_ESCROW_PUBLICATION.formats, issue_required=DEP_IND_NO_ESCROW_PUBLICATION.issue_model == 'dated', locator=DEP_IND_NO_ESCROW_PUBLICATION.locator, filename_pattern=DEP_IND_NO_ESCROW_PUBLICATION.filename_pattern, publication_kind=DEP_IND_NO_ESCROW_PUBLICATION.kind), Applicability(source_ids=frozenset({DEP_IND_NO_ESCROW_PUBLICATION.series_id})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules(DEP_IND_NO_ESCROW_PUBLICATION.series_id), Applicability(source_ids=frozenset({DEP_IND_NO_ESCROW_PUBLICATION.series_id})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            DEP_IND_NO_ESCROW_TABLE, Applicability(source_ids=frozenset({DEP_IND_NO_ESCROW_PUBLICATION.series_id})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            DEP_IND_NO_ESCROW_TABLE, Applicability(source_ids=frozenset({DEP_IND_NO_ESCROW_PUBLICATION.series_id})),
        ),
    }),
)

ESCROW_ACCOUNTS_PUBLICATION = Publication(
    'cbr.funding.escrow_accounts', FAMILY_ID, 'Escrow account balances',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/banksector/borrowings/02_28_Escrow_accounts.xlsx', None,
)
ESCROW_ACCOUNTS_TABLE = StatisticalSettings(
    ESCROW_ACCOUNTS_PUBLICATION.series_id, (
        TableVariant('rub', 'в\\ рублях', 'statistics', 'stock', 'as_of', ('source_geography_or_component', 'denomination_group'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published client funds and budget balances; denominations are separate from measurement currency. Source geography and perimeter editions remain explicit.'),
    ),
)
ESCROW_ACCOUNTS = SeriesSpec(
    id=ESCROW_ACCOUNTS_PUBLICATION.series_id,
    publication=ESCROW_ACCOUNTS_PUBLICATION,
    semantics=Semantics('publisher_defined', ('publication', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            ESCROW_ACCOUNTS_PUBLICATION, Applicability(source_ids=frozenset({ESCROW_ACCOUNTS_PUBLICATION.series_id})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            ESCROW_ACCOUNTS_PUBLICATION, Applicability(source_ids=frozenset({ESCROW_ACCOUNTS_PUBLICATION.series_id})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            ESCROW_ACCOUNTS_PUBLICATION, Applicability(source_ids=frozenset({ESCROW_ACCOUNTS_PUBLICATION.series_id})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            ESCROW_ACCOUNTS_PUBLICATION, Applicability(source_ids=frozenset({ESCROW_ACCOUNTS_PUBLICATION.series_id})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement(ESCROW_ACCOUNTS_PUBLICATION.series_id, ESCROW_ACCOUNTS_PUBLICATION.formats, issue_required=ESCROW_ACCOUNTS_PUBLICATION.issue_model == 'dated', locator=ESCROW_ACCOUNTS_PUBLICATION.locator, filename_pattern=ESCROW_ACCOUNTS_PUBLICATION.filename_pattern, publication_kind=ESCROW_ACCOUNTS_PUBLICATION.kind), Applicability(source_ids=frozenset({ESCROW_ACCOUNTS_PUBLICATION.series_id})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement(ESCROW_ACCOUNTS_PUBLICATION.series_id, ESCROW_ACCOUNTS_PUBLICATION.formats, issue_required=ESCROW_ACCOUNTS_PUBLICATION.issue_model == 'dated', locator=ESCROW_ACCOUNTS_PUBLICATION.locator, filename_pattern=ESCROW_ACCOUNTS_PUBLICATION.filename_pattern, publication_kind=ESCROW_ACCOUNTS_PUBLICATION.kind), Applicability(source_ids=frozenset({ESCROW_ACCOUNTS_PUBLICATION.series_id})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules(ESCROW_ACCOUNTS_PUBLICATION.series_id), Applicability(source_ids=frozenset({ESCROW_ACCOUNTS_PUBLICATION.series_id})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            ESCROW_ACCOUNTS_TABLE, Applicability(source_ids=frozenset({ESCROW_ACCOUNTS_PUBLICATION.series_id})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            ESCROW_ACCOUNTS_TABLE, Applicability(source_ids=frozenset({ESCROW_ACCOUNTS_PUBLICATION.series_id})),
        ),
    }),
)

FUNDS_ALL_PUBLICATION = Publication(
    'cbr.funding.funds_all', FAMILY_ID, 'Client funds by published component',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Borrowings/02_01_Funds_all.xlsx', None,
)
FUNDS_ALL_TABLE = StatisticalSettings(
    FUNDS_ALL_PUBLICATION.series_id, (
        TableVariant('total', 'итого', 'statistics', 'stock', 'as_of', ('source_geography_or_component', 'denomination_group'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published client funds and budget balances; denominations are separate from measurement currency. Source geography and perimeter editions remain explicit.'),
        TableVariant('rub', 'в\\ рублях', 'statistics', 'stock', 'as_of', ('source_geography_or_component', 'denomination_group'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published client funds and budget balances; denominations are separate from measurement currency. Source geography and perimeter editions remain explicit.'),
        TableVariant('fx', 'в\\ инвалюте', 'statistics', 'stock', 'as_of', ('source_geography_or_component', 'denomination_group'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published client funds and budget balances; denominations are separate from measurement currency. Source geography and perimeter editions remain explicit.'),
    ),
)
FUNDS_ALL = SeriesSpec(
    id=FUNDS_ALL_PUBLICATION.series_id,
    publication=FUNDS_ALL_PUBLICATION,
    semantics=Semantics('publisher_defined', ('publication', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            FUNDS_ALL_PUBLICATION, Applicability(source_ids=frozenset({FUNDS_ALL_PUBLICATION.series_id})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            FUNDS_ALL_PUBLICATION, Applicability(source_ids=frozenset({FUNDS_ALL_PUBLICATION.series_id})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            FUNDS_ALL_PUBLICATION, Applicability(source_ids=frozenset({FUNDS_ALL_PUBLICATION.series_id})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            FUNDS_ALL_PUBLICATION, Applicability(source_ids=frozenset({FUNDS_ALL_PUBLICATION.series_id})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement(FUNDS_ALL_PUBLICATION.series_id, FUNDS_ALL_PUBLICATION.formats, issue_required=FUNDS_ALL_PUBLICATION.issue_model == 'dated', locator=FUNDS_ALL_PUBLICATION.locator, filename_pattern=FUNDS_ALL_PUBLICATION.filename_pattern, publication_kind=FUNDS_ALL_PUBLICATION.kind), Applicability(source_ids=frozenset({FUNDS_ALL_PUBLICATION.series_id})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement(FUNDS_ALL_PUBLICATION.series_id, FUNDS_ALL_PUBLICATION.formats, issue_required=FUNDS_ALL_PUBLICATION.issue_model == 'dated', locator=FUNDS_ALL_PUBLICATION.locator, filename_pattern=FUNDS_ALL_PUBLICATION.filename_pattern, publication_kind=FUNDS_ALL_PUBLICATION.kind), Applicability(source_ids=frozenset({FUNDS_ALL_PUBLICATION.series_id})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules(FUNDS_ALL_PUBLICATION.series_id), Applicability(source_ids=frozenset({FUNDS_ALL_PUBLICATION.series_id})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            FUNDS_ALL_TABLE, Applicability(source_ids=frozenset({FUNDS_ALL_PUBLICATION.series_id})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            FUNDS_ALL_TABLE, Applicability(source_ids=frozenset({FUNDS_ALL_PUBLICATION.series_id})),
        ),
    }),
)

FUNDS_CLIENTS_PUBLICATION = Publication(
    'cbr.funding.funds_clients', FAMILY_ID, 'Client funds',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Borrowings/02_02_Funds_clients.xlsx', None,
)
FUNDS_CLIENTS_TABLE = StatisticalSettings(
    FUNDS_CLIENTS_PUBLICATION.series_id, (
        TableVariant('total', 'итого', 'statistics', 'stock', 'as_of', ('source_geography_or_component', 'denomination_group'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published client funds and budget balances; denominations are separate from measurement currency. Source geography and perimeter editions remain explicit.'),
        TableVariant('rub', 'в\\ рублях', 'statistics', 'stock', 'as_of', ('source_geography_or_component', 'denomination_group'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published client funds and budget balances; denominations are separate from measurement currency. Source geography and perimeter editions remain explicit.'),
        TableVariant('fx', 'в\\ инвалюте', 'statistics', 'stock', 'as_of', ('source_geography_or_component', 'denomination_group'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published client funds and budget balances; denominations are separate from measurement currency. Source geography and perimeter editions remain explicit.'),
    ),
)
FUNDS_CLIENTS = SeriesSpec(
    id=FUNDS_CLIENTS_PUBLICATION.series_id,
    publication=FUNDS_CLIENTS_PUBLICATION,
    semantics=Semantics('publisher_defined', ('publication', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            FUNDS_CLIENTS_PUBLICATION, Applicability(source_ids=frozenset({FUNDS_CLIENTS_PUBLICATION.series_id})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            FUNDS_CLIENTS_PUBLICATION, Applicability(source_ids=frozenset({FUNDS_CLIENTS_PUBLICATION.series_id})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            FUNDS_CLIENTS_PUBLICATION, Applicability(source_ids=frozenset({FUNDS_CLIENTS_PUBLICATION.series_id})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            FUNDS_CLIENTS_PUBLICATION, Applicability(source_ids=frozenset({FUNDS_CLIENTS_PUBLICATION.series_id})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement(FUNDS_CLIENTS_PUBLICATION.series_id, FUNDS_CLIENTS_PUBLICATION.formats, issue_required=FUNDS_CLIENTS_PUBLICATION.issue_model == 'dated', locator=FUNDS_CLIENTS_PUBLICATION.locator, filename_pattern=FUNDS_CLIENTS_PUBLICATION.filename_pattern, publication_kind=FUNDS_CLIENTS_PUBLICATION.kind), Applicability(source_ids=frozenset({FUNDS_CLIENTS_PUBLICATION.series_id})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement(FUNDS_CLIENTS_PUBLICATION.series_id, FUNDS_CLIENTS_PUBLICATION.formats, issue_required=FUNDS_CLIENTS_PUBLICATION.issue_model == 'dated', locator=FUNDS_CLIENTS_PUBLICATION.locator, filename_pattern=FUNDS_CLIENTS_PUBLICATION.filename_pattern, publication_kind=FUNDS_CLIENTS_PUBLICATION.kind), Applicability(source_ids=frozenset({FUNDS_CLIENTS_PUBLICATION.series_id})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules(FUNDS_CLIENTS_PUBLICATION.series_id), Applicability(source_ids=frozenset({FUNDS_CLIENTS_PUBLICATION.series_id})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            FUNDS_CLIENTS_TABLE, Applicability(source_ids=frozenset({FUNDS_CLIENTS_PUBLICATION.series_id})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            FUNDS_CLIENTS_TABLE, Applicability(source_ids=frozenset({FUNDS_CLIENTS_PUBLICATION.series_id})),
        ),
    }),
)

FUNDS_ORG_PUBLICATION = Publication(
    'cbr.funding.funds_org', FAMILY_ID, 'Organization funds',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Borrowings/02_04_Funds_org.xlsx', None,
)
FUNDS_ORG_TABLE = StatisticalSettings(
    FUNDS_ORG_PUBLICATION.series_id, (
        TableVariant('total', 'итого', 'statistics', 'stock', 'as_of', ('source_geography_or_component', 'denomination_group'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published client funds and budget balances; denominations are separate from measurement currency. Source geography and perimeter editions remain explicit.'),
        TableVariant('rub', 'в\\ рублях', 'statistics', 'stock', 'as_of', ('source_geography_or_component', 'denomination_group'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published client funds and budget balances; denominations are separate from measurement currency. Source geography and perimeter editions remain explicit.'),
        TableVariant('fx', 'в\\ инвалюте', 'statistics', 'stock', 'as_of', ('source_geography_or_component', 'denomination_group'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published client funds and budget balances; denominations are separate from measurement currency. Source geography and perimeter editions remain explicit.'),
    ),
)
FUNDS_ORG = SeriesSpec(
    id=FUNDS_ORG_PUBLICATION.series_id,
    publication=FUNDS_ORG_PUBLICATION,
    semantics=Semantics('publisher_defined', ('publication', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            FUNDS_ORG_PUBLICATION, Applicability(source_ids=frozenset({FUNDS_ORG_PUBLICATION.series_id})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            FUNDS_ORG_PUBLICATION, Applicability(source_ids=frozenset({FUNDS_ORG_PUBLICATION.series_id})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            FUNDS_ORG_PUBLICATION, Applicability(source_ids=frozenset({FUNDS_ORG_PUBLICATION.series_id})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            FUNDS_ORG_PUBLICATION, Applicability(source_ids=frozenset({FUNDS_ORG_PUBLICATION.series_id})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement(FUNDS_ORG_PUBLICATION.series_id, FUNDS_ORG_PUBLICATION.formats, issue_required=FUNDS_ORG_PUBLICATION.issue_model == 'dated', locator=FUNDS_ORG_PUBLICATION.locator, filename_pattern=FUNDS_ORG_PUBLICATION.filename_pattern, publication_kind=FUNDS_ORG_PUBLICATION.kind), Applicability(source_ids=frozenset({FUNDS_ORG_PUBLICATION.series_id})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement(FUNDS_ORG_PUBLICATION.series_id, FUNDS_ORG_PUBLICATION.formats, issue_required=FUNDS_ORG_PUBLICATION.issue_model == 'dated', locator=FUNDS_ORG_PUBLICATION.locator, filename_pattern=FUNDS_ORG_PUBLICATION.filename_pattern, publication_kind=FUNDS_ORG_PUBLICATION.kind), Applicability(source_ids=frozenset({FUNDS_ORG_PUBLICATION.series_id})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules(FUNDS_ORG_PUBLICATION.series_id), Applicability(source_ids=frozenset({FUNDS_ORG_PUBLICATION.series_id})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            FUNDS_ORG_TABLE, Applicability(source_ids=frozenset({FUNDS_ORG_PUBLICATION.series_id})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            FUNDS_ORG_TABLE, Applicability(source_ids=frozenset({FUNDS_ORG_PUBLICATION.series_id})),
        ),
    }),
)

