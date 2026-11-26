"""Explicit Bank of Russia external_debt source records and action settings."""
from types import MappingProxyType
from stratbox.capabilities.model.domains import SeriesSpec, CommandSpec, Applicability
from stratbox.capabilities.model.methods import MethodRef
from stratbox.domains.cbr.common.contracts import Publication, Semantics, StatisticalSettings, TableVariant, FormSettings, FamilySettings, SourceRequirement, MappingRules
from stratbox.domains.cbr.common.publications import SORS_INDEX, FORMS_INDEX, ESCROW_INDEX, OFFICES_PAGE, TERRITORIAL_INDEX

FAMILY_ID = 'cbr.external_debt'

DEBT_CUR_MAT_NEW_PUBLICATION = Publication(
    'cbr.external_debt.debt_cur-mat_new', FAMILY_ID, 'External debt by currency and maturity',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/credit_statistics/debt/debt_cur-mat_new.xlsx', None,
)
DEBT_CUR_MAT_NEW_TABLE = StatisticalSettings(
    DEBT_CUR_MAT_NEW_PUBLICATION.series_id, (
        TableVariant('table_1', '\\d{4}-\\d{4}', 'statistics', 'stock', 'as_of', ('source_hierarchy', 'layout_vintage', 'maturity_basis'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'External debt sectors, instruments, currencies and maturity labels; overlapping layout vintages remain independent until explicitly reconciled.'),
    ),
)
DEBT_CUR_MAT_NEW = SeriesSpec(
    id=DEBT_CUR_MAT_NEW_PUBLICATION.series_id,
    publication=DEBT_CUR_MAT_NEW_PUBLICATION,
    semantics=Semantics('publisher_defined', ('publication', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            DEBT_CUR_MAT_NEW_PUBLICATION, Applicability(source_ids=frozenset({DEBT_CUR_MAT_NEW_PUBLICATION.series_id})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            DEBT_CUR_MAT_NEW_PUBLICATION, Applicability(source_ids=frozenset({DEBT_CUR_MAT_NEW_PUBLICATION.series_id})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            DEBT_CUR_MAT_NEW_PUBLICATION, Applicability(source_ids=frozenset({DEBT_CUR_MAT_NEW_PUBLICATION.series_id})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            DEBT_CUR_MAT_NEW_PUBLICATION, Applicability(source_ids=frozenset({DEBT_CUR_MAT_NEW_PUBLICATION.series_id})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement(DEBT_CUR_MAT_NEW_PUBLICATION.series_id, DEBT_CUR_MAT_NEW_PUBLICATION.formats, issue_required=DEBT_CUR_MAT_NEW_PUBLICATION.issue_model == 'dated', locator=DEBT_CUR_MAT_NEW_PUBLICATION.locator, filename_pattern=DEBT_CUR_MAT_NEW_PUBLICATION.filename_pattern, publication_kind=DEBT_CUR_MAT_NEW_PUBLICATION.kind), Applicability(source_ids=frozenset({DEBT_CUR_MAT_NEW_PUBLICATION.series_id})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement(DEBT_CUR_MAT_NEW_PUBLICATION.series_id, DEBT_CUR_MAT_NEW_PUBLICATION.formats, issue_required=DEBT_CUR_MAT_NEW_PUBLICATION.issue_model == 'dated', locator=DEBT_CUR_MAT_NEW_PUBLICATION.locator, filename_pattern=DEBT_CUR_MAT_NEW_PUBLICATION.filename_pattern, publication_kind=DEBT_CUR_MAT_NEW_PUBLICATION.kind), Applicability(source_ids=frozenset({DEBT_CUR_MAT_NEW_PUBLICATION.series_id})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules(DEBT_CUR_MAT_NEW_PUBLICATION.series_id), Applicability(source_ids=frozenset({DEBT_CUR_MAT_NEW_PUBLICATION.series_id})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            DEBT_CUR_MAT_NEW_TABLE, Applicability(source_ids=frozenset({DEBT_CUR_MAT_NEW_PUBLICATION.series_id})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            DEBT_CUR_MAT_NEW_TABLE, Applicability(source_ids=frozenset({DEBT_CUR_MAT_NEW_PUBLICATION.series_id})),
        ),
    }),
)

DEBT_MATURITY_PUBLICATION = Publication(
    'cbr.external_debt.debt_maturity', FAMILY_ID, 'External debt by maturity and instrument',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/credit_statistics/debt/debt_maturity.xlsx', None,
)
DEBT_MATURITY_TABLE = StatisticalSettings(
    DEBT_MATURITY_PUBLICATION.series_id, (
        TableVariant('table_1', '\\d{4}-\\d{4}', 'statistics', 'stock', 'as_of', ('source_hierarchy', 'layout_vintage', 'maturity_basis'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'External debt sectors, instruments, currencies and maturity labels; overlapping layout vintages remain independent until explicitly reconciled.'),
    ),
)
DEBT_MATURITY = SeriesSpec(
    id=DEBT_MATURITY_PUBLICATION.series_id,
    publication=DEBT_MATURITY_PUBLICATION,
    semantics=Semantics('publisher_defined', ('publication', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            DEBT_MATURITY_PUBLICATION, Applicability(source_ids=frozenset({DEBT_MATURITY_PUBLICATION.series_id})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            DEBT_MATURITY_PUBLICATION, Applicability(source_ids=frozenset({DEBT_MATURITY_PUBLICATION.series_id})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            DEBT_MATURITY_PUBLICATION, Applicability(source_ids=frozenset({DEBT_MATURITY_PUBLICATION.series_id})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            DEBT_MATURITY_PUBLICATION, Applicability(source_ids=frozenset({DEBT_MATURITY_PUBLICATION.series_id})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement(DEBT_MATURITY_PUBLICATION.series_id, DEBT_MATURITY_PUBLICATION.formats, issue_required=DEBT_MATURITY_PUBLICATION.issue_model == 'dated', locator=DEBT_MATURITY_PUBLICATION.locator, filename_pattern=DEBT_MATURITY_PUBLICATION.filename_pattern, publication_kind=DEBT_MATURITY_PUBLICATION.kind), Applicability(source_ids=frozenset({DEBT_MATURITY_PUBLICATION.series_id})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement(DEBT_MATURITY_PUBLICATION.series_id, DEBT_MATURITY_PUBLICATION.formats, issue_required=DEBT_MATURITY_PUBLICATION.issue_model == 'dated', locator=DEBT_MATURITY_PUBLICATION.locator, filename_pattern=DEBT_MATURITY_PUBLICATION.filename_pattern, publication_kind=DEBT_MATURITY_PUBLICATION.kind), Applicability(source_ids=frozenset({DEBT_MATURITY_PUBLICATION.series_id})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules(DEBT_MATURITY_PUBLICATION.series_id), Applicability(source_ids=frozenset({DEBT_MATURITY_PUBLICATION.series_id})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            DEBT_MATURITY_TABLE, Applicability(source_ids=frozenset({DEBT_MATURITY_PUBLICATION.series_id})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            DEBT_MATURITY_TABLE, Applicability(source_ids=frozenset({DEBT_MATURITY_PUBLICATION.series_id})),
        ),
    }),
)

DEBT_NEW_PUBLICATION = Publication(
    'cbr.external_debt.debt_new', FAMILY_ID, 'External debt',
    'rolling', ('xlsx',), 'fixed', 'https://www.cbr.ru/vfs/statistics/credit_statistics/debt/debt_new.xlsx', None,
)
DEBT_NEW_TABLE = StatisticalSettings(
    DEBT_NEW_PUBLICATION.series_id, (
        TableVariant('table_1', '\\d{4}-\\d{4}', 'statistics', 'stock', 'as_of', ('source_hierarchy', 'layout_vintage', 'maturity_basis'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'External debt sectors, instruments, currencies and maturity labels; overlapping layout vintages remain independent until explicitly reconciled.'),
    ),
)
DEBT_NEW = SeriesSpec(
    id=DEBT_NEW_PUBLICATION.series_id,
    publication=DEBT_NEW_PUBLICATION,
    semantics=Semantics('publisher_defined', ('publication', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            DEBT_NEW_PUBLICATION, Applicability(source_ids=frozenset({DEBT_NEW_PUBLICATION.series_id})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            DEBT_NEW_PUBLICATION, Applicability(source_ids=frozenset({DEBT_NEW_PUBLICATION.series_id})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            DEBT_NEW_PUBLICATION, Applicability(source_ids=frozenset({DEBT_NEW_PUBLICATION.series_id})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            DEBT_NEW_PUBLICATION, Applicability(source_ids=frozenset({DEBT_NEW_PUBLICATION.series_id})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement(DEBT_NEW_PUBLICATION.series_id, DEBT_NEW_PUBLICATION.formats, issue_required=DEBT_NEW_PUBLICATION.issue_model == 'dated', locator=DEBT_NEW_PUBLICATION.locator, filename_pattern=DEBT_NEW_PUBLICATION.filename_pattern, publication_kind=DEBT_NEW_PUBLICATION.kind), Applicability(source_ids=frozenset({DEBT_NEW_PUBLICATION.series_id})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement(DEBT_NEW_PUBLICATION.series_id, DEBT_NEW_PUBLICATION.formats, issue_required=DEBT_NEW_PUBLICATION.issue_model == 'dated', locator=DEBT_NEW_PUBLICATION.locator, filename_pattern=DEBT_NEW_PUBLICATION.filename_pattern, publication_kind=DEBT_NEW_PUBLICATION.kind), Applicability(source_ids=frozenset({DEBT_NEW_PUBLICATION.series_id})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules(DEBT_NEW_PUBLICATION.series_id), Applicability(source_ids=frozenset({DEBT_NEW_PUBLICATION.series_id})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            DEBT_NEW_TABLE, Applicability(source_ids=frozenset({DEBT_NEW_PUBLICATION.series_id})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            DEBT_NEW_TABLE, Applicability(source_ids=frozenset({DEBT_NEW_PUBLICATION.series_id})),
        ),
    }),
)

