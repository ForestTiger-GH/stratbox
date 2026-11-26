"""Explicit Bank of Russia service_network source records and action settings."""
from types import MappingProxyType
from stratbox.capabilities.model.domains import SeriesSpec, CommandSpec, Applicability
from stratbox.capabilities.model.methods import MethodRef
from stratbox.domains.cbr.common.contracts import Publication, Semantics, StatisticalSettings, TableVariant, FormSettings, FamilySettings, SourceRequirement, MappingRules
from stratbox.domains.cbr.common.publications import SORS_INDEX, FORMS_INDEX, ESCROW_INDEX, OFFICES_PAGE, TERRITORIAL_INDEX

BANK_OFFICES_PUBLICATION = Publication(
    'cbr.service_network.bank_offices', 'cbr.service_network', 'Credit institution offices by bank and territory',
    'capture', ('html',), 'page', OFFICES_PAGE, None,
)
BANK_OFFICES_TABLE = FamilySettings('cbr.service_network.bank_offices', 'bank_offices')
BANK_OFFICES = SeriesSpec(
    id='cbr.service_network.bank_offices',
    publication=BANK_OFFICES_PUBLICATION,
    semantics=Semantics('qualified_official_date_or_capture', ('capture_date', 'territory', 'office_type'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.document.decode": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.network:decode_document"),
            BANK_OFFICES_TABLE, Applicability(source_ids=frozenset({'cbr.service_network.bank_offices'})),
        ),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            BANK_OFFICES_PUBLICATION, Applicability(source_ids=frozenset({'cbr.service_network.bank_offices'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            BANK_OFFICES_PUBLICATION, Applicability(source_ids=frozenset({'cbr.service_network.bank_offices'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            BANK_OFFICES_PUBLICATION, Applicability(source_ids=frozenset({'cbr.service_network.bank_offices'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            BANK_OFFICES_PUBLICATION, Applicability(source_ids=frozenset({'cbr.service_network.bank_offices'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.service_network.bank_offices', ('html',)), Applicability(source_ids=frozenset({'cbr.service_network.bank_offices'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.service_network.bank_offices', ('html',)), Applicability(source_ids=frozenset({'cbr.service_network.bank_offices'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.service_network.bank_offices'), Applicability(source_ids=frozenset({'cbr.service_network.bank_offices'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.network:extract"),
            BANK_OFFICES_TABLE, Applicability(source_ids=frozenset({'cbr.service_network.bank_offices'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.network:interpret"),
            BANK_OFFICES_TABLE, Applicability(source_ids=frozenset({'cbr.service_network.bank_offices'})),
        ),
    }),
)

TERRITORIAL_OFFICES_PUBLICATION = Publication(
    'cbr.service_network.territorial_offices', 'cbr.service_network', 'Credit institution offices by territory',
    'dated', ('xlsx',), 'territorial_index', TERRITORIAL_INDEX, None,
)
TERRITORIAL_OFFICES_TABLE = FamilySettings('cbr.service_network.territorial_offices', 'territorial_offices')
TERRITORIAL_OFFICES = SeriesSpec(
    id='cbr.service_network.territorial_offices',
    publication=TERRITORIAL_OFFICES_PUBLICATION,
    semantics=Semantics('qualified_official_date_or_capture', ('capture_date', 'territory', 'office_type'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            TERRITORIAL_OFFICES_PUBLICATION, Applicability(source_ids=frozenset({'cbr.service_network.territorial_offices'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            TERRITORIAL_OFFICES_PUBLICATION, Applicability(source_ids=frozenset({'cbr.service_network.territorial_offices'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            TERRITORIAL_OFFICES_PUBLICATION, Applicability(source_ids=frozenset({'cbr.service_network.territorial_offices'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            TERRITORIAL_OFFICES_PUBLICATION, Applicability(source_ids=frozenset({'cbr.service_network.territorial_offices'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.service_network.territorial_offices', ('xlsx',), issue_required=True), Applicability(source_ids=frozenset({'cbr.service_network.territorial_offices'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.service_network.territorial_offices', ('xlsx',), issue_required=True), Applicability(source_ids=frozenset({'cbr.service_network.territorial_offices'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.service_network.territorial_offices'), Applicability(source_ids=frozenset({'cbr.service_network.territorial_offices'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.network:extract"),
            TERRITORIAL_OFFICES_TABLE, Applicability(source_ids=frozenset({'cbr.service_network.territorial_offices'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.network:interpret"),
            TERRITORIAL_OFFICES_TABLE, Applicability(source_ids=frozenset({'cbr.service_network.territorial_offices'})),
        ),
    }),
)

