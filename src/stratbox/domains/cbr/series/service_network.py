"""Explicit Bank of Russia service_network source records and action settings."""
from types import MappingProxyType
from stratbox.capabilities.model.domains import SeriesSpec, CommandSpec, Applicability
from stratbox.capabilities.model.methods import MethodRef
from stratbox.domains.cbr.common.contracts import Publication, Semantics, StatisticalSettings, TableVariant, FormSettings, FamilySettings, SourceRequirement, MappingRules
from stratbox.domains.cbr.common.publications import SORS_INDEX, FORMS_INDEX, ESCROW_INDEX, OFFICES_PAGE, TERRITORIAL_INDEX

FAMILY_ID = 'cbr.service_network'

BANK_OFFICES_PUBLICATION = Publication(
    'cbr.service_network.bank_offices', FAMILY_ID, 'Credit institution offices by bank and territory',
    'capture', ('html',), 'page', OFFICES_PAGE, None,
)
BANK_OFFICES_TABLE = FamilySettings(BANK_OFFICES_PUBLICATION.series_id, 'bank_offices')
BANK_OFFICES = SeriesSpec(
    id=BANK_OFFICES_PUBLICATION.series_id,
    publication=BANK_OFFICES_PUBLICATION,
    semantics=Semantics('qualified_official_date_or_capture', ('capture_date', 'territory', 'office_type'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.document.decode": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.network:decode_document"),
            BANK_OFFICES_TABLE, Applicability(source_ids=frozenset({BANK_OFFICES_PUBLICATION.series_id})),
        ),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            BANK_OFFICES_PUBLICATION, Applicability(source_ids=frozenset({BANK_OFFICES_PUBLICATION.series_id})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            BANK_OFFICES_PUBLICATION, Applicability(source_ids=frozenset({BANK_OFFICES_PUBLICATION.series_id})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            BANK_OFFICES_PUBLICATION, Applicability(source_ids=frozenset({BANK_OFFICES_PUBLICATION.series_id})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            BANK_OFFICES_PUBLICATION, Applicability(source_ids=frozenset({BANK_OFFICES_PUBLICATION.series_id})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement(BANK_OFFICES_PUBLICATION.series_id, BANK_OFFICES_PUBLICATION.formats, issue_required=BANK_OFFICES_PUBLICATION.issue_model == 'dated', locator=BANK_OFFICES_PUBLICATION.locator, filename_pattern=BANK_OFFICES_PUBLICATION.filename_pattern, publication_kind=BANK_OFFICES_PUBLICATION.kind), Applicability(source_ids=frozenset({BANK_OFFICES_PUBLICATION.series_id})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement(BANK_OFFICES_PUBLICATION.series_id, BANK_OFFICES_PUBLICATION.formats, issue_required=BANK_OFFICES_PUBLICATION.issue_model == 'dated', locator=BANK_OFFICES_PUBLICATION.locator, filename_pattern=BANK_OFFICES_PUBLICATION.filename_pattern, publication_kind=BANK_OFFICES_PUBLICATION.kind), Applicability(source_ids=frozenset({BANK_OFFICES_PUBLICATION.series_id})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules(BANK_OFFICES_PUBLICATION.series_id), Applicability(source_ids=frozenset({BANK_OFFICES_PUBLICATION.series_id})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.network:extract"),
            BANK_OFFICES_TABLE, Applicability(source_ids=frozenset({BANK_OFFICES_PUBLICATION.series_id})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.network:interpret"),
            BANK_OFFICES_TABLE, Applicability(source_ids=frozenset({BANK_OFFICES_PUBLICATION.series_id})),
        ),
    }),
)

TERRITORIAL_OFFICES_PUBLICATION = Publication(
    'cbr.service_network.territorial_offices', FAMILY_ID, 'Credit institution offices by territory',
    'dated', ('xlsx',), 'territorial_index', TERRITORIAL_INDEX, None,
)
TERRITORIAL_OFFICES_TABLE = FamilySettings(TERRITORIAL_OFFICES_PUBLICATION.series_id, 'territorial_offices')
TERRITORIAL_OFFICES = SeriesSpec(
    id=TERRITORIAL_OFFICES_PUBLICATION.series_id,
    publication=TERRITORIAL_OFFICES_PUBLICATION,
    semantics=Semantics('qualified_official_date_or_capture', ('capture_date', 'territory', 'office_type'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            TERRITORIAL_OFFICES_PUBLICATION, Applicability(source_ids=frozenset({TERRITORIAL_OFFICES_PUBLICATION.series_id})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            TERRITORIAL_OFFICES_PUBLICATION, Applicability(source_ids=frozenset({TERRITORIAL_OFFICES_PUBLICATION.series_id})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            TERRITORIAL_OFFICES_PUBLICATION, Applicability(source_ids=frozenset({TERRITORIAL_OFFICES_PUBLICATION.series_id})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            TERRITORIAL_OFFICES_PUBLICATION, Applicability(source_ids=frozenset({TERRITORIAL_OFFICES_PUBLICATION.series_id})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement(TERRITORIAL_OFFICES_PUBLICATION.series_id, TERRITORIAL_OFFICES_PUBLICATION.formats, issue_required=TERRITORIAL_OFFICES_PUBLICATION.issue_model == 'dated', locator=TERRITORIAL_OFFICES_PUBLICATION.locator, filename_pattern=TERRITORIAL_OFFICES_PUBLICATION.filename_pattern, publication_kind=TERRITORIAL_OFFICES_PUBLICATION.kind), Applicability(source_ids=frozenset({TERRITORIAL_OFFICES_PUBLICATION.series_id})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement(TERRITORIAL_OFFICES_PUBLICATION.series_id, TERRITORIAL_OFFICES_PUBLICATION.formats, issue_required=TERRITORIAL_OFFICES_PUBLICATION.issue_model == 'dated', locator=TERRITORIAL_OFFICES_PUBLICATION.locator, filename_pattern=TERRITORIAL_OFFICES_PUBLICATION.filename_pattern, publication_kind=TERRITORIAL_OFFICES_PUBLICATION.kind), Applicability(source_ids=frozenset({TERRITORIAL_OFFICES_PUBLICATION.series_id})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules(TERRITORIAL_OFFICES_PUBLICATION.series_id), Applicability(source_ids=frozenset({TERRITORIAL_OFFICES_PUBLICATION.series_id})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.network:extract"),
            TERRITORIAL_OFFICES_TABLE, Applicability(source_ids=frozenset({TERRITORIAL_OFFICES_PUBLICATION.series_id})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.network:interpret"),
            TERRITORIAL_OFFICES_TABLE, Applicability(source_ids=frozenset({TERRITORIAL_OFFICES_PUBLICATION.series_id})),
        ),
    }),
)

