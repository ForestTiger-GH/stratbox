"""Explicit Bank of Russia household_lending source records and action settings."""
from types import MappingProxyType
from stratbox.capabilities.model.domains import SeriesSpec, CommandSpec, Applicability
from stratbox.capabilities.model.methods import MethodRef
from stratbox.domains.cbr.common.contracts import Publication, Semantics, StatisticalSettings, TableVariant, FormSettings, FamilySettings, SourceRequirement, MappingRules
from stratbox.domains.cbr.common.publications import SORS_INDEX, FORMS_INDEX, ESCROW_INDEX, OFFICES_PAGE, TERRITORIAL_INDEX

FAMILY_ID = 'cbr.household_lending'

MORTGAGE_DEBT_PUBLICATION = Publication(
    'cbr.household_lending.mortgage_debt', FAMILY_ID, 'Mortgage debt',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Mortgage/02_14_Debt_mortgage.xlsx', None,
)
MORTGAGE_DEBT_TABLE = StatisticalSettings(
    MORTGAGE_DEBT_PUBLICATION.series_id, (
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
    id=MORTGAGE_DEBT_PUBLICATION.series_id,
    publication=MORTGAGE_DEBT_PUBLICATION,
    semantics=Semantics('publisher_defined', ('publication', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            MORTGAGE_DEBT_PUBLICATION, Applicability(source_ids=frozenset({MORTGAGE_DEBT_PUBLICATION.series_id})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            MORTGAGE_DEBT_PUBLICATION, Applicability(source_ids=frozenset({MORTGAGE_DEBT_PUBLICATION.series_id})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            MORTGAGE_DEBT_PUBLICATION, Applicability(source_ids=frozenset({MORTGAGE_DEBT_PUBLICATION.series_id})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            MORTGAGE_DEBT_PUBLICATION, Applicability(source_ids=frozenset({MORTGAGE_DEBT_PUBLICATION.series_id})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement(MORTGAGE_DEBT_PUBLICATION.series_id, MORTGAGE_DEBT_PUBLICATION.formats, issue_required=MORTGAGE_DEBT_PUBLICATION.issue_model == 'dated', locator=MORTGAGE_DEBT_PUBLICATION.locator, filename_pattern=MORTGAGE_DEBT_PUBLICATION.filename_pattern, publication_kind=MORTGAGE_DEBT_PUBLICATION.kind), Applicability(source_ids=frozenset({MORTGAGE_DEBT_PUBLICATION.series_id})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement(MORTGAGE_DEBT_PUBLICATION.series_id, MORTGAGE_DEBT_PUBLICATION.formats, issue_required=MORTGAGE_DEBT_PUBLICATION.issue_model == 'dated', locator=MORTGAGE_DEBT_PUBLICATION.locator, filename_pattern=MORTGAGE_DEBT_PUBLICATION.filename_pattern, publication_kind=MORTGAGE_DEBT_PUBLICATION.kind), Applicability(source_ids=frozenset({MORTGAGE_DEBT_PUBLICATION.series_id})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules(MORTGAGE_DEBT_PUBLICATION.series_id), Applicability(source_ids=frozenset({MORTGAGE_DEBT_PUBLICATION.series_id})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            MORTGAGE_DEBT_TABLE, Applicability(source_ids=frozenset({MORTGAGE_DEBT_PUBLICATION.series_id})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            MORTGAGE_DEBT_TABLE, Applicability(source_ids=frozenset({MORTGAGE_DEBT_PUBLICATION.series_id})),
        ),
    }),
)

MORTGAGE_DEBT_IND_PUBLICATION = Publication(
    'cbr.household_lending.mortgage_debt_ind', FAMILY_ID, 'Household loan debt',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Mortgage/02_05_Debt_ind.xlsx', None,
)
MORTGAGE_DEBT_IND_TABLE = StatisticalSettings(
    MORTGAGE_DEBT_IND_PUBLICATION.series_id, (
        TableVariant('total', 'итого', 'statistics', 'stock', 'as_of', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
        TableVariant('table_2', 'в\\ т\\.ч\\.\\ просроч\\.', 'statistics', 'stock', 'as_of', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
        TableVariant('rub', 'в\\ рублях', 'statistics', 'stock', 'as_of', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
        TableVariant('table_4', 'в\\ т\\.ч\\.\\ просроч\\.\\ в\\ рублях', 'statistics', 'stock', 'as_of', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
        TableVariant('fx', 'в\\ инвалюте', 'statistics', 'stock', 'as_of', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
        TableVariant('table_6', 'в\\ т\\.ч\\.\\ просроч\\.\\ в\\ инвалюте', 'statistics', 'stock', 'as_of', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
    ),
)
MORTGAGE_DEBT_IND = SeriesSpec(
    id=MORTGAGE_DEBT_IND_PUBLICATION.series_id,
    publication=MORTGAGE_DEBT_IND_PUBLICATION,
    semantics=Semantics('publisher_defined', ('publication', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            MORTGAGE_DEBT_IND_PUBLICATION, Applicability(source_ids=frozenset({MORTGAGE_DEBT_IND_PUBLICATION.series_id})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            MORTGAGE_DEBT_IND_PUBLICATION, Applicability(source_ids=frozenset({MORTGAGE_DEBT_IND_PUBLICATION.series_id})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            MORTGAGE_DEBT_IND_PUBLICATION, Applicability(source_ids=frozenset({MORTGAGE_DEBT_IND_PUBLICATION.series_id})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            MORTGAGE_DEBT_IND_PUBLICATION, Applicability(source_ids=frozenset({MORTGAGE_DEBT_IND_PUBLICATION.series_id})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement(MORTGAGE_DEBT_IND_PUBLICATION.series_id, MORTGAGE_DEBT_IND_PUBLICATION.formats, issue_required=MORTGAGE_DEBT_IND_PUBLICATION.issue_model == 'dated', locator=MORTGAGE_DEBT_IND_PUBLICATION.locator, filename_pattern=MORTGAGE_DEBT_IND_PUBLICATION.filename_pattern, publication_kind=MORTGAGE_DEBT_IND_PUBLICATION.kind), Applicability(source_ids=frozenset({MORTGAGE_DEBT_IND_PUBLICATION.series_id})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement(MORTGAGE_DEBT_IND_PUBLICATION.series_id, MORTGAGE_DEBT_IND_PUBLICATION.formats, issue_required=MORTGAGE_DEBT_IND_PUBLICATION.issue_model == 'dated', locator=MORTGAGE_DEBT_IND_PUBLICATION.locator, filename_pattern=MORTGAGE_DEBT_IND_PUBLICATION.filename_pattern, publication_kind=MORTGAGE_DEBT_IND_PUBLICATION.kind), Applicability(source_ids=frozenset({MORTGAGE_DEBT_IND_PUBLICATION.series_id})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules(MORTGAGE_DEBT_IND_PUBLICATION.series_id), Applicability(source_ids=frozenset({MORTGAGE_DEBT_IND_PUBLICATION.series_id})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            MORTGAGE_DEBT_IND_TABLE, Applicability(source_ids=frozenset({MORTGAGE_DEBT_IND_PUBLICATION.series_id})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            MORTGAGE_DEBT_IND_TABLE, Applicability(source_ids=frozenset({MORTGAGE_DEBT_IND_PUBLICATION.series_id})),
        ),
    }),
)

MORTGAGE_FULL_PUBLICATION = Publication(
    'cbr.household_lending.mortgage_full', FAMILY_ID, 'Mortgage lending history',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Mortgage/02_02_Mortgage.xlsx', None,
)
MORTGAGE_FULL_TABLE = StatisticalSettings(
    MORTGAGE_FULL_PUBLICATION.series_id, (
        TableVariant('total', 'итого', 'statistics', None, 'mixed_source_periods', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
        TableVariant('rub', 'в\\ рублях', 'statistics', None, 'mixed_source_periods', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
        TableVariant('fx', 'в\\ инвалюте', 'statistics', None, 'mixed_source_periods', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
    ),
)
MORTGAGE_FULL = SeriesSpec(
    id=MORTGAGE_FULL_PUBLICATION.series_id,
    publication=MORTGAGE_FULL_PUBLICATION,
    semantics=Semantics('publisher_defined', ('publication', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            MORTGAGE_FULL_PUBLICATION, Applicability(source_ids=frozenset({MORTGAGE_FULL_PUBLICATION.series_id})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            MORTGAGE_FULL_PUBLICATION, Applicability(source_ids=frozenset({MORTGAGE_FULL_PUBLICATION.series_id})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            MORTGAGE_FULL_PUBLICATION, Applicability(source_ids=frozenset({MORTGAGE_FULL_PUBLICATION.series_id})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            MORTGAGE_FULL_PUBLICATION, Applicability(source_ids=frozenset({MORTGAGE_FULL_PUBLICATION.series_id})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement(MORTGAGE_FULL_PUBLICATION.series_id, MORTGAGE_FULL_PUBLICATION.formats, issue_required=MORTGAGE_FULL_PUBLICATION.issue_model == 'dated', locator=MORTGAGE_FULL_PUBLICATION.locator, filename_pattern=MORTGAGE_FULL_PUBLICATION.filename_pattern, publication_kind=MORTGAGE_FULL_PUBLICATION.kind), Applicability(source_ids=frozenset({MORTGAGE_FULL_PUBLICATION.series_id})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement(MORTGAGE_FULL_PUBLICATION.series_id, MORTGAGE_FULL_PUBLICATION.formats, issue_required=MORTGAGE_FULL_PUBLICATION.issue_model == 'dated', locator=MORTGAGE_FULL_PUBLICATION.locator, filename_pattern=MORTGAGE_FULL_PUBLICATION.filename_pattern, publication_kind=MORTGAGE_FULL_PUBLICATION.kind), Applicability(source_ids=frozenset({MORTGAGE_FULL_PUBLICATION.series_id})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules(MORTGAGE_FULL_PUBLICATION.series_id), Applicability(source_ids=frozenset({MORTGAGE_FULL_PUBLICATION.series_id})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            MORTGAGE_FULL_TABLE, Applicability(source_ids=frozenset({MORTGAGE_FULL_PUBLICATION.series_id})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            MORTGAGE_FULL_TABLE, Applicability(source_ids=frozenset({MORTGAGE_FULL_PUBLICATION.series_id})),
        ),
    }),
)

MORTGAGE_IHC_PUBLICATION = Publication(
    'cbr.household_lending.mortgage_ihc', FAMILY_ID, 'Mortgages for individual housing construction',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/banksector/mortgage/02_41_Mortgage_ihc.xlsx', None,
)
MORTGAGE_IHC_TABLE = StatisticalSettings(
    MORTGAGE_IHC_PUBLICATION.series_id, (
        TableVariant('total', 'итого', 'statistics', None, 'mixed_source_periods', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
        TableVariant('rub', 'в\\ рублях', 'statistics', None, 'mixed_source_periods', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
        TableVariant('fx', 'в\\ инвалюте', 'statistics', None, 'mixed_source_periods', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
    ),
)
MORTGAGE_IHC = SeriesSpec(
    id=MORTGAGE_IHC_PUBLICATION.series_id,
    publication=MORTGAGE_IHC_PUBLICATION,
    semantics=Semantics('publisher_defined', ('publication', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            MORTGAGE_IHC_PUBLICATION, Applicability(source_ids=frozenset({MORTGAGE_IHC_PUBLICATION.series_id})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            MORTGAGE_IHC_PUBLICATION, Applicability(source_ids=frozenset({MORTGAGE_IHC_PUBLICATION.series_id})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            MORTGAGE_IHC_PUBLICATION, Applicability(source_ids=frozenset({MORTGAGE_IHC_PUBLICATION.series_id})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            MORTGAGE_IHC_PUBLICATION, Applicability(source_ids=frozenset({MORTGAGE_IHC_PUBLICATION.series_id})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement(MORTGAGE_IHC_PUBLICATION.series_id, MORTGAGE_IHC_PUBLICATION.formats, issue_required=MORTGAGE_IHC_PUBLICATION.issue_model == 'dated', locator=MORTGAGE_IHC_PUBLICATION.locator, filename_pattern=MORTGAGE_IHC_PUBLICATION.filename_pattern, publication_kind=MORTGAGE_IHC_PUBLICATION.kind), Applicability(source_ids=frozenset({MORTGAGE_IHC_PUBLICATION.series_id})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement(MORTGAGE_IHC_PUBLICATION.series_id, MORTGAGE_IHC_PUBLICATION.formats, issue_required=MORTGAGE_IHC_PUBLICATION.issue_model == 'dated', locator=MORTGAGE_IHC_PUBLICATION.locator, filename_pattern=MORTGAGE_IHC_PUBLICATION.filename_pattern, publication_kind=MORTGAGE_IHC_PUBLICATION.kind), Applicability(source_ids=frozenset({MORTGAGE_IHC_PUBLICATION.series_id})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules(MORTGAGE_IHC_PUBLICATION.series_id), Applicability(source_ids=frozenset({MORTGAGE_IHC_PUBLICATION.series_id})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            MORTGAGE_IHC_TABLE, Applicability(source_ids=frozenset({MORTGAGE_IHC_PUBLICATION.series_id})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            MORTGAGE_IHC_TABLE, Applicability(source_ids=frozenset({MORTGAGE_IHC_PUBLICATION.series_id})),
        ),
    }),
)

MORTGAGE_SCPA_DEBT_PUBLICATION = Publication(
    'cbr.household_lending.mortgage_scpa_debt', FAMILY_ID, 'Mortgage debt under shared construction agreements',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Mortgage/02_18_Debt_scpa_mortgage.xlsx', None,
)
MORTGAGE_SCPA_DEBT_TABLE = StatisticalSettings(
    MORTGAGE_SCPA_DEBT_PUBLICATION.series_id, (
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
    id=MORTGAGE_SCPA_DEBT_PUBLICATION.series_id,
    publication=MORTGAGE_SCPA_DEBT_PUBLICATION,
    semantics=Semantics('publisher_defined', ('publication', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            MORTGAGE_SCPA_DEBT_PUBLICATION, Applicability(source_ids=frozenset({MORTGAGE_SCPA_DEBT_PUBLICATION.series_id})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            MORTGAGE_SCPA_DEBT_PUBLICATION, Applicability(source_ids=frozenset({MORTGAGE_SCPA_DEBT_PUBLICATION.series_id})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            MORTGAGE_SCPA_DEBT_PUBLICATION, Applicability(source_ids=frozenset({MORTGAGE_SCPA_DEBT_PUBLICATION.series_id})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            MORTGAGE_SCPA_DEBT_PUBLICATION, Applicability(source_ids=frozenset({MORTGAGE_SCPA_DEBT_PUBLICATION.series_id})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement(MORTGAGE_SCPA_DEBT_PUBLICATION.series_id, MORTGAGE_SCPA_DEBT_PUBLICATION.formats, issue_required=MORTGAGE_SCPA_DEBT_PUBLICATION.issue_model == 'dated', locator=MORTGAGE_SCPA_DEBT_PUBLICATION.locator, filename_pattern=MORTGAGE_SCPA_DEBT_PUBLICATION.filename_pattern, publication_kind=MORTGAGE_SCPA_DEBT_PUBLICATION.kind), Applicability(source_ids=frozenset({MORTGAGE_SCPA_DEBT_PUBLICATION.series_id})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement(MORTGAGE_SCPA_DEBT_PUBLICATION.series_id, MORTGAGE_SCPA_DEBT_PUBLICATION.formats, issue_required=MORTGAGE_SCPA_DEBT_PUBLICATION.issue_model == 'dated', locator=MORTGAGE_SCPA_DEBT_PUBLICATION.locator, filename_pattern=MORTGAGE_SCPA_DEBT_PUBLICATION.filename_pattern, publication_kind=MORTGAGE_SCPA_DEBT_PUBLICATION.kind), Applicability(source_ids=frozenset({MORTGAGE_SCPA_DEBT_PUBLICATION.series_id})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules(MORTGAGE_SCPA_DEBT_PUBLICATION.series_id), Applicability(source_ids=frozenset({MORTGAGE_SCPA_DEBT_PUBLICATION.series_id})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            MORTGAGE_SCPA_DEBT_TABLE, Applicability(source_ids=frozenset({MORTGAGE_SCPA_DEBT_PUBLICATION.series_id})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            MORTGAGE_SCPA_DEBT_TABLE, Applicability(source_ids=frozenset({MORTGAGE_SCPA_DEBT_PUBLICATION.series_id})),
        ),
    }),
)

MORTGAGE_SCPA_FULL_PUBLICATION = Publication(
    'cbr.household_lending.mortgage_scpa_full', FAMILY_ID, 'Mortgages under shared construction agreements',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Mortgage/02_03_Scpa_mortgage.xlsx', None,
)
MORTGAGE_SCPA_FULL_TABLE = StatisticalSettings(
    MORTGAGE_SCPA_FULL_PUBLICATION.series_id, (
        TableVariant('total', 'итого', 'statistics', None, 'mixed_source_periods', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
        TableVariant('rub', 'в\\ рублях', 'statistics', None, 'mixed_source_periods', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
        TableVariant('fx', 'в\\ инвалюте', 'statistics', None, 'mixed_source_periods', ('source_geography_or_measure', 'denomination_group', 'lending_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Household lending, mortgages, shared-construction and individual-housing perimeters remain separate; rates and terms require weights for aggregation.'),
    ),
)
MORTGAGE_SCPA_FULL = SeriesSpec(
    id=MORTGAGE_SCPA_FULL_PUBLICATION.series_id,
    publication=MORTGAGE_SCPA_FULL_PUBLICATION,
    semantics=Semantics('publisher_defined', ('publication', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            MORTGAGE_SCPA_FULL_PUBLICATION, Applicability(source_ids=frozenset({MORTGAGE_SCPA_FULL_PUBLICATION.series_id})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            MORTGAGE_SCPA_FULL_PUBLICATION, Applicability(source_ids=frozenset({MORTGAGE_SCPA_FULL_PUBLICATION.series_id})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            MORTGAGE_SCPA_FULL_PUBLICATION, Applicability(source_ids=frozenset({MORTGAGE_SCPA_FULL_PUBLICATION.series_id})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            MORTGAGE_SCPA_FULL_PUBLICATION, Applicability(source_ids=frozenset({MORTGAGE_SCPA_FULL_PUBLICATION.series_id})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement(MORTGAGE_SCPA_FULL_PUBLICATION.series_id, MORTGAGE_SCPA_FULL_PUBLICATION.formats, issue_required=MORTGAGE_SCPA_FULL_PUBLICATION.issue_model == 'dated', locator=MORTGAGE_SCPA_FULL_PUBLICATION.locator, filename_pattern=MORTGAGE_SCPA_FULL_PUBLICATION.filename_pattern, publication_kind=MORTGAGE_SCPA_FULL_PUBLICATION.kind), Applicability(source_ids=frozenset({MORTGAGE_SCPA_FULL_PUBLICATION.series_id})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement(MORTGAGE_SCPA_FULL_PUBLICATION.series_id, MORTGAGE_SCPA_FULL_PUBLICATION.formats, issue_required=MORTGAGE_SCPA_FULL_PUBLICATION.issue_model == 'dated', locator=MORTGAGE_SCPA_FULL_PUBLICATION.locator, filename_pattern=MORTGAGE_SCPA_FULL_PUBLICATION.filename_pattern, publication_kind=MORTGAGE_SCPA_FULL_PUBLICATION.kind), Applicability(source_ids=frozenset({MORTGAGE_SCPA_FULL_PUBLICATION.series_id})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules(MORTGAGE_SCPA_FULL_PUBLICATION.series_id), Applicability(source_ids=frozenset({MORTGAGE_SCPA_FULL_PUBLICATION.series_id})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            MORTGAGE_SCPA_FULL_TABLE, Applicability(source_ids=frozenset({MORTGAGE_SCPA_FULL_PUBLICATION.series_id})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            MORTGAGE_SCPA_FULL_TABLE, Applicability(source_ids=frozenset({MORTGAGE_SCPA_FULL_PUBLICATION.series_id})),
        ),
    }),
)

