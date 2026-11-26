"""Explicit Bank of Russia banking_sector_structure source records and action settings."""
from types import MappingProxyType
from stratbox.capabilities.model.domains import SeriesSpec, CommandSpec, Applicability
from stratbox.capabilities.model.methods import MethodRef
from stratbox.domains.cbr.common.contracts import Publication, Semantics, StatisticalSettings, TableVariant, FormSettings, FamilySettings, SourceRequirement, MappingRules
from stratbox.domains.cbr.common.publications import SORS_INDEX, FORMS_INDEX, ESCROW_INDEX, OFFICES_PAGE, TERRITORIAL_INDEX

FAMILY_ID = 'cbr.banking_sector_structure'

OBS_TABLE_20S_PUBLICATION = Publication(
    'cbr.banking_sector_structure.obs_table_20s', FAMILY_ID, 'Banking sector balance sheet and loan maturity structure',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/Content/Document/File/115862/obs_tabl20%D1%81.xlsx', None,
)
OBS_TABLE_20S_TABLE = StatisticalSettings(
    OBS_TABLE_20S_PUBLICATION.series_id, (
        TableVariant('table_1', 'Активы\\ \\-\\ всего', 'statistics', 'stock', 'as_of', ('source_hierarchy', 'balance_side', 'valuation_currency'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published balance-sheet hierarchy, valuation currency and loan maturity components are preserved without implicit summation.'),
        TableVariant('table_2', 'Активы\\ \\-\\ рубли', 'statistics', 'stock', 'as_of', ('source_hierarchy', 'balance_side', 'valuation_currency'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published balance-sheet hierarchy, valuation currency and loan maturity components are preserved without implicit summation.'),
        TableVariant('table_3', 'Активы\\ \\-\\ валюта', 'statistics', 'stock', 'as_of', ('source_hierarchy', 'balance_side', 'valuation_currency'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published balance-sheet hierarchy, valuation currency and loan maturity components are preserved without implicit summation.'),
        TableVariant('table_4', 'Активы\\ \\-\\ в\\ ин\\.\\ валюте\\ \\$', 'statistics', 'stock', 'as_of', ('source_hierarchy', 'balance_side', 'valuation_currency'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published balance-sheet hierarchy, valuation currency and loan maturity components are preserved without implicit summation.'),
        TableVariant('table_5', 'Пассивы\\ \\-\\ всего', 'statistics', 'stock', 'as_of', ('source_hierarchy', 'balance_side', 'valuation_currency'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published balance-sheet hierarchy, valuation currency and loan maturity components are preserved without implicit summation.'),
        TableVariant('table_6', 'Пассивы\\ \\-\\ рубли', 'statistics', 'stock', 'as_of', ('source_hierarchy', 'balance_side', 'valuation_currency'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published balance-sheet hierarchy, valuation currency and loan maturity components are preserved without implicit summation.'),
        TableVariant('table_7', 'Пассивы\\ \\-\\ валюта', 'statistics', 'stock', 'as_of', ('source_hierarchy', 'balance_side', 'valuation_currency'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published balance-sheet hierarchy, valuation currency and loan maturity components are preserved without implicit summation.'),
        TableVariant('table_8', 'Пассивы\\ \\-\\ в\\ ин\\.\\ валюте\\ \\$', 'statistics', 'stock', 'as_of', ('source_hierarchy', 'balance_side', 'valuation_currency'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published balance-sheet hierarchy, valuation currency and loan maturity components are preserved without implicit summation.'),
        TableVariant('table_9', 'Корпоративные\\ кредиты\\ по\\ срокам', 'statistics', 'stock', 'as_of', ('source_hierarchy', 'balance_side', 'valuation_currency'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published balance-sheet hierarchy, valuation currency and loan maturity components are preserved without implicit summation.'),
        TableVariant('table_10', 'Кредиты\\ физ\\.лицам\\ по\\ срокам', 'statistics', 'stock', 'as_of', ('source_hierarchy', 'balance_side', 'valuation_currency'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Published balance-sheet hierarchy, valuation currency and loan maturity components are preserved without implicit summation.'),
    ),
)
OBS_TABLE_20S = SeriesSpec(
    id=OBS_TABLE_20S_PUBLICATION.series_id,
    publication=OBS_TABLE_20S_PUBLICATION,
    semantics=Semantics('publisher_defined', ('publication', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            OBS_TABLE_20S_PUBLICATION, Applicability(source_ids=frozenset({OBS_TABLE_20S_PUBLICATION.series_id})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            OBS_TABLE_20S_PUBLICATION, Applicability(source_ids=frozenset({OBS_TABLE_20S_PUBLICATION.series_id})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            OBS_TABLE_20S_PUBLICATION, Applicability(source_ids=frozenset({OBS_TABLE_20S_PUBLICATION.series_id})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            OBS_TABLE_20S_PUBLICATION, Applicability(source_ids=frozenset({OBS_TABLE_20S_PUBLICATION.series_id})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement(OBS_TABLE_20S_PUBLICATION.series_id, OBS_TABLE_20S_PUBLICATION.formats, issue_required=OBS_TABLE_20S_PUBLICATION.issue_model == 'dated', locator=OBS_TABLE_20S_PUBLICATION.locator, filename_pattern=OBS_TABLE_20S_PUBLICATION.filename_pattern, publication_kind=OBS_TABLE_20S_PUBLICATION.kind), Applicability(source_ids=frozenset({OBS_TABLE_20S_PUBLICATION.series_id})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement(OBS_TABLE_20S_PUBLICATION.series_id, OBS_TABLE_20S_PUBLICATION.formats, issue_required=OBS_TABLE_20S_PUBLICATION.issue_model == 'dated', locator=OBS_TABLE_20S_PUBLICATION.locator, filename_pattern=OBS_TABLE_20S_PUBLICATION.filename_pattern, publication_kind=OBS_TABLE_20S_PUBLICATION.kind), Applicability(source_ids=frozenset({OBS_TABLE_20S_PUBLICATION.series_id})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules(OBS_TABLE_20S_PUBLICATION.series_id), Applicability(source_ids=frozenset({OBS_TABLE_20S_PUBLICATION.series_id})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            OBS_TABLE_20S_TABLE, Applicability(source_ids=frozenset({OBS_TABLE_20S_PUBLICATION.series_id})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            OBS_TABLE_20S_TABLE, Applicability(source_ids=frozenset({OBS_TABLE_20S_PUBLICATION.series_id})),
        ),
    }),
)

