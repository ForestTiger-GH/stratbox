"""Explicit Bank of Russia funding source records and action settings."""
from types import MappingProxyType
from stratbox.capabilities.model.domains import SeriesSpec, CommandSpec, Applicability
from stratbox.capabilities.model.methods import MethodRef
from stratbox.domains.cbr.common.contracts import Publication, Semantics, StatisticalSettings, TableVariant, FormSettings, FamilySettings, SourceRequirement, MappingRules
from stratbox.domains.cbr.common.publications import SORS_INDEX, FORMS_INDEX, ESCROW_INDEX, OFFICES_PAGE, TERRITORIAL_INDEX

BUDGET_ALL_PUBLICATION = Publication(
    'cbr.funding.budget_all', 'cbr.funding', 'Budget funds',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/banksector/borrowings/02_29_Budget_all.xlsx', None,
)
BUDGET_ALL_TABLE = StatisticalSettings(
    'cbr.funding.budget_all', (
        TableVariant('total', 'итого', 'statistics', 'stock', 'as_of', ('source_geography_or_component', 'denomination_group'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published client funds and budget balances; denominations are separate from measurement currency. Source geography and perimeter editions remain explicit.'),
        TableVariant('rub', 'в\\ рублях', 'statistics', 'stock', 'as_of', ('source_geography_or_component', 'denomination_group'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published client funds and budget balances; denominations are separate from measurement currency. Source geography and perimeter editions remain explicit.'),
        TableVariant('fx', 'в\\ инвалюте', 'statistics', 'stock', 'as_of', ('source_geography_or_component', 'denomination_group'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published client funds and budget balances; denominations are separate from measurement currency. Source geography and perimeter editions remain explicit.'),
    ),
)
BUDGET_ALL = SeriesSpec(
    id='cbr.funding.budget_all',
    publication=BUDGET_ALL_PUBLICATION,
    semantics=Semantics('publisher_defined', ('publication', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            BUDGET_ALL_PUBLICATION, Applicability(source_ids=frozenset({'cbr.funding.budget_all'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            BUDGET_ALL_PUBLICATION, Applicability(source_ids=frozenset({'cbr.funding.budget_all'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            BUDGET_ALL_PUBLICATION, Applicability(source_ids=frozenset({'cbr.funding.budget_all'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            BUDGET_ALL_PUBLICATION, Applicability(source_ids=frozenset({'cbr.funding.budget_all'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.funding.budget_all', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.funding.budget_all'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.funding.budget_all', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.funding.budget_all'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.funding.budget_all'), Applicability(source_ids=frozenset({'cbr.funding.budget_all'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            BUDGET_ALL_TABLE, Applicability(source_ids=frozenset({'cbr.funding.budget_all'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            BUDGET_ALL_TABLE, Applicability(source_ids=frozenset({'cbr.funding.budget_all'})),
        ),
    }),
)

DEP_CORP_PUBLICATION = Publication(
    'cbr.funding.dep_corp', 'cbr.funding', 'Corporate deposits excluding individual entrepreneurs',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Borrowings/02_05_Dep_corp.xlsx', None,
)
DEP_CORP_TABLE = StatisticalSettings(
    'cbr.funding.dep_corp', (
        TableVariant('total', 'итого', 'statistics', 'stock', 'as_of', ('source_geography_or_component', 'denomination_group'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published client funds and budget balances; denominations are separate from measurement currency. Source geography and perimeter editions remain explicit.'),
        TableVariant('rub', 'в\\ рублях', 'statistics', 'stock', 'as_of', ('source_geography_or_component', 'denomination_group'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published client funds and budget balances; denominations are separate from measurement currency. Source geography and perimeter editions remain explicit.'),
        TableVariant('fx', 'в\\ инвалюте', 'statistics', 'stock', 'as_of', ('source_geography_or_component', 'denomination_group'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published client funds and budget balances; denominations are separate from measurement currency. Source geography and perimeter editions remain explicit.'),
    ),
)
DEP_CORP = SeriesSpec(
    id='cbr.funding.dep_corp',
    publication=DEP_CORP_PUBLICATION,
    semantics=Semantics('publisher_defined', ('publication', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            DEP_CORP_PUBLICATION, Applicability(source_ids=frozenset({'cbr.funding.dep_corp'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            DEP_CORP_PUBLICATION, Applicability(source_ids=frozenset({'cbr.funding.dep_corp'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            DEP_CORP_PUBLICATION, Applicability(source_ids=frozenset({'cbr.funding.dep_corp'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            DEP_CORP_PUBLICATION, Applicability(source_ids=frozenset({'cbr.funding.dep_corp'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.funding.dep_corp', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.funding.dep_corp'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.funding.dep_corp', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.funding.dep_corp'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.funding.dep_corp'), Applicability(source_ids=frozenset({'cbr.funding.dep_corp'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            DEP_CORP_TABLE, Applicability(source_ids=frozenset({'cbr.funding.dep_corp'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            DEP_CORP_TABLE, Applicability(source_ids=frozenset({'cbr.funding.dep_corp'})),
        ),
    }),
)

DEP_ENTREPRENEUR_PUBLICATION = Publication(
    'cbr.funding.dep_entrepreneur', 'cbr.funding', 'Individual entrepreneur funds',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Borrowings/02_07_Dep_enterpreneur.xlsx', None,
)
DEP_ENTREPRENEUR_TABLE = StatisticalSettings(
    'cbr.funding.dep_entrepreneur', (
        TableVariant('total', 'итого', 'statistics', 'stock', 'as_of', ('source_geography_or_component', 'denomination_group'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published client funds and budget balances; denominations are separate from measurement currency. Source geography and perimeter editions remain explicit.'),
        TableVariant('rub', 'в\\ рублях', 'statistics', 'stock', 'as_of', ('source_geography_or_component', 'denomination_group'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published client funds and budget balances; denominations are separate from measurement currency. Source geography and perimeter editions remain explicit.'),
        TableVariant('fx', 'в\\ инвалюте', 'statistics', 'stock', 'as_of', ('source_geography_or_component', 'denomination_group'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published client funds and budget balances; denominations are separate from measurement currency. Source geography and perimeter editions remain explicit.'),
    ),
)
DEP_ENTREPRENEUR = SeriesSpec(
    id='cbr.funding.dep_entrepreneur',
    publication=DEP_ENTREPRENEUR_PUBLICATION,
    semantics=Semantics('publisher_defined', ('publication', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            DEP_ENTREPRENEUR_PUBLICATION, Applicability(source_ids=frozenset({'cbr.funding.dep_entrepreneur'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            DEP_ENTREPRENEUR_PUBLICATION, Applicability(source_ids=frozenset({'cbr.funding.dep_entrepreneur'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            DEP_ENTREPRENEUR_PUBLICATION, Applicability(source_ids=frozenset({'cbr.funding.dep_entrepreneur'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            DEP_ENTREPRENEUR_PUBLICATION, Applicability(source_ids=frozenset({'cbr.funding.dep_entrepreneur'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.funding.dep_entrepreneur', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.funding.dep_entrepreneur'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.funding.dep_entrepreneur', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.funding.dep_entrepreneur'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.funding.dep_entrepreneur'), Applicability(source_ids=frozenset({'cbr.funding.dep_entrepreneur'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            DEP_ENTREPRENEUR_TABLE, Applicability(source_ids=frozenset({'cbr.funding.dep_entrepreneur'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            DEP_ENTREPRENEUR_TABLE, Applicability(source_ids=frozenset({'cbr.funding.dep_entrepreneur'})),
        ),
    }),
)

DEP_IND_PUBLICATION = Publication(
    'cbr.funding.dep_ind', 'cbr.funding', 'Household deposits and funds including escrow',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Borrowings/02_06_Dep_ind.xlsx', None,
)
DEP_IND_TABLE = StatisticalSettings(
    'cbr.funding.dep_ind', (
        TableVariant('total', 'итого', 'statistics', 'stock', 'as_of', ('source_geography_or_component', 'denomination_group'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published client funds and budget balances; denominations are separate from measurement currency. Source geography and perimeter editions remain explicit.'),
        TableVariant('rub', 'в\\ рублях', 'statistics', 'stock', 'as_of', ('source_geography_or_component', 'denomination_group'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published client funds and budget balances; denominations are separate from measurement currency. Source geography and perimeter editions remain explicit.'),
        TableVariant('fx', 'в\\ инвалюте', 'statistics', 'stock', 'as_of', ('source_geography_or_component', 'denomination_group'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published client funds and budget balances; denominations are separate from measurement currency. Source geography and perimeter editions remain explicit.'),
    ),
)
DEP_IND = SeriesSpec(
    id='cbr.funding.dep_ind',
    publication=DEP_IND_PUBLICATION,
    semantics=Semantics('publisher_defined', ('publication', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            DEP_IND_PUBLICATION, Applicability(source_ids=frozenset({'cbr.funding.dep_ind'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            DEP_IND_PUBLICATION, Applicability(source_ids=frozenset({'cbr.funding.dep_ind'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            DEP_IND_PUBLICATION, Applicability(source_ids=frozenset({'cbr.funding.dep_ind'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            DEP_IND_PUBLICATION, Applicability(source_ids=frozenset({'cbr.funding.dep_ind'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.funding.dep_ind', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.funding.dep_ind'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.funding.dep_ind', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.funding.dep_ind'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.funding.dep_ind'), Applicability(source_ids=frozenset({'cbr.funding.dep_ind'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            DEP_IND_TABLE, Applicability(source_ids=frozenset({'cbr.funding.dep_ind'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            DEP_IND_TABLE, Applicability(source_ids=frozenset({'cbr.funding.dep_ind'})),
        ),
    }),
)

DEP_IND_NO_ESCROW_PUBLICATION = Publication(
    'cbr.funding.dep_ind_no_escrow', 'cbr.funding', 'Household deposits excluding escrow',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/banksector/borrowings/02_27_Dep_ind_excluding_escrow.xlsx', None,
)
DEP_IND_NO_ESCROW_TABLE = StatisticalSettings(
    'cbr.funding.dep_ind_no_escrow', (
        TableVariant('total', 'итого', 'statistics', 'stock', 'as_of', ('source_geography_or_component', 'denomination_group'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published client funds and budget balances; denominations are separate from measurement currency. Source geography and perimeter editions remain explicit.'),
        TableVariant('rub', 'в\\ рублях', 'statistics', 'stock', 'as_of', ('source_geography_or_component', 'denomination_group'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published client funds and budget balances; denominations are separate from measurement currency. Source geography and perimeter editions remain explicit.'),
        TableVariant('fx', 'в\\ инвалюте', 'statistics', 'stock', 'as_of', ('source_geography_or_component', 'denomination_group'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published client funds and budget balances; denominations are separate from measurement currency. Source geography and perimeter editions remain explicit.'),
    ),
)
DEP_IND_NO_ESCROW = SeriesSpec(
    id='cbr.funding.dep_ind_no_escrow',
    publication=DEP_IND_NO_ESCROW_PUBLICATION,
    semantics=Semantics('publisher_defined', ('publication', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            DEP_IND_NO_ESCROW_PUBLICATION, Applicability(source_ids=frozenset({'cbr.funding.dep_ind_no_escrow'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            DEP_IND_NO_ESCROW_PUBLICATION, Applicability(source_ids=frozenset({'cbr.funding.dep_ind_no_escrow'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            DEP_IND_NO_ESCROW_PUBLICATION, Applicability(source_ids=frozenset({'cbr.funding.dep_ind_no_escrow'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            DEP_IND_NO_ESCROW_PUBLICATION, Applicability(source_ids=frozenset({'cbr.funding.dep_ind_no_escrow'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.funding.dep_ind_no_escrow', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.funding.dep_ind_no_escrow'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.funding.dep_ind_no_escrow', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.funding.dep_ind_no_escrow'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.funding.dep_ind_no_escrow'), Applicability(source_ids=frozenset({'cbr.funding.dep_ind_no_escrow'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            DEP_IND_NO_ESCROW_TABLE, Applicability(source_ids=frozenset({'cbr.funding.dep_ind_no_escrow'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            DEP_IND_NO_ESCROW_TABLE, Applicability(source_ids=frozenset({'cbr.funding.dep_ind_no_escrow'})),
        ),
    }),
)

ESCROW_ACCOUNTS_PUBLICATION = Publication(
    'cbr.funding.escrow_accounts', 'cbr.funding', 'Escrow account balances',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/banksector/borrowings/02_28_Escrow_accounts.xlsx', None,
)
ESCROW_ACCOUNTS_TABLE = StatisticalSettings(
    'cbr.funding.escrow_accounts', (
        TableVariant('rub', 'в\\ рублях', 'statistics', 'stock', 'as_of', ('source_geography_or_component', 'denomination_group'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published client funds and budget balances; denominations are separate from measurement currency. Source geography and perimeter editions remain explicit.'),
    ),
)
ESCROW_ACCOUNTS = SeriesSpec(
    id='cbr.funding.escrow_accounts',
    publication=ESCROW_ACCOUNTS_PUBLICATION,
    semantics=Semantics('publisher_defined', ('publication', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            ESCROW_ACCOUNTS_PUBLICATION, Applicability(source_ids=frozenset({'cbr.funding.escrow_accounts'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            ESCROW_ACCOUNTS_PUBLICATION, Applicability(source_ids=frozenset({'cbr.funding.escrow_accounts'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            ESCROW_ACCOUNTS_PUBLICATION, Applicability(source_ids=frozenset({'cbr.funding.escrow_accounts'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            ESCROW_ACCOUNTS_PUBLICATION, Applicability(source_ids=frozenset({'cbr.funding.escrow_accounts'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.funding.escrow_accounts', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.funding.escrow_accounts'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.funding.escrow_accounts', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.funding.escrow_accounts'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.funding.escrow_accounts'), Applicability(source_ids=frozenset({'cbr.funding.escrow_accounts'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            ESCROW_ACCOUNTS_TABLE, Applicability(source_ids=frozenset({'cbr.funding.escrow_accounts'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            ESCROW_ACCOUNTS_TABLE, Applicability(source_ids=frozenset({'cbr.funding.escrow_accounts'})),
        ),
    }),
)

FUNDS_ALL_PUBLICATION = Publication(
    'cbr.funding.funds_all', 'cbr.funding', 'Client funds by published component',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Borrowings/02_01_Funds_all.xlsx', None,
)
FUNDS_ALL_TABLE = StatisticalSettings(
    'cbr.funding.funds_all', (
        TableVariant('total', 'итого', 'statistics', 'stock', 'as_of', ('source_geography_or_component', 'denomination_group'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published client funds and budget balances; denominations are separate from measurement currency. Source geography and perimeter editions remain explicit.'),
        TableVariant('rub', 'в\\ рублях', 'statistics', 'stock', 'as_of', ('source_geography_or_component', 'denomination_group'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published client funds and budget balances; denominations are separate from measurement currency. Source geography and perimeter editions remain explicit.'),
        TableVariant('fx', 'в\\ инвалюте', 'statistics', 'stock', 'as_of', ('source_geography_or_component', 'denomination_group'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published client funds and budget balances; denominations are separate from measurement currency. Source geography and perimeter editions remain explicit.'),
    ),
)
FUNDS_ALL = SeriesSpec(
    id='cbr.funding.funds_all',
    publication=FUNDS_ALL_PUBLICATION,
    semantics=Semantics('publisher_defined', ('publication', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            FUNDS_ALL_PUBLICATION, Applicability(source_ids=frozenset({'cbr.funding.funds_all'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            FUNDS_ALL_PUBLICATION, Applicability(source_ids=frozenset({'cbr.funding.funds_all'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            FUNDS_ALL_PUBLICATION, Applicability(source_ids=frozenset({'cbr.funding.funds_all'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            FUNDS_ALL_PUBLICATION, Applicability(source_ids=frozenset({'cbr.funding.funds_all'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.funding.funds_all', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.funding.funds_all'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.funding.funds_all', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.funding.funds_all'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.funding.funds_all'), Applicability(source_ids=frozenset({'cbr.funding.funds_all'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            FUNDS_ALL_TABLE, Applicability(source_ids=frozenset({'cbr.funding.funds_all'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            FUNDS_ALL_TABLE, Applicability(source_ids=frozenset({'cbr.funding.funds_all'})),
        ),
    }),
)

FUNDS_CLIENTS_PUBLICATION = Publication(
    'cbr.funding.funds_clients', 'cbr.funding', 'Client funds',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Borrowings/02_02_Funds_clients.xlsx', None,
)
FUNDS_CLIENTS_TABLE = StatisticalSettings(
    'cbr.funding.funds_clients', (
        TableVariant('total', 'итого', 'statistics', 'stock', 'as_of', ('source_geography_or_component', 'denomination_group'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published client funds and budget balances; denominations are separate from measurement currency. Source geography and perimeter editions remain explicit.'),
        TableVariant('rub', 'в\\ рублях', 'statistics', 'stock', 'as_of', ('source_geography_or_component', 'denomination_group'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published client funds and budget balances; denominations are separate from measurement currency. Source geography and perimeter editions remain explicit.'),
        TableVariant('fx', 'в\\ инвалюте', 'statistics', 'stock', 'as_of', ('source_geography_or_component', 'denomination_group'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published client funds and budget balances; denominations are separate from measurement currency. Source geography and perimeter editions remain explicit.'),
    ),
)
FUNDS_CLIENTS = SeriesSpec(
    id='cbr.funding.funds_clients',
    publication=FUNDS_CLIENTS_PUBLICATION,
    semantics=Semantics('publisher_defined', ('publication', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            FUNDS_CLIENTS_PUBLICATION, Applicability(source_ids=frozenset({'cbr.funding.funds_clients'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            FUNDS_CLIENTS_PUBLICATION, Applicability(source_ids=frozenset({'cbr.funding.funds_clients'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            FUNDS_CLIENTS_PUBLICATION, Applicability(source_ids=frozenset({'cbr.funding.funds_clients'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            FUNDS_CLIENTS_PUBLICATION, Applicability(source_ids=frozenset({'cbr.funding.funds_clients'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.funding.funds_clients', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.funding.funds_clients'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.funding.funds_clients', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.funding.funds_clients'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.funding.funds_clients'), Applicability(source_ids=frozenset({'cbr.funding.funds_clients'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            FUNDS_CLIENTS_TABLE, Applicability(source_ids=frozenset({'cbr.funding.funds_clients'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            FUNDS_CLIENTS_TABLE, Applicability(source_ids=frozenset({'cbr.funding.funds_clients'})),
        ),
    }),
)

FUNDS_ORG_PUBLICATION = Publication(
    'cbr.funding.funds_org', 'cbr.funding', 'Organization funds',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Borrowings/02_04_Funds_org.xlsx', None,
)
FUNDS_ORG_TABLE = StatisticalSettings(
    'cbr.funding.funds_org', (
        TableVariant('total', 'итого', 'statistics', 'stock', 'as_of', ('source_geography_or_component', 'denomination_group'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published client funds and budget balances; denominations are separate from measurement currency. Source geography and perimeter editions remain explicit.'),
        TableVariant('rub', 'в\\ рублях', 'statistics', 'stock', 'as_of', ('source_geography_or_component', 'denomination_group'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published client funds and budget balances; denominations are separate from measurement currency. Source geography and perimeter editions remain explicit.'),
        TableVariant('fx', 'в\\ инвалюте', 'statistics', 'stock', 'as_of', ('source_geography_or_component', 'denomination_group'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published client funds and budget balances; denominations are separate from measurement currency. Source geography and perimeter editions remain explicit.'),
    ),
)
FUNDS_ORG = SeriesSpec(
    id='cbr.funding.funds_org',
    publication=FUNDS_ORG_PUBLICATION,
    semantics=Semantics('publisher_defined', ('publication', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            FUNDS_ORG_PUBLICATION, Applicability(source_ids=frozenset({'cbr.funding.funds_org'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            FUNDS_ORG_PUBLICATION, Applicability(source_ids=frozenset({'cbr.funding.funds_org'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            FUNDS_ORG_PUBLICATION, Applicability(source_ids=frozenset({'cbr.funding.funds_org'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            FUNDS_ORG_PUBLICATION, Applicability(source_ids=frozenset({'cbr.funding.funds_org'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.funding.funds_org', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.funding.funds_org'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.funding.funds_org', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.funding.funds_org'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.funding.funds_org'), Applicability(source_ids=frozenset({'cbr.funding.funds_org'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            FUNDS_ORG_TABLE, Applicability(source_ids=frozenset({'cbr.funding.funds_org'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            FUNDS_ORG_TABLE, Applicability(source_ids=frozenset({'cbr.funding.funds_org'})),
        ),
    }),
)

