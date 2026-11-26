"""Explicit Bank of Russia corporate_lending source records and action settings."""
from types import MappingProxyType
from stratbox.capabilities.model.domains import SeriesSpec, CommandSpec, Applicability
from stratbox.capabilities.model.methods import MethodRef
from stratbox.domains.cbr.common.contracts import Publication, Semantics, StatisticalSettings, TableVariant, CorporateMeaning, FormSettings, FamilySettings, SourceRequirement, MappingRules
from stratbox.domains.cbr.common.publications import SORS_INDEX, FORMS_INDEX, ESCROW_INDEX, OFFICES_PAGE, TERRITORIAL_INDEX

CORP_DEBT_A_PUBLICATION = Publication(
    'cbr.corporate_lending.corp_debt_a', 'cbr.corporate_lending', 'Corporate debt by published activity categories',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/01_02_A_Debt_corp_by_activity.xlsx', None,
)
CORP_DEBT_A_TABLE = StatisticalSettings(
    'cbr.corporate_lending.corp_debt_a', (
        TableVariant('total', 'итого', 'statistics', 'stock', 'as_of', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
        TableVariant('table_2', 'в\\ т\\.ч\\.\\ просроч\\.', 'statistics', 'stock', 'as_of', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
        TableVariant('rub', 'в\\ рублях', 'statistics', 'stock', 'as_of', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
        TableVariant('table_4', 'в\\ т\\.ч\\.\\ просроч\\.\\ в\\ рублях', 'statistics', 'stock', 'as_of', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
        TableVariant('fx', 'в\\ инвалюте', 'statistics', 'stock', 'as_of', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
        TableVariant('table_6', 'в\\ т\\.ч\\.\\ просроч\\.\\ в\\ инвалюте', 'statistics', 'stock', 'as_of', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
    ), corporate=CorporateMeaning('01_02_A', 'history', 'activity', 'stock', 'CORPORATE_TOTAL'),
)
CORP_DEBT_A = SeriesSpec(
    id='cbr.corporate_lending.corp_debt_a',
    publication=CORP_DEBT_A_PUBLICATION,
    semantics=Semantics('credit_debt_stock', ('report_date', 'territory', 'activity', 'currency', 'measure'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            CORP_DEBT_A_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.corp_debt_a'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            CORP_DEBT_A_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.corp_debt_a'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            CORP_DEBT_A_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.corp_debt_a'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            CORP_DEBT_A_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.corp_debt_a'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.corporate_lending.corp_debt_a', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.corporate_lending.corp_debt_a'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.corporate_lending.corp_debt_a', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.corporate_lending.corp_debt_a'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.corporate_lending.corp_debt_a'), Applicability(source_ids=frozenset({'cbr.corporate_lending.corp_debt_a'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            CORP_DEBT_A_TABLE, Applicability(source_ids=frozenset({'cbr.corporate_lending.corp_debt_a'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            CORP_DEBT_A_TABLE, Applicability(source_ids=frozenset({'cbr.corporate_lending.corp_debt_a'})),
        ),
    }),
)

CORP_DEBT_C_PUBLICATION = Publication(
    'cbr.corporate_lending.corp_debt_c', 'cbr.corporate_lending', 'Corporate debt by OKVED2 classes',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/01_02_C_Debt_corp_by_activity.xlsx', None,
)
CORP_DEBT_C_TABLE = StatisticalSettings(
    'cbr.corporate_lending.corp_debt_c', (
        TableVariant('total', 'итого', 'statistics', 'stock', 'as_of', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
        TableVariant('table_2', 'в\\ т\\.ч\\.\\ просроч\\.\\ итого', 'statistics', 'stock', 'as_of', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
        TableVariant('rub', 'в\\ рублях', 'statistics', 'stock', 'as_of', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
        TableVariant('table_4', 'в\\ т\\.ч\\.\\ просроч\\.\\ в\\ рублях', 'statistics', 'stock', 'as_of', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
        TableVariant('fx', 'в\\ инвалюте', 'statistics', 'stock', 'as_of', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
        TableVariant('table_6', 'в\\ т\\.ч\\.\\ просроч\\.\\ в\\ инвалюте', 'statistics', 'stock', 'as_of', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
    ), corporate=CorporateMeaning('01_02_C', 'history', 'activity', 'stock', 'CORPORATE_TOTAL'),
)
CORP_DEBT_C = SeriesSpec(
    id='cbr.corporate_lending.corp_debt_c',
    publication=CORP_DEBT_C_PUBLICATION,
    semantics=Semantics('credit_debt_stock', ('report_date', 'territory', 'activity', 'currency', 'measure'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            CORP_DEBT_C_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.corp_debt_c'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            CORP_DEBT_C_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.corp_debt_c'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            CORP_DEBT_C_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.corp_debt_c'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            CORP_DEBT_C_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.corp_debt_c'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.corporate_lending.corp_debt_c', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.corporate_lending.corp_debt_c'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.corporate_lending.corp_debt_c', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.corporate_lending.corp_debt_c'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.corporate_lending.corp_debt_c'), Applicability(source_ids=frozenset({'cbr.corporate_lending.corp_debt_c'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            CORP_DEBT_C_TABLE, Applicability(source_ids=frozenset({'cbr.corporate_lending.corp_debt_c'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            CORP_DEBT_C_TABLE, Applicability(source_ids=frozenset({'cbr.corporate_lending.corp_debt_c'})),
        ),
    }),
)

CORP_DEBT_SUBJ_PUBLICATION = Publication(
    'cbr.corporate_lending.corp_debt_subj', 'cbr.corporate_lending', 'Corporate debt by region over time',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/01_05_D_Debt_subj.xlsx', None,
)
CORP_DEBT_SUBJ_TABLE = StatisticalSettings(
    'cbr.corporate_lending.corp_debt_subj', (
        TableVariant('total', 'итого', 'statistics', 'stock', 'as_of', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
        TableVariant('table_2', 'в\\ т\\.ч\\.\\ просроч\\.\\ итого', 'statistics', 'stock', 'as_of', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
        TableVariant('rub', 'в\\ рублях', 'statistics', 'stock', 'as_of', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
        TableVariant('table_4', 'в\\ т\\.ч\\.\\ просроч\\.\\ в\\ рублях', 'statistics', 'stock', 'as_of', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
        TableVariant('fx', 'в\\ инвалюте', 'statistics', 'stock', 'as_of', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
        TableVariant('table_6', 'в\\ т\\.ч\\.\\ просроч\\.\\ в\\ инвалюте', 'statistics', 'stock', 'as_of', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
    ), corporate=CorporateMeaning('01_05_D', 'history', 'geography', 'stock', 'CORPORATE_TOTAL'),
)
CORP_DEBT_SUBJ = SeriesSpec(
    id='cbr.corporate_lending.corp_debt_subj',
    publication=CORP_DEBT_SUBJ_PUBLICATION,
    semantics=Semantics('credit_debt_stock', ('report_date', 'territory', 'activity', 'currency', 'measure'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            CORP_DEBT_SUBJ_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.corp_debt_subj'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            CORP_DEBT_SUBJ_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.corp_debt_subj'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            CORP_DEBT_SUBJ_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.corp_debt_subj'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            CORP_DEBT_SUBJ_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.corp_debt_subj'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.corporate_lending.corp_debt_subj', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.corporate_lending.corp_debt_subj'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.corporate_lending.corp_debt_subj', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.corporate_lending.corp_debt_subj'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.corporate_lending.corp_debt_subj'), Applicability(source_ids=frozenset({'cbr.corporate_lending.corp_debt_subj'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            CORP_DEBT_SUBJ_TABLE, Applicability(source_ids=frozenset({'cbr.corporate_lending.corp_debt_subj'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            CORP_DEBT_SUBJ_TABLE, Applicability(source_ids=frozenset({'cbr.corporate_lending.corp_debt_subj'})),
        ),
    }),
)

CORP_NEW_LOANS_A_PUBLICATION = Publication(
    'cbr.corporate_lending.corp_new_loans_a', 'cbr.corporate_lending', 'Corporate lending by published activity categories',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/01_01_A_New_loans_corp_by_activity.xlsx', None,
)
CORP_NEW_LOANS_A_TABLE = StatisticalSettings(
    'cbr.corporate_lending.corp_new_loans_a', (
        TableVariant('total', 'итого', 'statistics', 'flow', 'source_interval', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
        TableVariant('rub', 'в\\ рублях', 'statistics', 'flow', 'source_interval', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
        TableVariant('fx', 'в\\ инвалюте', 'statistics', 'flow', 'source_interval', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
    ), corporate=CorporateMeaning('01_01_A', 'history', 'activity', 'flow', 'CORPORATE_TOTAL'),
)
CORP_NEW_LOANS_A = SeriesSpec(
    id='cbr.corporate_lending.corp_new_loans_a',
    publication=CORP_NEW_LOANS_A_PUBLICATION,
    semantics=Semantics('credit_issuance_flow', ('report_date', 'territory', 'activity', 'currency', 'measure'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            CORP_NEW_LOANS_A_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.corp_new_loans_a'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            CORP_NEW_LOANS_A_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.corp_new_loans_a'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            CORP_NEW_LOANS_A_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.corp_new_loans_a'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            CORP_NEW_LOANS_A_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.corp_new_loans_a'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.corporate_lending.corp_new_loans_a', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.corporate_lending.corp_new_loans_a'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.corporate_lending.corp_new_loans_a', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.corporate_lending.corp_new_loans_a'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.corporate_lending.corp_new_loans_a'), Applicability(source_ids=frozenset({'cbr.corporate_lending.corp_new_loans_a'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            CORP_NEW_LOANS_A_TABLE, Applicability(source_ids=frozenset({'cbr.corporate_lending.corp_new_loans_a'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            CORP_NEW_LOANS_A_TABLE, Applicability(source_ids=frozenset({'cbr.corporate_lending.corp_new_loans_a'})),
        ),
    }),
)

CORP_NEW_LOANS_C_PUBLICATION = Publication(
    'cbr.corporate_lending.corp_new_loans_c', 'cbr.corporate_lending', 'Corporate lending by OKVED2 classes',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/01_01_C_New_loans_corp_by_activity.xlsx', None,
)
CORP_NEW_LOANS_C_TABLE = StatisticalSettings(
    'cbr.corporate_lending.corp_new_loans_c', (
        TableVariant('total', 'итого', 'statistics', 'flow', 'source_interval', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
        TableVariant('rub', 'в\\ рублях', 'statistics', 'flow', 'source_interval', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
        TableVariant('fx', 'в\\ валюте', 'statistics', 'flow', 'source_interval', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
    ), corporate=CorporateMeaning('01_01_C', 'history', 'activity', 'flow', 'CORPORATE_TOTAL'),
)
CORP_NEW_LOANS_C = SeriesSpec(
    id='cbr.corporate_lending.corp_new_loans_c',
    publication=CORP_NEW_LOANS_C_PUBLICATION,
    semantics=Semantics('credit_issuance_flow', ('report_date', 'territory', 'activity', 'currency', 'measure'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            CORP_NEW_LOANS_C_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.corp_new_loans_c'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            CORP_NEW_LOANS_C_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.corp_new_loans_c'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            CORP_NEW_LOANS_C_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.corp_new_loans_c'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            CORP_NEW_LOANS_C_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.corp_new_loans_c'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.corporate_lending.corp_new_loans_c', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.corporate_lending.corp_new_loans_c'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.corporate_lending.corp_new_loans_c', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.corporate_lending.corp_new_loans_c'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.corporate_lending.corp_new_loans_c'), Applicability(source_ids=frozenset({'cbr.corporate_lending.corp_new_loans_c'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            CORP_NEW_LOANS_C_TABLE, Applicability(source_ids=frozenset({'cbr.corporate_lending.corp_new_loans_c'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            CORP_NEW_LOANS_C_TABLE, Applicability(source_ids=frozenset({'cbr.corporate_lending.corp_new_loans_c'})),
        ),
    }),
)

DEBT_0105A_PUBLICATION = Publication(
    'cbr.corporate_lending.debt_0105a', 'cbr.corporate_lending', 'Regional corporate debt by activity',
    'dated', ('xlsx',), 'index', SORS_INDEX, '01_05_A_Debt_corp_(?P<date>\\d{8})\\.xlsx',
)
DEBT_0105A_TABLE = FamilySettings('cbr.corporate_lending.debt_0105a', 'industry_debt')
DEBT_0105A = SeriesSpec(
    id='cbr.corporate_lending.debt_0105a',
    publication=DEBT_0105A_PUBLICATION,
    semantics=Semantics('credit_debt_stock', ('report_date', 'territory', 'activity', 'currency', 'measure'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            DEBT_0105A_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.debt_0105a'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            DEBT_0105A_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.debt_0105a'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            DEBT_0105A_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.debt_0105a'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            DEBT_0105A_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.debt_0105a'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.corporate_lending.debt_0105a', ('xlsx',), issue_required=True), Applicability(source_ids=frozenset({'cbr.corporate_lending.debt_0105a'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.industries:validate"),
            SourceRequirement('cbr.corporate_lending.debt_0105a', ('xlsx',), issue_required=True), Applicability(source_ids=frozenset({'cbr.corporate_lending.debt_0105a'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.corporate_lending.debt_0105a'), Applicability(source_ids=frozenset({'cbr.corporate_lending.debt_0105a'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.industries:extract"),
            DEBT_0105A_TABLE, Applicability(source_ids=frozenset({'cbr.corporate_lending.debt_0105a'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.industries:interpret"),
            DEBT_0105A_TABLE, Applicability(source_ids=frozenset({'cbr.corporate_lending.debt_0105a'})),
        ),
    }),
)

FD_OKVED2_PUBLICATION = Publication(
    'cbr.corporate_lending.fd_okved2', 'cbr.corporate_lending', 'Corporate loans by federal district and OKVED2 section',
    'dated', ('xlsx',), 'index', SORS_INDEX, '01_03_C_Loans_corp_by_fd_activity_(?P<date>\\d{8})\\.xlsx',
)
FD_OKVED2_TABLE = StatisticalSettings(
    'cbr.corporate_lending.fd_okved2', (
        TableVariant('table_1', '.*', 'statistics', None, 'mixed_source_periods', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
    ), corporate=CorporateMeaning('01_03_C', 'district', 'geography_activity', 'mixed', 'CORPORATE_TOTAL'),
)
FD_OKVED2 = SeriesSpec(
    id='cbr.corporate_lending.fd_okved2',
    publication=FD_OKVED2_PUBLICATION,
    semantics=Semantics('credit_debt_stock', ('report_date', 'territory', 'activity', 'currency', 'measure'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            FD_OKVED2_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.fd_okved2'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            FD_OKVED2_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.fd_okved2'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            FD_OKVED2_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.fd_okved2'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            FD_OKVED2_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.fd_okved2'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.corporate_lending.fd_okved2', ('xlsx',), issue_required=True), Applicability(source_ids=frozenset({'cbr.corporate_lending.fd_okved2'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.corporate_lending.fd_okved2', ('xlsx',), issue_required=True), Applicability(source_ids=frozenset({'cbr.corporate_lending.fd_okved2'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.corporate_lending.fd_okved2'), Applicability(source_ids=frozenset({'cbr.corporate_lending.fd_okved2'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            FD_OKVED2_TABLE, Applicability(source_ids=frozenset({'cbr.corporate_lending.fd_okved2'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            FD_OKVED2_TABLE, Applicability(source_ids=frozenset({'cbr.corporate_lending.fd_okved2'})),
        ),
    }),
)

ISSUANCE_0104A_PUBLICATION = Publication(
    'cbr.corporate_lending.issuance_0104a', 'cbr.corporate_lending', 'Monthly regional corporate lending by activity',
    'dated', ('xlsx',), 'index', SORS_INDEX, '01_04_A_New_loans_corp_(?P<date>\\d{8})\\.xlsx',
)
ISSUANCE_0104A_TABLE = FamilySettings('cbr.corporate_lending.issuance_0104a', 'industry_issuance')
ISSUANCE_0104A = SeriesSpec(
    id='cbr.corporate_lending.issuance_0104a',
    publication=ISSUANCE_0104A_PUBLICATION,
    semantics=Semantics('credit_issuance_flow', ('report_date', 'territory', 'activity', 'currency', 'measure'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            ISSUANCE_0104A_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.issuance_0104a'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            ISSUANCE_0104A_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.issuance_0104a'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            ISSUANCE_0104A_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.issuance_0104a'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            ISSUANCE_0104A_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.issuance_0104a'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.corporate_lending.issuance_0104a', ('xlsx',), issue_required=True), Applicability(source_ids=frozenset({'cbr.corporate_lending.issuance_0104a'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.industries:validate"),
            SourceRequirement('cbr.corporate_lending.issuance_0104a', ('xlsx',), issue_required=True), Applicability(source_ids=frozenset({'cbr.corporate_lending.issuance_0104a'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.corporate_lending.issuance_0104a'), Applicability(source_ids=frozenset({'cbr.corporate_lending.issuance_0104a'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.industries:extract"),
            ISSUANCE_0104A_TABLE, Applicability(source_ids=frozenset({'cbr.corporate_lending.issuance_0104a'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.industries:interpret"),
            ISSUANCE_0104A_TABLE, Applicability(source_ids=frozenset({'cbr.corporate_lending.issuance_0104a'})),
        ),
    }),
)

SME_BORROWERS_INFO_PUBLICATION = Publication(
    'cbr.corporate_lending.sme_borrowers_info', 'cbr.corporate_lending', 'SME borrowers and loans',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/banksector/loans_to_corporations/02_02_SME_Borrowers_info.xlsx', None,
)
SME_BORROWERS_INFO_TABLE = StatisticalSettings(
    'cbr.corporate_lending.sme_borrowers_info', (
        TableVariant('table_1', 'Данные', 'statistics', None, 'mixed_source_periods', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
    ),
)
SME_BORROWERS_INFO = SeriesSpec(
    id='cbr.corporate_lending.sme_borrowers_info',
    publication=SME_BORROWERS_INFO_PUBLICATION,
    semantics=Semantics('credit_debt_stock', ('report_date', 'territory', 'activity', 'currency', 'measure'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            SME_BORROWERS_INFO_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_borrowers_info'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            SME_BORROWERS_INFO_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_borrowers_info'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            SME_BORROWERS_INFO_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_borrowers_info'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            SME_BORROWERS_INFO_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_borrowers_info'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.corporate_lending.sme_borrowers_info', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_borrowers_info'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.corporate_lending.sme_borrowers_info', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_borrowers_info'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.corporate_lending.sme_borrowers_info'), Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_borrowers_info'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            SME_BORROWERS_INFO_TABLE, Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_borrowers_info'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            SME_BORROWERS_INFO_TABLE, Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_borrowers_info'})),
        ),
    }),
)

SME_BY_ACTIVITY_PUBLICATION = Publication(
    'cbr.corporate_lending.sme_by_activity', 'cbr.corporate_lending', 'SME lending by OKVED2 classes',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/01_10_F_New_loans_sme_by_activity.xlsx', None,
)
SME_BY_ACTIVITY_TABLE = StatisticalSettings(
    'cbr.corporate_lending.sme_by_activity', (
        TableVariant('total', 'итого', 'statistics', 'flow', 'source_interval', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
        TableVariant('rub', 'в\\ рублях', 'statistics', 'flow', 'source_interval', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
        TableVariant('fx', 'в\\ валюте', 'statistics', 'flow', 'source_interval', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
    ), corporate=CorporateMeaning('01_10_F', 'history', 'activity', 'flow', 'SME'),
)
SME_BY_ACTIVITY = SeriesSpec(
    id='cbr.corporate_lending.sme_by_activity',
    publication=SME_BY_ACTIVITY_PUBLICATION,
    semantics=Semantics('credit_debt_stock', ('report_date', 'territory', 'activity', 'currency', 'measure'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            SME_BY_ACTIVITY_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_by_activity'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            SME_BY_ACTIVITY_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_by_activity'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            SME_BY_ACTIVITY_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_by_activity'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            SME_BY_ACTIVITY_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_by_activity'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.corporate_lending.sme_by_activity', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_by_activity'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.corporate_lending.sme_by_activity', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_by_activity'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.corporate_lending.sme_by_activity'), Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_by_activity'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            SME_BY_ACTIVITY_TABLE, Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_by_activity'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            SME_BY_ACTIVITY_TABLE, Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_by_activity'})),
        ),
    }),
)

SME_DEBT_PUBLICATION = Publication(
    'cbr.corporate_lending.sme_debt', 'cbr.corporate_lending', 'SME loan debt',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/01_11_Debt_sme.xlsx', None,
)
SME_DEBT_TABLE = StatisticalSettings(
    'cbr.corporate_lending.sme_debt', (
        TableVariant('total', 'итого', 'statistics', 'stock', 'as_of', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
        TableVariant('table_2', 'в\\ т\\.ч\\.\\ просроч\\.\\ итого', 'statistics', 'stock', 'as_of', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
        TableVariant('rub', 'в\\ рублях', 'statistics', 'stock', 'as_of', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
        TableVariant('table_4', 'в\\ т\\.ч\\.\\ просроч\\.\\ в\\ рублях', 'statistics', 'stock', 'as_of', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
        TableVariant('fx', 'в\\ инвалюте', 'statistics', 'stock', 'as_of', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
        TableVariant('table_6', 'в\\ т\\.ч\\.\\ просроч\\.\\ в\\ инвалюте', 'statistics', 'stock', 'as_of', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
    ), corporate=CorporateMeaning('01_11', 'history', 'portfolio', 'stock', 'SME'),
)
SME_DEBT = SeriesSpec(
    id='cbr.corporate_lending.sme_debt',
    publication=SME_DEBT_PUBLICATION,
    semantics=Semantics('credit_debt_stock', ('report_date', 'territory', 'activity', 'currency', 'measure'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            SME_DEBT_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_debt'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            SME_DEBT_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_debt'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            SME_DEBT_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_debt'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            SME_DEBT_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_debt'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.corporate_lending.sme_debt', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_debt'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.corporate_lending.sme_debt', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_debt'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.corporate_lending.sme_debt'), Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_debt'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            SME_DEBT_TABLE, Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_debt'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            SME_DEBT_TABLE, Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_debt'})),
        ),
    }),
)

SME_DEBT_ACTIVITY_PUBLICATION = Publication(
    'cbr.corporate_lending.sme_debt_activity', 'cbr.corporate_lending', 'SME debt by OKVED2 classes',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/01_11_F_Debt_sme_by_activity.xlsx', None,
)
SME_DEBT_ACTIVITY_TABLE = StatisticalSettings(
    'cbr.corporate_lending.sme_debt_activity', (
        TableVariant('total', 'итого', 'statistics', 'stock', 'as_of', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
        TableVariant('table_2', 'в\\ т\\.ч\\.\\ просроч\\.\\ итого', 'statistics', 'stock', 'as_of', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
        TableVariant('rub', 'в\\ рублях', 'statistics', 'stock', 'as_of', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
        TableVariant('table_4', 'в\\ т\\.ч\\.\\ просроч\\.\\ в\\ рублях', 'statistics', 'stock', 'as_of', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
        TableVariant('fx', 'в\\ инвалюте', 'statistics', 'stock', 'as_of', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
        TableVariant('table_6', 'в\\ т\\.ч\\.\\ просроч\\.\\ в\\ инвалюте', 'statistics', 'stock', 'as_of', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
    ), corporate=CorporateMeaning('01_11_F', 'history', 'activity', 'stock', 'SME'),
)
SME_DEBT_ACTIVITY = SeriesSpec(
    id='cbr.corporate_lending.sme_debt_activity',
    publication=SME_DEBT_ACTIVITY_PUBLICATION,
    semantics=Semantics('credit_debt_stock', ('report_date', 'territory', 'activity', 'currency', 'measure'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            SME_DEBT_ACTIVITY_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_debt_activity'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            SME_DEBT_ACTIVITY_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_debt_activity'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            SME_DEBT_ACTIVITY_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_debt_activity'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            SME_DEBT_ACTIVITY_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_debt_activity'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.corporate_lending.sme_debt_activity', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_debt_activity'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.corporate_lending.sme_debt_activity', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_debt_activity'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.corporate_lending.sme_debt_activity'), Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_debt_activity'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            SME_DEBT_ACTIVITY_TABLE, Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_debt_activity'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            SME_DEBT_ACTIVITY_TABLE, Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_debt_activity'})),
        ),
    }),
)

SME_DEBT_SUBJ_F_PUBLICATION = Publication(
    'cbr.corporate_lending.sme_debt_subj_f', 'cbr.corporate_lending', 'SME debt by region',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/01_13_F_Debt_sme_subj.xlsx', None,
)
SME_DEBT_SUBJ_F_TABLE = StatisticalSettings(
    'cbr.corporate_lending.sme_debt_subj_f', (
        TableVariant('table_1', 'МСП\\ итого', 'statistics', 'stock', 'as_of', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
        TableVariant('table_2', 'МСП\\ в\\ т\\.ч\\.\\ просроч\\.\\ итого', 'statistics', 'stock', 'as_of', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
        TableVariant('table_3', 'МСП\\ в\\ рублях', 'statistics', 'stock', 'as_of', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
        TableVariant('table_4', 'МСП\\ в\\ т\\.ч\\.\\ проср\\.\\ в\\ рублях', 'statistics', 'stock', 'as_of', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
        TableVariant('table_5', 'МСП\\ в\\ инвалюте', 'statistics', 'stock', 'as_of', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
        TableVariant('table_6', 'МСП\\ в\\ т\\.ч\\.\\ просроч\\.\\ в\\ инвалюте', 'statistics', 'stock', 'as_of', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
    ), corporate=CorporateMeaning('01_13_F', 'history', 'geography', 'stock', 'SME'),
)
SME_DEBT_SUBJ_F = SeriesSpec(
    id='cbr.corporate_lending.sme_debt_subj_f',
    publication=SME_DEBT_SUBJ_F_PUBLICATION,
    semantics=Semantics('credit_debt_stock', ('report_date', 'territory', 'activity', 'currency', 'measure'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            SME_DEBT_SUBJ_F_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_debt_subj_f'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            SME_DEBT_SUBJ_F_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_debt_subj_f'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            SME_DEBT_SUBJ_F_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_debt_subj_f'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            SME_DEBT_SUBJ_F_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_debt_subj_f'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.corporate_lending.sme_debt_subj_f', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_debt_subj_f'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.corporate_lending.sme_debt_subj_f', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_debt_subj_f'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.corporate_lending.sme_debt_subj_f'), Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_debt_subj_f'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            SME_DEBT_SUBJ_F_TABLE, Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_debt_subj_f'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            SME_DEBT_SUBJ_F_TABLE, Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_debt_subj_f'})),
        ),
    }),
)

SME_DEBT_SUBJ_I_PUBLICATION = Publication(
    'cbr.corporate_lending.sme_debt_subj_i', 'cbr.corporate_lending', 'SME individual entrepreneur debt by region',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/01_13_I_Debt_sme_subj.xlsx', None,
)
SME_DEBT_SUBJ_I_TABLE = StatisticalSettings(
    'cbr.corporate_lending.sme_debt_subj_i', (
        TableVariant('table_1', 'ИП\\ итого', 'statistics', 'stock', 'as_of', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
        TableVariant('table_2', 'ИП\\ в\\ т\\.ч\\.\\ просроч\\.\\ итого', 'statistics', 'stock', 'as_of', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
        TableVariant('table_3', 'ИП\\ в\\ рублях', 'statistics', 'stock', 'as_of', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
        TableVariant('table_4', 'ИП\\ в\\ т\\.ч\\ просроч\\.\\ в\\ рублях', 'statistics', 'stock', 'as_of', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
        TableVariant('table_5', 'ИП\\ в\\ инвалюте', 'statistics', 'stock', 'as_of', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
        TableVariant('table_6', 'ИП\\ в\\ т\\.ч\\.\\ просроч\\.\\ в\\ инвалюте', 'statistics', 'stock', 'as_of', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
    ), corporate=CorporateMeaning('01_13_I', 'history', 'geography', 'stock', 'SME_IE'),
)
SME_DEBT_SUBJ_I = SeriesSpec(
    id='cbr.corporate_lending.sme_debt_subj_i',
    publication=SME_DEBT_SUBJ_I_PUBLICATION,
    semantics=Semantics('credit_debt_stock', ('report_date', 'territory', 'activity', 'currency', 'measure'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            SME_DEBT_SUBJ_I_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_debt_subj_i'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            SME_DEBT_SUBJ_I_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_debt_subj_i'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            SME_DEBT_SUBJ_I_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_debt_subj_i'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            SME_DEBT_SUBJ_I_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_debt_subj_i'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.corporate_lending.sme_debt_subj_i', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_debt_subj_i'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.corporate_lending.sme_debt_subj_i', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_debt_subj_i'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.corporate_lending.sme_debt_subj_i'), Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_debt_subj_i'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            SME_DEBT_SUBJ_I_TABLE, Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_debt_subj_i'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            SME_DEBT_SUBJ_I_TABLE, Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_debt_subj_i'})),
        ),
    }),
)

SME_FD_OKVED2_PUBLICATION = Publication(
    'cbr.corporate_lending.sme_fd_okved2', 'cbr.corporate_lending', 'SME loans by federal district and OKVED2 section',
    'dated', ('xlsx',), 'index', SORS_INDEX, '01_12_A_Loans_sme_by_fd_activity_(?P<date>\\d{8})\\.xlsx',
)
SME_FD_OKVED2_TABLE = StatisticalSettings(
    'cbr.corporate_lending.sme_fd_okved2', (
        TableVariant('table_1', '.*', 'statistics', None, 'mixed_source_periods', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
    ), corporate=CorporateMeaning('01_12_A', 'district', 'geography_activity', 'mixed', 'SME'),
)
SME_FD_OKVED2 = SeriesSpec(
    id='cbr.corporate_lending.sme_fd_okved2',
    publication=SME_FD_OKVED2_PUBLICATION,
    semantics=Semantics('credit_debt_stock', ('report_date', 'territory', 'activity', 'currency', 'measure'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            SME_FD_OKVED2_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_fd_okved2'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            SME_FD_OKVED2_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_fd_okved2'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            SME_FD_OKVED2_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_fd_okved2'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            SME_FD_OKVED2_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_fd_okved2'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.corporate_lending.sme_fd_okved2', ('xlsx',), issue_required=True), Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_fd_okved2'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.corporate_lending.sme_fd_okved2', ('xlsx',), issue_required=True), Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_fd_okved2'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.corporate_lending.sme_fd_okved2'), Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_fd_okved2'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            SME_FD_OKVED2_TABLE, Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_fd_okved2'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            SME_FD_OKVED2_TABLE, Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_fd_okved2'})),
        ),
    }),
)

SME_IE_DEBT_ACTIVITY_PUBLICATION = Publication(
    'cbr.corporate_lending.sme_ie_debt_activity', 'cbr.corporate_lending', 'SME individual entrepreneur debt by OKVED2 classes',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/01_11_I_Debt_ie_by_activity.xlsx', None,
)
SME_IE_DEBT_ACTIVITY_TABLE = StatisticalSettings(
    'cbr.corporate_lending.sme_ie_debt_activity', (
        TableVariant('total', 'итого', 'statistics', 'stock', 'as_of', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
        TableVariant('table_2', 'в\\ т\\.ч\\.\\ просроч\\.\\ итого', 'statistics', 'stock', 'as_of', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
        TableVariant('rub', 'в\\ рублях', 'statistics', 'stock', 'as_of', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
        TableVariant('table_4', 'в\\ т\\.ч\\.\\ просроч\\.\\ в\\ рублях', 'statistics', 'stock', 'as_of', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
        TableVariant('fx', 'в\\ инвалюте', 'statistics', 'stock', 'as_of', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
        TableVariant('table_6', 'в\\ т\\.ч\\.\\ просроч\\.\\ в\\ инвалюте', 'statistics', 'stock', 'as_of', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
    ), corporate=CorporateMeaning('01_11_I', 'history', 'activity', 'stock', 'SME_IE'),
)
SME_IE_DEBT_ACTIVITY = SeriesSpec(
    id='cbr.corporate_lending.sme_ie_debt_activity',
    publication=SME_IE_DEBT_ACTIVITY_PUBLICATION,
    semantics=Semantics('credit_debt_stock', ('report_date', 'territory', 'activity', 'currency', 'measure'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            SME_IE_DEBT_ACTIVITY_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_ie_debt_activity'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            SME_IE_DEBT_ACTIVITY_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_ie_debt_activity'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            SME_IE_DEBT_ACTIVITY_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_ie_debt_activity'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            SME_IE_DEBT_ACTIVITY_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_ie_debt_activity'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.corporate_lending.sme_ie_debt_activity', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_ie_debt_activity'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.corporate_lending.sme_ie_debt_activity', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_ie_debt_activity'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.corporate_lending.sme_ie_debt_activity'), Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_ie_debt_activity'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            SME_IE_DEBT_ACTIVITY_TABLE, Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_ie_debt_activity'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            SME_IE_DEBT_ACTIVITY_TABLE, Applicability(source_ids=frozenset({'cbr.corporate_lending.sme_ie_debt_activity'})),
        ),
    }),
)

STRUCTURE_BY_BENCHMARK_INTEREST_RATE_TYPE_PUBLICATION = Publication(
    'cbr.corporate_lending.structure_by_benchmark_interest_rate_type', 'cbr.corporate_lending', 'Corporate debt by benchmark interest rate type',
    'rolling', ('xlsx',), 'fixed', 'https://cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/02_03_Debt_structure_by_benchmark_interest_rate_type.xlsx', None,
)
STRUCTURE_BY_BENCHMARK_INTEREST_RATE_TYPE_TABLE = StatisticalSettings(
    'cbr.corporate_lending.structure_by_benchmark_interest_rate_type', (
        TableVariant('table_1', 'Данные', 'statistics', None, 'mixed_source_periods', ('source_activity_or_geography', 'denomination_group', 'borrower_perimeter'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Corporate, SME and individual-entrepreneur perimeters and published activity classifications remain distinct. Source cells retain every period before model selection.'),
    ),
)
STRUCTURE_BY_BENCHMARK_INTEREST_RATE_TYPE = SeriesSpec(
    id='cbr.corporate_lending.structure_by_benchmark_interest_rate_type',
    publication=STRUCTURE_BY_BENCHMARK_INTEREST_RATE_TYPE_PUBLICATION,
    semantics=Semantics('credit_debt_stock', ('report_date', 'territory', 'activity', 'currency', 'measure'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            STRUCTURE_BY_BENCHMARK_INTEREST_RATE_TYPE_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.structure_by_benchmark_interest_rate_type'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            STRUCTURE_BY_BENCHMARK_INTEREST_RATE_TYPE_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.structure_by_benchmark_interest_rate_type'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            STRUCTURE_BY_BENCHMARK_INTEREST_RATE_TYPE_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.structure_by_benchmark_interest_rate_type'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            STRUCTURE_BY_BENCHMARK_INTEREST_RATE_TYPE_PUBLICATION, Applicability(source_ids=frozenset({'cbr.corporate_lending.structure_by_benchmark_interest_rate_type'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.corporate_lending.structure_by_benchmark_interest_rate_type', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.corporate_lending.structure_by_benchmark_interest_rate_type'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.corporate_lending.structure_by_benchmark_interest_rate_type', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.corporate_lending.structure_by_benchmark_interest_rate_type'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.corporate_lending.structure_by_benchmark_interest_rate_type'), Applicability(source_ids=frozenset({'cbr.corporate_lending.structure_by_benchmark_interest_rate_type'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            STRUCTURE_BY_BENCHMARK_INTEREST_RATE_TYPE_TABLE, Applicability(source_ids=frozenset({'cbr.corporate_lending.structure_by_benchmark_interest_rate_type'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            STRUCTURE_BY_BENCHMARK_INTEREST_RATE_TYPE_TABLE, Applicability(source_ids=frozenset({'cbr.corporate_lending.structure_by_benchmark_interest_rate_type'})),
        ),
    }),
)

