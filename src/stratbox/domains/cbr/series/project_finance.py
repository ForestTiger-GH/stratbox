"""Explicit Bank of Russia project_finance source records and action settings."""
from types import MappingProxyType
from stratbox.capabilities.model.domains import SeriesSpec, CommandSpec, Applicability
from stratbox.capabilities.model.methods import MethodRef
from stratbox.domains.cbr.common.contracts import Publication, Semantics, StatisticalSettings, TableVariant, FormSettings, FamilySettings, SourceRequirement, MappingRules
from stratbox.domains.cbr.common.publications import SORS_INDEX, FORMS_INDEX, ESCROW_INDEX, OFFICES_PAGE, TERRITORIAL_INDEX

ESCROW_PUBLICATION = Publication(
    'cbr.project_finance.escrow', 'cbr.project_finance', 'Housing project finance and escrow',
    'dated', ('xlsx', 'html'), 'escrow_index', ESCROW_INDEX, None,
)
ESCROW_TABLE = FamilySettings('cbr.project_finance.escrow', 'escrow')
ESCROW = SeriesSpec(
    id='cbr.project_finance.escrow',
    publication=ESCROW_PUBLICATION,
    semantics=Semantics('stock_or_metric_specific_flow', ('report_date', 'territory', 'indicator'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            ESCROW_PUBLICATION, Applicability(source_ids=frozenset({'cbr.project_finance.escrow'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            ESCROW_PUBLICATION, Applicability(source_ids=frozenset({'cbr.project_finance.escrow'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            ESCROW_PUBLICATION, Applicability(source_ids=frozenset({'cbr.project_finance.escrow'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            ESCROW_PUBLICATION, Applicability(source_ids=frozenset({'cbr.project_finance.escrow'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.project_finance.escrow', ('xlsx', 'html'), issue_required=True), Applicability(source_ids=frozenset({'cbr.project_finance.escrow'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.project_finance.escrow', ('xlsx', 'html'), issue_required=True), Applicability(source_ids=frozenset({'cbr.project_finance.escrow'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.project_finance.escrow'), Applicability(source_ids=frozenset({'cbr.project_finance.escrow'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.escrow:extract"),
            ESCROW_TABLE, Applicability(source_ids=frozenset({'cbr.project_finance.escrow'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.escrow:interpret"),
            ESCROW_TABLE, Applicability(source_ids=frozenset({'cbr.project_finance.escrow'})),
        ),
    }),
)

