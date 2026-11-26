"""Explicit Bank of Russia household_lending source records and action settings."""
from types import MappingProxyType
from stratbox.capabilities.model.domains import SeriesSpec, CommandSpec, Applicability
from stratbox.capabilities.model.methods import MethodRef
from stratbox.domains.cbr.common.contracts import Publication, Semantics, StatisticalSettings, TableVariant, FormSettings, FamilySettings, SourceRequirement, MappingRules
from stratbox.domains.cbr.common.publications import SORS_INDEX, FORMS_INDEX, ESCROW_INDEX, OFFICES_PAGE, TERRITORIAL_INDEX

MORTGAGE_DEBT_PUBLICATION = Publication(
    'cbr.household_lending.mortgage_debt', 'cbr.household_lending', 'Mortgage debt',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Mortgage/02_14_Debt_mortgage.xlsx', None,
)
MORTGAGE_DEBT_TABLE = StatisticalSettings(
    'cbr.household_lending.mortgage_debt', (
        TableVariant('total', 'итого', 'statistics', 'stock', 'as_of', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
        TableVariant('table_2', 'в\\ т\\.ч\\.\\ просроч\\.', 'statistics', 'stock', 'as_of', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
        TableVariant('table_3', 'по\\ приобр\\.\\ правам\\ итого', 'statistics', 'stock', 'as_of', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
        TableVariant('table_4', 'с\\ учетом\\ приобр\\.\\ прав\\ итого', 'statistics', 'stock', 'as_of', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
        TableVariant('rub', 'в\\ рублях', 'statistics', 'stock', 'as_of', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
        TableVariant('table_6', 'в\\ т\\.ч\\.\\ просроч\\.\\ в\\ рублях', 'statistics', 'stock', 'as_of', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
        TableVariant('table_7', 'по\\ приобр\\.\\ правам\\ в\\ рублях', 'statistics', 'stock', 'as_of', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
        TableVariant('table_8', 'с\\ учетом\\ приобр\\.\\ прав\\ в\\ рублях', 'statistics', 'stock', 'as_of', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
        TableVariant('fx', 'в\\ инвалюте', 'statistics', 'stock', 'as_of', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
        TableVariant('table_10', 'в\\ т\\.ч\\.\\ просроч\\.\\ в\\ инвалюте', 'statistics', 'stock', 'as_of', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
        TableVariant('table_11', 'по\\ приобр\\.\\ правам\\ в\\ инвалюте', 'statistics', 'stock', 'as_of', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
        TableVariant('table_12', 'с\\ учетом\\ приобр\\.\\ прав\\ в\\ инвал', 'statistics', 'stock', 'as_of', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
    ),
)
MORTGAGE_DEBT = SeriesSpec(
    id='cbr.household_lending.mortgage_debt',
    publication=MORTGAGE_DEBT_PUBLICATION,
    semantics=Semantics('publisher_defined', ('publication', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            MORTGAGE_DEBT_PUBLICATION, Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_debt'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            MORTGAGE_DEBT_PUBLICATION, Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_debt'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            MORTGAGE_DEBT_PUBLICATION, Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_debt'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            MORTGAGE_DEBT_PUBLICATION, Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_debt'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.household_lending.mortgage_debt', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_debt'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.household_lending.mortgage_debt', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_debt'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.household_lending.mortgage_debt'), Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_debt'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            MORTGAGE_DEBT_TABLE, Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_debt'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            MORTGAGE_DEBT_TABLE, Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_debt'})),
        ),
    }),
)

MORTGAGE_DEBT_IND_PUBLICATION = Publication(
    'cbr.household_lending.mortgage_debt_ind', 'cbr.household_lending', 'Household loan debt',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Mortgage/02_05_Debt_ind.xlsx', None,
)
MORTGAGE_DEBT_IND_TABLE = StatisticalSettings(
    'cbr.household_lending.mortgage_debt_ind', (
        TableVariant('total', 'итого', 'statistics', 'stock', 'as_of', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
        TableVariant('table_2', 'в\\ т\\.ч\\.\\ просроч\\.', 'statistics', 'stock', 'as_of', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
        TableVariant('rub', 'в\\ рублях', 'statistics', 'stock', 'as_of', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
        TableVariant('table_4', 'в\\ т\\.ч\\.\\ просроч\\.\\ в\\ рублях', 'statistics', 'stock', 'as_of', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
        TableVariant('fx', 'в\\ инвалюте', 'statistics', 'stock', 'as_of', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
        TableVariant('table_6', 'в\\ т\\.ч\\.\\ просроч\\.\\ в\\ инвалюте', 'statistics', 'stock', 'as_of', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
    ),
)
MORTGAGE_DEBT_IND = SeriesSpec(
    id='cbr.household_lending.mortgage_debt_ind',
    publication=MORTGAGE_DEBT_IND_PUBLICATION,
    semantics=Semantics('publisher_defined', ('publication', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            MORTGAGE_DEBT_IND_PUBLICATION, Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_debt_ind'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            MORTGAGE_DEBT_IND_PUBLICATION, Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_debt_ind'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            MORTGAGE_DEBT_IND_PUBLICATION, Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_debt_ind'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            MORTGAGE_DEBT_IND_PUBLICATION, Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_debt_ind'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.household_lending.mortgage_debt_ind', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_debt_ind'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.household_lending.mortgage_debt_ind', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_debt_ind'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.household_lending.mortgage_debt_ind'), Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_debt_ind'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            MORTGAGE_DEBT_IND_TABLE, Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_debt_ind'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            MORTGAGE_DEBT_IND_TABLE, Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_debt_ind'})),
        ),
    }),
)

MORTGAGE_FULL_PUBLICATION = Publication(
    'cbr.household_lending.mortgage_full', 'cbr.household_lending', 'Mortgage lending history',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Mortgage/02_02_Mortgage.xlsx', None,
)
MORTGAGE_FULL_TABLE = StatisticalSettings(
    'cbr.household_lending.mortgage_full', (
        TableVariant('total', 'итого', 'statistics', None, 'mixed_source_periods', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
        TableVariant('rub', 'в\\ рублях', 'statistics', None, 'mixed_source_periods', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
        TableVariant('fx', 'в\\ инвалюте', 'statistics', None, 'mixed_source_periods', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
    ),
)
MORTGAGE_FULL = SeriesSpec(
    id='cbr.household_lending.mortgage_full',
    publication=MORTGAGE_FULL_PUBLICATION,
    semantics=Semantics('publisher_defined', ('publication', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            MORTGAGE_FULL_PUBLICATION, Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_full'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            MORTGAGE_FULL_PUBLICATION, Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_full'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            MORTGAGE_FULL_PUBLICATION, Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_full'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            MORTGAGE_FULL_PUBLICATION, Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_full'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.household_lending.mortgage_full', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_full'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.household_lending.mortgage_full', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_full'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.household_lending.mortgage_full'), Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_full'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            MORTGAGE_FULL_TABLE, Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_full'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            MORTGAGE_FULL_TABLE, Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_full'})),
        ),
    }),
)

MORTGAGE_IHC_PUBLICATION = Publication(
    'cbr.household_lending.mortgage_ihc', 'cbr.household_lending', 'Mortgages for individual housing construction',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/banksector/mortgage/02_41_Mortgage_ihc.xlsx', None,
)
MORTGAGE_IHC_TABLE = StatisticalSettings(
    'cbr.household_lending.mortgage_ihc', (
        TableVariant('total', 'итого', 'statistics', None, 'mixed_source_periods', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
        TableVariant('rub', 'в\\ рублях', 'statistics', None, 'mixed_source_periods', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
        TableVariant('fx', 'в\\ инвалюте', 'statistics', None, 'mixed_source_periods', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
    ),
)
MORTGAGE_IHC = SeriesSpec(
    id='cbr.household_lending.mortgage_ihc',
    publication=MORTGAGE_IHC_PUBLICATION,
    semantics=Semantics('publisher_defined', ('publication', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            MORTGAGE_IHC_PUBLICATION, Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_ihc'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            MORTGAGE_IHC_PUBLICATION, Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_ihc'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            MORTGAGE_IHC_PUBLICATION, Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_ihc'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            MORTGAGE_IHC_PUBLICATION, Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_ihc'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.household_lending.mortgage_ihc', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_ihc'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.household_lending.mortgage_ihc', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_ihc'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.household_lending.mortgage_ihc'), Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_ihc'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            MORTGAGE_IHC_TABLE, Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_ihc'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            MORTGAGE_IHC_TABLE, Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_ihc'})),
        ),
    }),
)

MORTGAGE_SCPA_DEBT_PUBLICATION = Publication(
    'cbr.household_lending.mortgage_scpa_debt', 'cbr.household_lending', 'Mortgage debt under shared construction agreements',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Mortgage/02_18_Debt_scpa_mortgage.xlsx', None,
)
MORTGAGE_SCPA_DEBT_TABLE = StatisticalSettings(
    'cbr.household_lending.mortgage_scpa_debt', (
        TableVariant('total', 'итого', 'statistics', 'stock', 'as_of', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
        TableVariant('table_2', 'в\\ т\\.ч\\.\\ просроч\\.', 'statistics', 'stock', 'as_of', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
        TableVariant('table_3', 'по\\ приобр\\.\\ правам\\ итого', 'statistics', 'stock', 'as_of', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
        TableVariant('table_4', 'с\\ учетом\\ приобр\\.\\ прав\\ итого', 'statistics', 'stock', 'as_of', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
        TableVariant('rub', 'в\\ рублях', 'statistics', 'stock', 'as_of', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
        TableVariant('table_6', 'в\\ т\\.ч\\.\\ просроч\\.\\ в\\ рублях', 'statistics', 'stock', 'as_of', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
        TableVariant('table_7', 'по\\ приобр\\.\\ правам\\ в\\ рублях', 'statistics', 'stock', 'as_of', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
        TableVariant('table_8', 'с\\ учетом\\ приобр\\.\\ прав\\ в\\ рублях', 'statistics', 'stock', 'as_of', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
        TableVariant('fx', 'в\\ инвалюте', 'statistics', 'stock', 'as_of', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
        TableVariant('table_10', 'в\\ т\\.ч\\.\\ просроч\\.\\ в\\ инвалюте', 'statistics', 'stock', 'as_of', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
        TableVariant('table_11', 'по\\ приобр\\.\\ правам\\ в\\ инвалюте', 'statistics', 'stock', 'as_of', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
        TableVariant('table_12', 'с\\ учетом\\ приобр\\.\\ прав\\ в\\ инвал', 'statistics', 'stock', 'as_of', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
    ),
)
MORTGAGE_SCPA_DEBT = SeriesSpec(
    id='cbr.household_lending.mortgage_scpa_debt',
    publication=MORTGAGE_SCPA_DEBT_PUBLICATION,
    semantics=Semantics('publisher_defined', ('publication', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            MORTGAGE_SCPA_DEBT_PUBLICATION, Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_scpa_debt'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            MORTGAGE_SCPA_DEBT_PUBLICATION, Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_scpa_debt'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            MORTGAGE_SCPA_DEBT_PUBLICATION, Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_scpa_debt'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            MORTGAGE_SCPA_DEBT_PUBLICATION, Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_scpa_debt'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.household_lending.mortgage_scpa_debt', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_scpa_debt'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.household_lending.mortgage_scpa_debt', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_scpa_debt'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.household_lending.mortgage_scpa_debt'), Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_scpa_debt'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            MORTGAGE_SCPA_DEBT_TABLE, Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_scpa_debt'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            MORTGAGE_SCPA_DEBT_TABLE, Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_scpa_debt'})),
        ),
    }),
)

MORTGAGE_SCPA_FULL_PUBLICATION = Publication(
    'cbr.household_lending.mortgage_scpa_full', 'cbr.household_lending', 'Mortgages under shared construction agreements',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Mortgage/02_03_Scpa_mortgage.xlsx', None,
)
MORTGAGE_SCPA_FULL_TABLE = StatisticalSettings(
    'cbr.household_lending.mortgage_scpa_full', (
        TableVariant('total', 'итого', 'statistics', None, 'mixed_source_periods', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
        TableVariant('rub', 'в\\ рублях', 'statistics', None, 'mixed_source_periods', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
        TableVariant('fx', 'в\\ инвалюте', 'statistics', None, 'mixed_source_periods', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
    ),
)
MORTGAGE_SCPA_FULL = SeriesSpec(
    id='cbr.household_lending.mortgage_scpa_full',
    publication=MORTGAGE_SCPA_FULL_PUBLICATION,
    semantics=Semantics('publisher_defined', ('publication', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            MORTGAGE_SCPA_FULL_PUBLICATION, Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_scpa_full'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            MORTGAGE_SCPA_FULL_PUBLICATION, Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_scpa_full'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            MORTGAGE_SCPA_FULL_PUBLICATION, Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_scpa_full'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            MORTGAGE_SCPA_FULL_PUBLICATION, Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_scpa_full'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.household_lending.mortgage_scpa_full', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_scpa_full'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.household_lending.mortgage_scpa_full', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_scpa_full'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.household_lending.mortgage_scpa_full'), Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_scpa_full'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            MORTGAGE_SCPA_FULL_TABLE, Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_scpa_full'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            MORTGAGE_SCPA_FULL_TABLE, Applicability(source_ids=frozenset({'cbr.household_lending.mortgage_scpa_full'})),
        ),
    }),
)

