"""Explicit Bank of Russia monetary_statistics source records and action settings."""
from types import MappingProxyType
from stratbox.capabilities.model.domains import SeriesSpec, CommandSpec, Applicability
from stratbox.capabilities.model.methods import MethodRef
from stratbox.domains.cbr.common.contracts import Publication, Semantics, StatisticalSettings, TableVariant, FormSettings, FamilySettings, SourceRequirement, MappingRules
from stratbox.domains.cbr.common.publications import SORS_INDEX, FORMS_INDEX, ESCROW_INDEX, OFFICES_PAGE, TERRITORIAL_INDEX

ANNEX_SURVEY_DC_PUBLICATION = Publication(
    'cbr.monetary_statistics.annex_survey_dc', 'cbr.monetary_statistics', 'Banking system survey annex',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/credit_statistics/survey/annex_survey_dc.xlsx', None,
)
ANNEX_SURVEY_DC_TABLE = StatisticalSettings(
    'cbr.monetary_statistics.annex_survey_dc', (
        TableVariant('table_1', 'Приложение\\ к\\ обзору', 'statistics', 'stock', 'as_of', ('source_hierarchy', 'survey_perimeter', 'seasonal_adjustment', 'measure_basis'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Central bank, credit institution and consolidated banking-system perimeters remain separate. Published adjusted growth and transactions differ from computed stock changes.'),
        TableVariant('table_2', 'Приложение\\ к\\ обзору\\ \\(с\\.к\\)', 'statistics', 'stock', 'as_of', ('source_hierarchy', 'survey_perimeter', 'seasonal_adjustment', 'measure_basis'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Central bank, credit institution and consolidated banking-system perimeters remain separate. Published adjusted growth and transactions differ from computed stock changes.', unit_anchor='A2'),
        TableVariant('seasonal_metadata', 'Метаданные', 'metadata', None, 'mixed_source_periods', ('source_hierarchy', 'survey_perimeter', 'seasonal_adjustment', 'measure_basis'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Central bank, credit institution and consolidated banking-system perimeters remain separate. Published adjusted growth and transactions differ from computed stock changes.'),
    ),
)
ANNEX_SURVEY_DC = SeriesSpec(
    id='cbr.monetary_statistics.annex_survey_dc',
    publication=ANNEX_SURVEY_DC_PUBLICATION,
    semantics=Semantics('publisher_defined', ('publication', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            ANNEX_SURVEY_DC_PUBLICATION, Applicability(source_ids=frozenset({'cbr.monetary_statistics.annex_survey_dc'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            ANNEX_SURVEY_DC_PUBLICATION, Applicability(source_ids=frozenset({'cbr.monetary_statistics.annex_survey_dc'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            ANNEX_SURVEY_DC_PUBLICATION, Applicability(source_ids=frozenset({'cbr.monetary_statistics.annex_survey_dc'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            ANNEX_SURVEY_DC_PUBLICATION, Applicability(source_ids=frozenset({'cbr.monetary_statistics.annex_survey_dc'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.monetary_statistics.annex_survey_dc', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.monetary_statistics.annex_survey_dc'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.monetary_statistics.annex_survey_dc', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.monetary_statistics.annex_survey_dc'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.monetary_statistics.annex_survey_dc'), Applicability(source_ids=frozenset({'cbr.monetary_statistics.annex_survey_dc'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            ANNEX_SURVEY_DC_TABLE, Applicability(source_ids=frozenset({'cbr.monetary_statistics.annex_survey_dc'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            ANNEX_SURVEY_DC_TABLE, Applicability(source_ids=frozenset({'cbr.monetary_statistics.annex_survey_dc'})),
        ),
    }),
)

BALANCE_ODC_PUBLICATION = Publication(
    'cbr.monetary_statistics.balance_odc', 'cbr.monetary_statistics', 'Credit institution balance sheet',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/credit_statistics/survey/balance_odc.xlsx', None,
)
BALANCE_ODC_TABLE = StatisticalSettings(
    'cbr.monetary_statistics.balance_odc', (
        TableVariant('balances', 'Баланс\\ КО', 'statistics', 'stock', 'as_of', ('source_hierarchy', 'survey_perimeter', 'seasonal_adjustment', 'measure_basis'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Central bank, credit institution and consolidated banking-system perimeters remain separate. Published adjusted growth and transactions differ from computed stock changes.'),
        TableVariant('table_2', 'Кредиты', 'statistics', 'stock', 'as_of', ('source_hierarchy', 'survey_perimeter', 'seasonal_adjustment', 'measure_basis'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Central bank, credit institution and consolidated banking-system perimeters remain separate. Published adjusted growth and transactions differ from computed stock changes.', unit_anchor='A2'),
        TableVariant('table_3', 'Депозиты\\ в\\ М2Х', 'statistics', 'stock', 'as_of', ('source_hierarchy', 'survey_perimeter', 'seasonal_adjustment', 'measure_basis'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Central bank, credit institution and consolidated banking-system perimeters remain separate. Published adjusted growth and transactions differ from computed stock changes.', unit_anchor='A2'),
        TableVariant('table_4', 'Прочие\\ депозиты', 'statistics', 'stock', 'as_of', ('source_hierarchy', 'survey_perimeter', 'seasonal_adjustment', 'measure_basis'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Central bank, credit institution and consolidated banking-system perimeters remain separate. Published adjusted growth and transactions differ from computed stock changes.', unit_anchor='A2'),
    ),
)
BALANCE_ODC = SeriesSpec(
    id='cbr.monetary_statistics.balance_odc',
    publication=BALANCE_ODC_PUBLICATION,
    semantics=Semantics('publisher_defined', ('publication', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            BALANCE_ODC_PUBLICATION, Applicability(source_ids=frozenset({'cbr.monetary_statistics.balance_odc'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            BALANCE_ODC_PUBLICATION, Applicability(source_ids=frozenset({'cbr.monetary_statistics.balance_odc'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            BALANCE_ODC_PUBLICATION, Applicability(source_ids=frozenset({'cbr.monetary_statistics.balance_odc'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            BALANCE_ODC_PUBLICATION, Applicability(source_ids=frozenset({'cbr.monetary_statistics.balance_odc'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.monetary_statistics.balance_odc', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.monetary_statistics.balance_odc'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.monetary_statistics.balance_odc', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.monetary_statistics.balance_odc'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.monetary_statistics.balance_odc'), Applicability(source_ids=frozenset({'cbr.monetary_statistics.balance_odc'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            BALANCE_ODC_TABLE, Applicability(source_ids=frozenset({'cbr.monetary_statistics.balance_odc'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            BALANCE_ODC_TABLE, Applicability(source_ids=frozenset({'cbr.monetary_statistics.balance_odc'})),
        ),
    }),
)

MONETARY_AGG_PUBLICATION = Publication(
    'cbr.monetary_statistics.monetary_agg', 'cbr.monetary_statistics', 'Monetary aggregates',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/credit_statistics/monetary_agg.xlsx', None,
)
MONETARY_AGG_TABLE = StatisticalSettings(
    'cbr.monetary_statistics.monetary_agg', (
        TableVariant('table_1', 'Денежные\\ агрегаты', 'statistics', 'stock', 'as_of', ('source_hierarchy', 'survey_perimeter', 'seasonal_adjustment', 'measure_basis'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Central bank, credit institution and consolidated banking-system perimeters remain separate. Published adjusted growth and transactions differ from computed stock changes.'),
        TableVariant('table_2', 'Денежные\\ агрегаты_Сектора', 'statistics', 'stock', 'as_of', ('source_hierarchy', 'survey_perimeter', 'seasonal_adjustment', 'measure_basis'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Central bank, credit institution and consolidated banking-system perimeters remain separate. Published adjusted growth and transactions differ from computed stock changes.', unit_anchor='A2'),
        TableVariant('reported_growth_yoy', 'Годовые\\ темпы\\ прироста', 'statistics', 'ratio', 'source_interval', ('source_hierarchy', 'survey_perimeter', 'seasonal_adjustment', 'measure_basis'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Central bank, credit institution and consolidated banking-system perimeters remain separate. Published adjusted growth and transactions differ from computed stock changes.'),
        TableVariant('reported_growth_ytd', 'Темпы\\ прироста\\ к\\ началу\\ год', 'statistics', 'ratio', 'source_interval', ('source_hierarchy', 'survey_perimeter', 'seasonal_adjustment', 'measure_basis'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Central bank, credit institution and consolidated banking-system perimeters remain separate. Published adjusted growth and transactions differ from computed stock changes.'),
        TableVariant('reported_growth_mom', 'Темпы\\ прироста\\ за\\ месяц', 'statistics', 'ratio', 'source_interval', ('source_hierarchy', 'survey_perimeter', 'seasonal_adjustment', 'measure_basis'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Central bank, credit institution and consolidated banking-system perimeters remain separate. Published adjusted growth and transactions differ from computed stock changes.'),
    ),
)
MONETARY_AGG = SeriesSpec(
    id='cbr.monetary_statistics.monetary_agg',
    publication=MONETARY_AGG_PUBLICATION,
    semantics=Semantics('publisher_defined', ('publication', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            MONETARY_AGG_PUBLICATION, Applicability(source_ids=frozenset({'cbr.monetary_statistics.monetary_agg'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            MONETARY_AGG_PUBLICATION, Applicability(source_ids=frozenset({'cbr.monetary_statistics.monetary_agg'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            MONETARY_AGG_PUBLICATION, Applicability(source_ids=frozenset({'cbr.monetary_statistics.monetary_agg'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            MONETARY_AGG_PUBLICATION, Applicability(source_ids=frozenset({'cbr.monetary_statistics.monetary_agg'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.monetary_statistics.monetary_agg', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.monetary_statistics.monetary_agg'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.monetary_statistics.monetary_agg', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.monetary_statistics.monetary_agg'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.monetary_statistics.monetary_agg'), Applicability(source_ids=frozenset({'cbr.monetary_statistics.monetary_agg'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            MONETARY_AGG_TABLE, Applicability(source_ids=frozenset({'cbr.monetary_statistics.monetary_agg'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            MONETARY_AGG_TABLE, Applicability(source_ids=frozenset({'cbr.monetary_statistics.monetary_agg'})),
        ),
    }),
)

SURVEY_CB_PUBLICATION = Publication(
    'cbr.monetary_statistics.survey_cb', 'cbr.monetary_statistics', 'Central bank survey',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/credit_statistics/survey/survey_cb.xlsx', None,
)
SURVEY_CB_TABLE = StatisticalSettings(
    'cbr.monetary_statistics.survey_cb', (
        TableVariant('table_1', 'Агрегированная\\ форма\\ обзора', 'statistics', 'stock', 'as_of', ('source_hierarchy', 'survey_perimeter', 'seasonal_adjustment', 'measure_basis'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Central bank, credit institution and consolidated banking-system perimeters remain separate. Published adjusted growth and transactions differ from computed stock changes.'),
        TableVariant('reported_transactions', 'Операции', 'statistics', 'flow', 'source_interval', ('source_hierarchy', 'survey_perimeter', 'seasonal_adjustment', 'measure_basis'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Central bank, credit institution and consolidated banking-system perimeters remain separate. Published adjusted growth and transactions differ from computed stock changes.'),
        TableVariant('reported_growth_mom', 'ММ_%', 'statistics', 'ratio', 'source_interval', ('source_hierarchy', 'survey_perimeter', 'seasonal_adjustment', 'measure_basis'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Central bank, credit institution and consolidated banking-system perimeters remain separate. Published adjusted growth and transactions differ from computed stock changes.'),
        TableVariant('reported_growth_yoy', 'ГГ_%', 'statistics', 'ratio', 'source_interval', ('source_hierarchy', 'survey_perimeter', 'seasonal_adjustment', 'measure_basis'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Central bank, credit institution and consolidated banking-system perimeters remain separate. Published adjusted growth and transactions differ from computed stock changes.'),
        TableVariant('reported_growth_ytd', 'К\\ началу\\ года_%', 'statistics', 'ratio', 'source_interval', ('source_hierarchy', 'survey_perimeter', 'seasonal_adjustment', 'measure_basis'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Central bank, credit institution and consolidated banking-system perimeters remain separate. Published adjusted growth and transactions differ from computed stock changes.'),
    ),
)
SURVEY_CB = SeriesSpec(
    id='cbr.monetary_statistics.survey_cb',
    publication=SURVEY_CB_PUBLICATION,
    semantics=Semantics('publisher_defined', ('publication', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            SURVEY_CB_PUBLICATION, Applicability(source_ids=frozenset({'cbr.monetary_statistics.survey_cb'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            SURVEY_CB_PUBLICATION, Applicability(source_ids=frozenset({'cbr.monetary_statistics.survey_cb'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            SURVEY_CB_PUBLICATION, Applicability(source_ids=frozenset({'cbr.monetary_statistics.survey_cb'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            SURVEY_CB_PUBLICATION, Applicability(source_ids=frozenset({'cbr.monetary_statistics.survey_cb'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.monetary_statistics.survey_cb', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.monetary_statistics.survey_cb'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.monetary_statistics.survey_cb', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.monetary_statistics.survey_cb'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.monetary_statistics.survey_cb'), Applicability(source_ids=frozenset({'cbr.monetary_statistics.survey_cb'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            SURVEY_CB_TABLE, Applicability(source_ids=frozenset({'cbr.monetary_statistics.survey_cb'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            SURVEY_CB_TABLE, Applicability(source_ids=frozenset({'cbr.monetary_statistics.survey_cb'})),
        ),
    }),
)

SURVEY_DC_NEW_PUBLICATION = Publication(
    'cbr.monetary_statistics.survey_dc_new', 'cbr.monetary_statistics', 'Banking system survey',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/credit_statistics/survey/survey_dc_new.xlsx', None,
)
SURVEY_DC_NEW_TABLE = StatisticalSettings(
    'cbr.monetary_statistics.survey_dc_new', (
        TableVariant('table_1', 'Агрегированная\\ форма\\ обзора', 'statistics', 'stock', 'as_of', ('source_hierarchy', 'survey_perimeter', 'seasonal_adjustment', 'measure_basis'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Central bank, credit institution and consolidated banking-system perimeters remain separate. Published adjusted growth and transactions differ from computed stock changes.'),
        TableVariant('reported_transactions', 'Операции', 'statistics', 'flow', 'source_interval', ('source_hierarchy', 'survey_perimeter', 'seasonal_adjustment', 'measure_basis'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Central bank, credit institution and consolidated banking-system perimeters remain separate. Published adjusted growth and transactions differ from computed stock changes.'),
        TableVariant('reported_growth_mom', 'MM_%', 'statistics', 'ratio', 'source_interval', ('source_hierarchy', 'survey_perimeter', 'seasonal_adjustment', 'measure_basis'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Central bank, credit institution and consolidated banking-system perimeters remain separate. Published adjusted growth and transactions differ from computed stock changes.'),
        TableVariant('reported_growth_yoy', 'ГГ_%', 'statistics', 'ratio', 'source_interval', ('source_hierarchy', 'survey_perimeter', 'seasonal_adjustment', 'measure_basis'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Central bank, credit institution and consolidated banking-system perimeters remain separate. Published adjusted growth and transactions differ from computed stock changes.'),
        TableVariant('reported_growth_ytd', 'К\\ началу\\ года_%', 'statistics', 'ratio', 'source_interval', ('source_hierarchy', 'survey_perimeter', 'seasonal_adjustment', 'measure_basis'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Central bank, credit institution and consolidated banking-system perimeters remain separate. Published adjusted growth and transactions differ from computed stock changes.'),
    ),
)
SURVEY_DC_NEW = SeriesSpec(
    id='cbr.monetary_statistics.survey_dc_new',
    publication=SURVEY_DC_NEW_PUBLICATION,
    semantics=Semantics('publisher_defined', ('publication', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            SURVEY_DC_NEW_PUBLICATION, Applicability(source_ids=frozenset({'cbr.monetary_statistics.survey_dc_new'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            SURVEY_DC_NEW_PUBLICATION, Applicability(source_ids=frozenset({'cbr.monetary_statistics.survey_dc_new'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            SURVEY_DC_NEW_PUBLICATION, Applicability(source_ids=frozenset({'cbr.monetary_statistics.survey_dc_new'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            SURVEY_DC_NEW_PUBLICATION, Applicability(source_ids=frozenset({'cbr.monetary_statistics.survey_dc_new'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.monetary_statistics.survey_dc_new', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.monetary_statistics.survey_dc_new'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.monetary_statistics.survey_dc_new', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.monetary_statistics.survey_dc_new'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.monetary_statistics.survey_dc_new'), Applicability(source_ids=frozenset({'cbr.monetary_statistics.survey_dc_new'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            SURVEY_DC_NEW_TABLE, Applicability(source_ids=frozenset({'cbr.monetary_statistics.survey_dc_new'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            SURVEY_DC_NEW_TABLE, Applicability(source_ids=frozenset({'cbr.monetary_statistics.survey_dc_new'})),
        ),
    }),
)

SURVEY_ODC_PUBLICATION = Publication(
    'cbr.monetary_statistics.survey_odc', 'cbr.monetary_statistics', 'Credit institution survey',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/credit_statistics/survey/survey_odc.xlsx', None,
)
SURVEY_ODC_TABLE = StatisticalSettings(
    'cbr.monetary_statistics.survey_odc', (
        TableVariant('table_1', 'Агрегированная\\ форма\\ обзора', 'statistics', 'stock', 'as_of', ('source_hierarchy', 'survey_perimeter', 'seasonal_adjustment', 'measure_basis'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Central bank, credit institution and consolidated banking-system perimeters remain separate. Published adjusted growth and transactions differ from computed stock changes.'),
        TableVariant('reported_transactions', 'Операции', 'statistics', 'flow', 'source_interval', ('source_hierarchy', 'survey_perimeter', 'seasonal_adjustment', 'measure_basis'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Central bank, credit institution and consolidated banking-system perimeters remain separate. Published adjusted growth and transactions differ from computed stock changes.'),
        TableVariant('reported_growth_mom', 'MM_%', 'statistics', 'ratio', 'source_interval', ('source_hierarchy', 'survey_perimeter', 'seasonal_adjustment', 'measure_basis'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Central bank, credit institution and consolidated banking-system perimeters remain separate. Published adjusted growth and transactions differ from computed stock changes.'),
        TableVariant('reported_growth_yoy', 'ГГ_%', 'statistics', 'ratio', 'source_interval', ('source_hierarchy', 'survey_perimeter', 'seasonal_adjustment', 'measure_basis'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Central bank, credit institution and consolidated banking-system perimeters remain separate. Published adjusted growth and transactions differ from computed stock changes.'),
        TableVariant('reported_growth_ytd', 'К\\ началу\\ года_%', 'statistics', 'ratio', 'source_interval', ('source_hierarchy', 'survey_perimeter', 'seasonal_adjustment', 'measure_basis'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Central bank, credit institution and consolidated banking-system perimeters remain separate. Published adjusted growth and transactions differ from computed stock changes.'),
    ),
)
SURVEY_ODC = SeriesSpec(
    id='cbr.monetary_statistics.survey_odc',
    publication=SURVEY_ODC_PUBLICATION,
    semantics=Semantics('publisher_defined', ('publication', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            SURVEY_ODC_PUBLICATION, Applicability(source_ids=frozenset({'cbr.monetary_statistics.survey_odc'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            SURVEY_ODC_PUBLICATION, Applicability(source_ids=frozenset({'cbr.monetary_statistics.survey_odc'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            SURVEY_ODC_PUBLICATION, Applicability(source_ids=frozenset({'cbr.monetary_statistics.survey_odc'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            SURVEY_ODC_PUBLICATION, Applicability(source_ids=frozenset({'cbr.monetary_statistics.survey_odc'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.monetary_statistics.survey_odc', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.monetary_statistics.survey_odc'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.monetary_statistics.survey_odc', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.monetary_statistics.survey_odc'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.monetary_statistics.survey_odc'), Applicability(source_ids=frozenset({'cbr.monetary_statistics.survey_odc'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            SURVEY_ODC_TABLE, Applicability(source_ids=frozenset({'cbr.monetary_statistics.survey_odc'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            SURVEY_ODC_TABLE, Applicability(source_ids=frozenset({'cbr.monetary_statistics.survey_odc'})),
        ),
    }),
)

