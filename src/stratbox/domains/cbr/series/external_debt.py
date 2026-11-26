"""Explicit Bank of Russia external_debt source records and action settings."""
from types import MappingProxyType
from stratbox.capabilities.model.domains import SeriesSpec, CommandSpec, Applicability
from stratbox.capabilities.model.methods import MethodRef
from stratbox.domains.cbr.common.contracts import Publication, Semantics, StatisticalSettings, TableVariant, FormSettings, FamilySettings, SourceRequirement, MappingRules
from stratbox.domains.cbr.common.publications import SORS_INDEX, FORMS_INDEX, ESCROW_INDEX, OFFICES_PAGE, TERRITORIAL_INDEX

DEBT_CUR_MAT_NEW_PUBLICATION = Publication(
    'cbr.external_debt.debt_cur-mat_new', 'cbr.external_debt', 'External debt by currency and maturity',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/credit_statistics/debt/debt_cur-mat_new.xlsx', None,
)
DEBT_CUR_MAT_NEW_TABLE = StatisticalSettings(
    'cbr.external_debt.debt_cur-mat_new', (
        TableVariant('table_1', '\\d{4}-\\d{4}', 'statistics', 'stock', 'as_of', ('source_hierarchy', 'layout_vintage', 'maturity_basis'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'External debt sectors, instruments, currencies and maturity labels; overlapping layout vintages remain independent until explicitly reconciled.'),
    ),
)
DEBT_CUR_MAT_NEW = SeriesSpec(
    id='cbr.external_debt.debt_cur-mat_new',
    publication=DEBT_CUR_MAT_NEW_PUBLICATION,
    semantics=Semantics('publisher_defined', ('publication', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            DEBT_CUR_MAT_NEW_PUBLICATION, Applicability(source_ids=frozenset({'cbr.external_debt.debt_cur-mat_new'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            DEBT_CUR_MAT_NEW_PUBLICATION, Applicability(source_ids=frozenset({'cbr.external_debt.debt_cur-mat_new'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            DEBT_CUR_MAT_NEW_PUBLICATION, Applicability(source_ids=frozenset({'cbr.external_debt.debt_cur-mat_new'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            DEBT_CUR_MAT_NEW_PUBLICATION, Applicability(source_ids=frozenset({'cbr.external_debt.debt_cur-mat_new'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.external_debt.debt_cur-mat_new', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.external_debt.debt_cur-mat_new'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.external_debt.debt_cur-mat_new', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.external_debt.debt_cur-mat_new'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.external_debt.debt_cur-mat_new'), Applicability(source_ids=frozenset({'cbr.external_debt.debt_cur-mat_new'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            DEBT_CUR_MAT_NEW_TABLE, Applicability(source_ids=frozenset({'cbr.external_debt.debt_cur-mat_new'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            DEBT_CUR_MAT_NEW_TABLE, Applicability(source_ids=frozenset({'cbr.external_debt.debt_cur-mat_new'})),
        ),
    }),
)

DEBT_MATURITY_PUBLICATION = Publication(
    'cbr.external_debt.debt_maturity', 'cbr.external_debt', 'External debt by maturity and instrument',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/credit_statistics/debt/debt_maturity.xlsx', None,
)
DEBT_MATURITY_TABLE = StatisticalSettings(
    'cbr.external_debt.debt_maturity', (
        TableVariant('table_1', '\\d{4}-\\d{4}', 'statistics', 'stock', 'as_of', ('source_hierarchy', 'layout_vintage', 'maturity_basis'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'External debt sectors, instruments, currencies and maturity labels; overlapping layout vintages remain independent until explicitly reconciled.'),
    ),
)
DEBT_MATURITY = SeriesSpec(
    id='cbr.external_debt.debt_maturity',
    publication=DEBT_MATURITY_PUBLICATION,
    semantics=Semantics('publisher_defined', ('publication', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            DEBT_MATURITY_PUBLICATION, Applicability(source_ids=frozenset({'cbr.external_debt.debt_maturity'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            DEBT_MATURITY_PUBLICATION, Applicability(source_ids=frozenset({'cbr.external_debt.debt_maturity'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            DEBT_MATURITY_PUBLICATION, Applicability(source_ids=frozenset({'cbr.external_debt.debt_maturity'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            DEBT_MATURITY_PUBLICATION, Applicability(source_ids=frozenset({'cbr.external_debt.debt_maturity'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.external_debt.debt_maturity', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.external_debt.debt_maturity'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.external_debt.debt_maturity', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.external_debt.debt_maturity'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.external_debt.debt_maturity'), Applicability(source_ids=frozenset({'cbr.external_debt.debt_maturity'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            DEBT_MATURITY_TABLE, Applicability(source_ids=frozenset({'cbr.external_debt.debt_maturity'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            DEBT_MATURITY_TABLE, Applicability(source_ids=frozenset({'cbr.external_debt.debt_maturity'})),
        ),
    }),
)

DEBT_NEW_PUBLICATION = Publication(
    'cbr.external_debt.debt_new', 'cbr.external_debt', 'External debt',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/credit_statistics/debt/debt_new.xlsx', None,
)
DEBT_NEW_TABLE = StatisticalSettings(
    'cbr.external_debt.debt_new', (
        TableVariant('table_1', '\\d{4}-\\d{4}', 'statistics', 'stock', 'as_of', ('source_hierarchy', 'layout_vintage', 'maturity_basis'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'External debt sectors, instruments, currencies and maturity labels; overlapping layout vintages remain independent until explicitly reconciled.'),
    ),
)
DEBT_NEW = SeriesSpec(
    id='cbr.external_debt.debt_new',
    publication=DEBT_NEW_PUBLICATION,
    semantics=Semantics('publisher_defined', ('publication', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            DEBT_NEW_PUBLICATION, Applicability(source_ids=frozenset({'cbr.external_debt.debt_new'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            DEBT_NEW_PUBLICATION, Applicability(source_ids=frozenset({'cbr.external_debt.debt_new'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            DEBT_NEW_PUBLICATION, Applicability(source_ids=frozenset({'cbr.external_debt.debt_new'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            DEBT_NEW_PUBLICATION, Applicability(source_ids=frozenset({'cbr.external_debt.debt_new'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.external_debt.debt_new', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.external_debt.debt_new'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.external_debt.debt_new', ('xlsx',)), Applicability(source_ids=frozenset({'cbr.external_debt.debt_new'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.external_debt.debt_new'), Applicability(source_ids=frozenset({'cbr.external_debt.debt_new'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            DEBT_NEW_TABLE, Applicability(source_ids=frozenset({'cbr.external_debt.debt_new'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            DEBT_NEW_TABLE, Applicability(source_ids=frozenset({'cbr.external_debt.debt_new'})),
        ),
    }),
)

