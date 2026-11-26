"""Explicit Bank of Russia reporting_forms source records and action settings."""
from types import MappingProxyType
from stratbox.capabilities.model.domains import SeriesSpec, CommandSpec, Applicability
from stratbox.capabilities.model.methods import MethodRef
from stratbox.domains.cbr.common.contracts import Publication, Semantics, StatisticalSettings, TableVariant, FormSettings, FamilySettings, SourceRequirement, MappingRules
from stratbox.domains.cbr.common.publications import SORS_INDEX, FORMS_INDEX, ESCROW_INDEX, OFFICES_PAGE, TERRITORIAL_INDEX

FAMILY_ID = 'cbr.reporting_forms'

F101_PUBLICATION = Publication(
    'cbr.reporting_forms.f101', FAMILY_ID, 'Credit institution reporting form 101',
    'dated', ('rar', 'zip', 'dbf'), 'index', FORMS_INDEX, '101-(?P<date>\\d{8})\\.(?:rar|zip)',
    archive_mode="dbf_collection",
)
F101_TABLE = FormSettings(F101_PUBLICATION.series_id, '101')
F101 = SeriesSpec(
    id=F101_PUBLICATION.series_id,
    publication=F101_PUBLICATION,
    semantics=Semantics('reporting_period', ('report_date', 'credit_institution', 'form', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            F101_PUBLICATION, Applicability(source_ids=frozenset({F101_PUBLICATION.series_id})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            F101_PUBLICATION, Applicability(source_ids=frozenset({F101_PUBLICATION.series_id})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            F101_PUBLICATION, Applicability(source_ids=frozenset({F101_PUBLICATION.series_id})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            F101_PUBLICATION, Applicability(source_ids=frozenset({F101_PUBLICATION.series_id})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement(F101_PUBLICATION.series_id, F101_PUBLICATION.formats, issue_required=F101_PUBLICATION.issue_model == 'dated'), Applicability(source_ids=frozenset({F101_PUBLICATION.series_id})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement(F101_PUBLICATION.series_id, F101_PUBLICATION.formats, issue_required=F101_PUBLICATION.issue_model == 'dated'), Applicability(source_ids=frozenset({F101_PUBLICATION.series_id})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules(F101_PUBLICATION.series_id), Applicability(source_ids=frozenset({F101_PUBLICATION.series_id})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.forms:extract"),
            F101_TABLE, Applicability(source_ids=frozenset({F101_PUBLICATION.series_id})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.forms:interpret"),
            F101_TABLE, Applicability(source_ids=frozenset({F101_PUBLICATION.series_id})),
        ),
    }),
)

F102_PUBLICATION = Publication(
    'cbr.reporting_forms.f102', FAMILY_ID, 'Credit institution reporting form 102',
    'dated', ('rar', 'zip', 'dbf'), 'index', FORMS_INDEX, '102-(?P<date>\\d{8})\\.(?:rar|zip)',
    archive_mode="dbf_collection",
)
F102_TABLE = FormSettings(F102_PUBLICATION.series_id, '102')
F102 = SeriesSpec(
    id=F102_PUBLICATION.series_id,
    publication=F102_PUBLICATION,
    semantics=Semantics('reporting_period', ('report_date', 'credit_institution', 'form', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            F102_PUBLICATION, Applicability(source_ids=frozenset({F102_PUBLICATION.series_id})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            F102_PUBLICATION, Applicability(source_ids=frozenset({F102_PUBLICATION.series_id})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            F102_PUBLICATION, Applicability(source_ids=frozenset({F102_PUBLICATION.series_id})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            F102_PUBLICATION, Applicability(source_ids=frozenset({F102_PUBLICATION.series_id})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement(F102_PUBLICATION.series_id, F102_PUBLICATION.formats, issue_required=F102_PUBLICATION.issue_model == 'dated'), Applicability(source_ids=frozenset({F102_PUBLICATION.series_id})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement(F102_PUBLICATION.series_id, F102_PUBLICATION.formats, issue_required=F102_PUBLICATION.issue_model == 'dated'), Applicability(source_ids=frozenset({F102_PUBLICATION.series_id})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules(F102_PUBLICATION.series_id), Applicability(source_ids=frozenset({F102_PUBLICATION.series_id})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.forms:extract"),
            F102_TABLE, Applicability(source_ids=frozenset({F102_PUBLICATION.series_id})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.forms:interpret"),
            F102_TABLE, Applicability(source_ids=frozenset({F102_PUBLICATION.series_id})),
        ),
    }),
)

F123_PUBLICATION = Publication(
    'cbr.reporting_forms.f123', FAMILY_ID, 'Credit institution reporting form 123',
    'dated', ('rar', 'zip', 'dbf'), 'index', FORMS_INDEX, '123-(?P<date>\\d{8})\\.(?:rar|zip)',
    archive_mode="dbf_collection",
)
F123_TABLE = FormSettings(F123_PUBLICATION.series_id, '123')
F123 = SeriesSpec(
    id=F123_PUBLICATION.series_id,
    publication=F123_PUBLICATION,
    semantics=Semantics('reporting_period', ('report_date', 'credit_institution', 'form', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            F123_PUBLICATION, Applicability(source_ids=frozenset({F123_PUBLICATION.series_id})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            F123_PUBLICATION, Applicability(source_ids=frozenset({F123_PUBLICATION.series_id})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            F123_PUBLICATION, Applicability(source_ids=frozenset({F123_PUBLICATION.series_id})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            F123_PUBLICATION, Applicability(source_ids=frozenset({F123_PUBLICATION.series_id})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement(F123_PUBLICATION.series_id, F123_PUBLICATION.formats, issue_required=F123_PUBLICATION.issue_model == 'dated'), Applicability(source_ids=frozenset({F123_PUBLICATION.series_id})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement(F123_PUBLICATION.series_id, F123_PUBLICATION.formats, issue_required=F123_PUBLICATION.issue_model == 'dated'), Applicability(source_ids=frozenset({F123_PUBLICATION.series_id})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules(F123_PUBLICATION.series_id), Applicability(source_ids=frozenset({F123_PUBLICATION.series_id})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.forms:extract"),
            F123_TABLE, Applicability(source_ids=frozenset({F123_PUBLICATION.series_id})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.forms:interpret"),
            F123_TABLE, Applicability(source_ids=frozenset({F123_PUBLICATION.series_id})),
        ),
    }),
)

F134_PUBLICATION = Publication(
    'cbr.reporting_forms.f134', FAMILY_ID, 'Credit institution reporting form 134',
    'dated', ('rar', 'zip', 'dbf'), 'index', FORMS_INDEX, '134-(?P<date>\\d{8})\\.(?:rar|zip)',
    archive_mode="dbf_collection",
)
F134_TABLE = FormSettings(F134_PUBLICATION.series_id, '134', ('C3',), ('C1',),
    required_fields=(('REGN', 'N', 4), ('C1', 'C', 15), ('C3', 'N', 16)), require_measurement=True)
F134 = SeriesSpec(
    id=F134_PUBLICATION.series_id,
    publication=F134_PUBLICATION,
    semantics=Semantics('reporting_period', ('report_date', 'credit_institution', 'form', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            F134_PUBLICATION, Applicability(source_ids=frozenset({F134_PUBLICATION.series_id})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            F134_PUBLICATION, Applicability(source_ids=frozenset({F134_PUBLICATION.series_id})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            F134_PUBLICATION, Applicability(source_ids=frozenset({F134_PUBLICATION.series_id})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            F134_PUBLICATION, Applicability(source_ids=frozenset({F134_PUBLICATION.series_id})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement(F134_PUBLICATION.series_id, F134_PUBLICATION.formats, issue_required=F134_PUBLICATION.issue_model == 'dated'), Applicability(source_ids=frozenset({F134_PUBLICATION.series_id})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement(F134_PUBLICATION.series_id, F134_PUBLICATION.formats, issue_required=F134_PUBLICATION.issue_model == 'dated'), Applicability(source_ids=frozenset({F134_PUBLICATION.series_id})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules(F134_PUBLICATION.series_id), Applicability(source_ids=frozenset({F134_PUBLICATION.series_id})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.forms:extract"),
            F134_TABLE, Applicability(source_ids=frozenset({F134_PUBLICATION.series_id})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.forms:interpret"),
            F134_TABLE, Applicability(source_ids=frozenset({F134_PUBLICATION.series_id})),
        ),
    }),
)

F135_PUBLICATION = Publication(
    'cbr.reporting_forms.f135', FAMILY_ID, 'Credit institution reporting form 135',
    'dated', ('rar', 'zip', 'dbf'), 'index', FORMS_INDEX, '135-(?P<date>\\d{8})\\.(?:rar|zip)',
    archive_mode="dbf_collection",
)
F135_TABLE = FormSettings(F135_PUBLICATION.series_id, '135')
F135 = SeriesSpec(
    id=F135_PUBLICATION.series_id,
    publication=F135_PUBLICATION,
    semantics=Semantics('reporting_period', ('report_date', 'credit_institution', 'form', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            F135_PUBLICATION, Applicability(source_ids=frozenset({F135_PUBLICATION.series_id})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            F135_PUBLICATION, Applicability(source_ids=frozenset({F135_PUBLICATION.series_id})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            F135_PUBLICATION, Applicability(source_ids=frozenset({F135_PUBLICATION.series_id})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            F135_PUBLICATION, Applicability(source_ids=frozenset({F135_PUBLICATION.series_id})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement(F135_PUBLICATION.series_id, F135_PUBLICATION.formats, issue_required=F135_PUBLICATION.issue_model == 'dated'), Applicability(source_ids=frozenset({F135_PUBLICATION.series_id})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement(F135_PUBLICATION.series_id, F135_PUBLICATION.formats, issue_required=F135_PUBLICATION.issue_model == 'dated'), Applicability(source_ids=frozenset({F135_PUBLICATION.series_id})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules(F135_PUBLICATION.series_id), Applicability(source_ids=frozenset({F135_PUBLICATION.series_id})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.forms:extract"),
            F135_TABLE, Applicability(source_ids=frozenset({F135_PUBLICATION.series_id})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.forms:interpret"),
            F135_TABLE, Applicability(source_ids=frozenset({F135_PUBLICATION.series_id})),
        ),
    }),
)

F802_PUBLICATION = Publication(
    'cbr.reporting_forms.f802', FAMILY_ID, 'Credit institution reporting form 802',
    'dated', ('rar', 'zip', 'dbf'), 'index', FORMS_INDEX, '802-(?P<date>\\d{8})\\.(?:rar|zip)',
    archive_mode="dbf_collection",
)
F802_TABLE = FormSettings(F802_PUBLICATION.series_id, '802')
F802 = SeriesSpec(
    id=F802_PUBLICATION.series_id,
    publication=F802_PUBLICATION,
    semantics=Semantics('reporting_period', ('report_date', 'credit_institution', 'form', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            F802_PUBLICATION, Applicability(source_ids=frozenset({F802_PUBLICATION.series_id})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            F802_PUBLICATION, Applicability(source_ids=frozenset({F802_PUBLICATION.series_id})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            F802_PUBLICATION, Applicability(source_ids=frozenset({F802_PUBLICATION.series_id})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            F802_PUBLICATION, Applicability(source_ids=frozenset({F802_PUBLICATION.series_id})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement(F802_PUBLICATION.series_id, F802_PUBLICATION.formats, issue_required=F802_PUBLICATION.issue_model == 'dated'), Applicability(source_ids=frozenset({F802_PUBLICATION.series_id})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement(F802_PUBLICATION.series_id, F802_PUBLICATION.formats, issue_required=F802_PUBLICATION.issue_model == 'dated'), Applicability(source_ids=frozenset({F802_PUBLICATION.series_id})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules(F802_PUBLICATION.series_id), Applicability(source_ids=frozenset({F802_PUBLICATION.series_id})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.forms:extract"),
            F802_TABLE, Applicability(source_ids=frozenset({F802_PUBLICATION.series_id})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.forms:interpret"),
            F802_TABLE, Applicability(source_ids=frozenset({F802_PUBLICATION.series_id})),
        ),
    }),
)

F803_PUBLICATION = Publication(
    'cbr.reporting_forms.f803', FAMILY_ID, 'Credit institution reporting form 803',
    'dated', ('rar', 'zip', 'dbf'), 'index', FORMS_INDEX, '803-(?P<date>\\d{8})\\.(?:rar|zip)',
    archive_mode="dbf_collection",
)
F803_TABLE = FormSettings(F803_PUBLICATION.series_id, '803', ('KORR_P', 'KORR_M', 'VSEGO'), ('RAZDEL', 'STR'), 'REGN_GKO', 'flow',
    required_fields=(('REGN_GKO', 'N', 4), ('RAZDEL', 'C', 3), ('STR', 'C', 5),
        ('KORR_P', 'N', 16), ('KORR_M', 'N', 16), ('VSEGO', 'N', 16)), require_measurement=True)
F803 = SeriesSpec(
    id=F803_PUBLICATION.series_id,
    publication=F803_PUBLICATION,
    semantics=Semantics('reporting_period', ('report_date', 'credit_institution', 'form', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            F803_PUBLICATION, Applicability(source_ids=frozenset({F803_PUBLICATION.series_id})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            F803_PUBLICATION, Applicability(source_ids=frozenset({F803_PUBLICATION.series_id})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            F803_PUBLICATION, Applicability(source_ids=frozenset({F803_PUBLICATION.series_id})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            F803_PUBLICATION, Applicability(source_ids=frozenset({F803_PUBLICATION.series_id})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement(F803_PUBLICATION.series_id, F803_PUBLICATION.formats, issue_required=F803_PUBLICATION.issue_model == 'dated'), Applicability(source_ids=frozenset({F803_PUBLICATION.series_id})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement(F803_PUBLICATION.series_id, F803_PUBLICATION.formats, issue_required=F803_PUBLICATION.issue_model == 'dated'), Applicability(source_ids=frozenset({F803_PUBLICATION.series_id})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules(F803_PUBLICATION.series_id), Applicability(source_ids=frozenset({F803_PUBLICATION.series_id})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.forms:extract"),
            F803_TABLE, Applicability(source_ids=frozenset({F803_PUBLICATION.series_id})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.forms:interpret"),
            F803_TABLE, Applicability(source_ids=frozenset({F803_PUBLICATION.series_id})),
        ),
    }),
)

F805_PUBLICATION = Publication(
    'cbr.reporting_forms.f805', FAMILY_ID, 'Credit institution reporting form 805',
    'dated', ('rar', 'zip', 'dbf'), 'index', FORMS_INDEX, '805-(?P<date>\\d{8})\\.(?:rar|zip)',
    archive_mode="dbf_collection",
)
F805_TABLE = FormSettings(F805_PUBLICATION.series_id, '805')
F805 = SeriesSpec(
    id=F805_PUBLICATION.series_id,
    publication=F805_PUBLICATION,
    semantics=Semantics('reporting_period', ('report_date', 'credit_institution', 'form', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            F805_PUBLICATION, Applicability(source_ids=frozenset({F805_PUBLICATION.series_id})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            F805_PUBLICATION, Applicability(source_ids=frozenset({F805_PUBLICATION.series_id})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            F805_PUBLICATION, Applicability(source_ids=frozenset({F805_PUBLICATION.series_id})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            F805_PUBLICATION, Applicability(source_ids=frozenset({F805_PUBLICATION.series_id})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement(F805_PUBLICATION.series_id, F805_PUBLICATION.formats, issue_required=F805_PUBLICATION.issue_model == 'dated'), Applicability(source_ids=frozenset({F805_PUBLICATION.series_id})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement(F805_PUBLICATION.series_id, F805_PUBLICATION.formats, issue_required=F805_PUBLICATION.issue_model == 'dated'), Applicability(source_ids=frozenset({F805_PUBLICATION.series_id})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules(F805_PUBLICATION.series_id), Applicability(source_ids=frozenset({F805_PUBLICATION.series_id})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.forms:extract"),
            F805_TABLE, Applicability(source_ids=frozenset({F805_PUBLICATION.series_id})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.forms:interpret"),
            F805_TABLE, Applicability(source_ids=frozenset({F805_PUBLICATION.series_id})),
        ),
    }),
)

