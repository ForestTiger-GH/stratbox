"""Explicit Bank of Russia project_finance source records and action settings."""
from types import MappingProxyType
from stratbox.capabilities.model.domains import SeriesSpec, CommandSpec, Applicability
from stratbox.capabilities.model.methods import MethodRef
from stratbox.domains.cbr.common.contracts import Publication, Semantics, StatisticalSettings, TableVariant, FormSettings, FamilySettings, SourceRequirement, MappingRules
from stratbox.domains.cbr.common.publications import SORS_INDEX, FORMS_INDEX, ESCROW_INDEX, OFFICES_PAGE, TERRITORIAL_INDEX

FAMILY_ID = 'cbr.project_finance'

ESCROW_PUBLICATION = Publication(
    'cbr.project_finance.escrow', FAMILY_ID, 'Housing project finance and escrow',
    'dated', ('xlsx', 'html'), 'escrow_index', ESCROW_INDEX, None,
)
ESCROW_TABLE = FamilySettings(ESCROW_PUBLICATION.series_id, 'escrow')
ESCROW = SeriesSpec(
    id=ESCROW_PUBLICATION.series_id,
    publication=ESCROW_PUBLICATION,
    semantics=Semantics('stock_or_metric_specific_flow', ('report_date', 'territory', 'indicator'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            ESCROW_PUBLICATION, Applicability(source_ids=frozenset({ESCROW_PUBLICATION.series_id})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            ESCROW_PUBLICATION, Applicability(source_ids=frozenset({ESCROW_PUBLICATION.series_id})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            ESCROW_PUBLICATION, Applicability(source_ids=frozenset({ESCROW_PUBLICATION.series_id})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            ESCROW_PUBLICATION, Applicability(source_ids=frozenset({ESCROW_PUBLICATION.series_id})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement(ESCROW_PUBLICATION.series_id, ESCROW_PUBLICATION.formats, issue_required=ESCROW_PUBLICATION.issue_model == 'dated', locator=ESCROW_PUBLICATION.locator, filename_pattern=ESCROW_PUBLICATION.filename_pattern, publication_kind=ESCROW_PUBLICATION.kind), Applicability(source_ids=frozenset({ESCROW_PUBLICATION.series_id})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement(ESCROW_PUBLICATION.series_id, ESCROW_PUBLICATION.formats, issue_required=ESCROW_PUBLICATION.issue_model == 'dated', locator=ESCROW_PUBLICATION.locator, filename_pattern=ESCROW_PUBLICATION.filename_pattern, publication_kind=ESCROW_PUBLICATION.kind), Applicability(source_ids=frozenset({ESCROW_PUBLICATION.series_id})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules(ESCROW_PUBLICATION.series_id), Applicability(source_ids=frozenset({ESCROW_PUBLICATION.series_id})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.escrow:extract"),
            ESCROW_TABLE, Applicability(source_ids=frozenset({ESCROW_PUBLICATION.series_id})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.escrow:interpret"),
            ESCROW_TABLE, Applicability(source_ids=frozenset({ESCROW_PUBLICATION.series_id})),
        ),
    }),
)

