"""Explicit Bank of Russia reporting_forms source records and action settings."""
from types import MappingProxyType
from stratbox.capabilities.model.domains import SeriesSpec, CommandSpec, Applicability
from stratbox.capabilities.model.methods import MethodRef
from stratbox.domains.cbr.common.contracts import Publication, Semantics, StatisticalSettings, TableVariant, FormSettings, FamilySettings, SourceRequirement, MappingRules
from stratbox.domains.cbr.common.publications import SORS_INDEX, FORMS_INDEX, ESCROW_INDEX, OFFICES_PAGE, TERRITORIAL_INDEX

F101_PUBLICATION = Publication(
    'cbr.reporting_forms.f101', 'cbr.reporting_forms', 'Credit institution reporting form 101',
    'dated', ('rar', 'zip', 'dbf'), 'index', FORMS_INDEX, '101-(?P<date>\\d{8})\\.(?:rar|zip)',
)
F101_TABLE = FormSettings('cbr.reporting_forms.f101', '101')
F101 = SeriesSpec(
    id='cbr.reporting_forms.f101',
    publication=F101_PUBLICATION,
    semantics=Semantics('reporting_period', ('report_date', 'credit_institution', 'form', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            F101_PUBLICATION, Applicability(source_ids=frozenset({'cbr.reporting_forms.f101'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            F101_PUBLICATION, Applicability(source_ids=frozenset({'cbr.reporting_forms.f101'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            F101_PUBLICATION, Applicability(source_ids=frozenset({'cbr.reporting_forms.f101'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            F101_PUBLICATION, Applicability(source_ids=frozenset({'cbr.reporting_forms.f101'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.reporting_forms.f101', ('rar', 'zip', 'dbf'), issue_required=True), Applicability(source_ids=frozenset({'cbr.reporting_forms.f101'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.reporting_forms.f101', ('rar', 'zip', 'dbf'), issue_required=True), Applicability(source_ids=frozenset({'cbr.reporting_forms.f101'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.reporting_forms.f101'), Applicability(source_ids=frozenset({'cbr.reporting_forms.f101'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.forms:extract"),
            F101_TABLE, Applicability(source_ids=frozenset({'cbr.reporting_forms.f101'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.forms:interpret"),
            F101_TABLE, Applicability(source_ids=frozenset({'cbr.reporting_forms.f101'})),
        ),
    }),
)

F102_PUBLICATION = Publication(
    'cbr.reporting_forms.f102', 'cbr.reporting_forms', 'Credit institution reporting form 102',
    'dated', ('rar', 'zip', 'dbf'), 'index', FORMS_INDEX, '102-(?P<date>\\d{8})\\.(?:rar|zip)',
)
F102_TABLE = FormSettings('cbr.reporting_forms.f102', '102')
F102 = SeriesSpec(
    id='cbr.reporting_forms.f102',
    publication=F102_PUBLICATION,
    semantics=Semantics('reporting_period', ('report_date', 'credit_institution', 'form', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            F102_PUBLICATION, Applicability(source_ids=frozenset({'cbr.reporting_forms.f102'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            F102_PUBLICATION, Applicability(source_ids=frozenset({'cbr.reporting_forms.f102'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            F102_PUBLICATION, Applicability(source_ids=frozenset({'cbr.reporting_forms.f102'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            F102_PUBLICATION, Applicability(source_ids=frozenset({'cbr.reporting_forms.f102'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.reporting_forms.f102', ('rar', 'zip', 'dbf'), issue_required=True), Applicability(source_ids=frozenset({'cbr.reporting_forms.f102'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.reporting_forms.f102', ('rar', 'zip', 'dbf'), issue_required=True), Applicability(source_ids=frozenset({'cbr.reporting_forms.f102'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.reporting_forms.f102'), Applicability(source_ids=frozenset({'cbr.reporting_forms.f102'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.forms:extract"),
            F102_TABLE, Applicability(source_ids=frozenset({'cbr.reporting_forms.f102'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.forms:interpret"),
            F102_TABLE, Applicability(source_ids=frozenset({'cbr.reporting_forms.f102'})),
        ),
    }),
)

F123_PUBLICATION = Publication(
    'cbr.reporting_forms.f123', 'cbr.reporting_forms', 'Credit institution reporting form 123',
    'dated', ('rar', 'zip', 'dbf'), 'index', FORMS_INDEX, '123-(?P<date>\\d{8})\\.(?:rar|zip)',
)
F123_TABLE = FormSettings('cbr.reporting_forms.f123', '123')
F123 = SeriesSpec(
    id='cbr.reporting_forms.f123',
    publication=F123_PUBLICATION,
    semantics=Semantics('reporting_period', ('report_date', 'credit_institution', 'form', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            F123_PUBLICATION, Applicability(source_ids=frozenset({'cbr.reporting_forms.f123'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            F123_PUBLICATION, Applicability(source_ids=frozenset({'cbr.reporting_forms.f123'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            F123_PUBLICATION, Applicability(source_ids=frozenset({'cbr.reporting_forms.f123'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            F123_PUBLICATION, Applicability(source_ids=frozenset({'cbr.reporting_forms.f123'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.reporting_forms.f123', ('rar', 'zip', 'dbf'), issue_required=True), Applicability(source_ids=frozenset({'cbr.reporting_forms.f123'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.reporting_forms.f123', ('rar', 'zip', 'dbf'), issue_required=True), Applicability(source_ids=frozenset({'cbr.reporting_forms.f123'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.reporting_forms.f123'), Applicability(source_ids=frozenset({'cbr.reporting_forms.f123'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.forms:extract"),
            F123_TABLE, Applicability(source_ids=frozenset({'cbr.reporting_forms.f123'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.forms:interpret"),
            F123_TABLE, Applicability(source_ids=frozenset({'cbr.reporting_forms.f123'})),
        ),
    }),
)

F134_PUBLICATION = Publication(
    'cbr.reporting_forms.f134', 'cbr.reporting_forms', 'Credit institution reporting form 134',
    'dated', ('rar', 'zip', 'dbf'), 'index', FORMS_INDEX, '134-(?P<date>\\d{8})\\.(?:rar|zip)',
)
F134_TABLE = FormSettings('cbr.reporting_forms.f134', '134', ('C3',), ('C1',),
    required_fields=(('REGN', 'N', 4), ('C1', 'C', 15), ('C3', 'N', 16)), require_measurement=True)
F134 = SeriesSpec(
    id='cbr.reporting_forms.f134',
    publication=F134_PUBLICATION,
    semantics=Semantics('reporting_period', ('report_date', 'credit_institution', 'form', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            F134_PUBLICATION, Applicability(source_ids=frozenset({'cbr.reporting_forms.f134'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            F134_PUBLICATION, Applicability(source_ids=frozenset({'cbr.reporting_forms.f134'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            F134_PUBLICATION, Applicability(source_ids=frozenset({'cbr.reporting_forms.f134'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            F134_PUBLICATION, Applicability(source_ids=frozenset({'cbr.reporting_forms.f134'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.reporting_forms.f134', ('rar', 'zip', 'dbf'), issue_required=True), Applicability(source_ids=frozenset({'cbr.reporting_forms.f134'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.reporting_forms.f134', ('rar', 'zip', 'dbf'), issue_required=True), Applicability(source_ids=frozenset({'cbr.reporting_forms.f134'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.reporting_forms.f134'), Applicability(source_ids=frozenset({'cbr.reporting_forms.f134'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.forms:extract"),
            F134_TABLE, Applicability(source_ids=frozenset({'cbr.reporting_forms.f134'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.forms:interpret"),
            F134_TABLE, Applicability(source_ids=frozenset({'cbr.reporting_forms.f134'})),
        ),
    }),
)

F135_PUBLICATION = Publication(
    'cbr.reporting_forms.f135', 'cbr.reporting_forms', 'Credit institution reporting form 135',
    'dated', ('rar', 'zip', 'dbf'), 'index', FORMS_INDEX, '135-(?P<date>\\d{8})\\.(?:rar|zip)',
)
F135_TABLE = FormSettings('cbr.reporting_forms.f135', '135')
F135 = SeriesSpec(
    id='cbr.reporting_forms.f135',
    publication=F135_PUBLICATION,
    semantics=Semantics('reporting_period', ('report_date', 'credit_institution', 'form', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            F135_PUBLICATION, Applicability(source_ids=frozenset({'cbr.reporting_forms.f135'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            F135_PUBLICATION, Applicability(source_ids=frozenset({'cbr.reporting_forms.f135'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            F135_PUBLICATION, Applicability(source_ids=frozenset({'cbr.reporting_forms.f135'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            F135_PUBLICATION, Applicability(source_ids=frozenset({'cbr.reporting_forms.f135'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.reporting_forms.f135', ('rar', 'zip', 'dbf'), issue_required=True), Applicability(source_ids=frozenset({'cbr.reporting_forms.f135'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.reporting_forms.f135', ('rar', 'zip', 'dbf'), issue_required=True), Applicability(source_ids=frozenset({'cbr.reporting_forms.f135'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.reporting_forms.f135'), Applicability(source_ids=frozenset({'cbr.reporting_forms.f135'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.forms:extract"),
            F135_TABLE, Applicability(source_ids=frozenset({'cbr.reporting_forms.f135'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.forms:interpret"),
            F135_TABLE, Applicability(source_ids=frozenset({'cbr.reporting_forms.f135'})),
        ),
    }),
)

F802_PUBLICATION = Publication(
    'cbr.reporting_forms.f802', 'cbr.reporting_forms', 'Credit institution reporting form 802',
    'dated', ('rar', 'zip', 'dbf'), 'index', FORMS_INDEX, '802-(?P<date>\\d{8})\\.(?:rar|zip)',
)
F802_TABLE = FormSettings('cbr.reporting_forms.f802', '802')
F802 = SeriesSpec(
    id='cbr.reporting_forms.f802',
    publication=F802_PUBLICATION,
    semantics=Semantics('reporting_period', ('report_date', 'credit_institution', 'form', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            F802_PUBLICATION, Applicability(source_ids=frozenset({'cbr.reporting_forms.f802'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            F802_PUBLICATION, Applicability(source_ids=frozenset({'cbr.reporting_forms.f802'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            F802_PUBLICATION, Applicability(source_ids=frozenset({'cbr.reporting_forms.f802'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            F802_PUBLICATION, Applicability(source_ids=frozenset({'cbr.reporting_forms.f802'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.reporting_forms.f802', ('rar', 'zip', 'dbf'), issue_required=True), Applicability(source_ids=frozenset({'cbr.reporting_forms.f802'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.reporting_forms.f802', ('rar', 'zip', 'dbf'), issue_required=True), Applicability(source_ids=frozenset({'cbr.reporting_forms.f802'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.reporting_forms.f802'), Applicability(source_ids=frozenset({'cbr.reporting_forms.f802'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.forms:extract"),
            F802_TABLE, Applicability(source_ids=frozenset({'cbr.reporting_forms.f802'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.forms:interpret"),
            F802_TABLE, Applicability(source_ids=frozenset({'cbr.reporting_forms.f802'})),
        ),
    }),
)

F803_PUBLICATION = Publication(
    'cbr.reporting_forms.f803', 'cbr.reporting_forms', 'Credit institution reporting form 803',
    'dated', ('rar', 'zip', 'dbf'), 'index', FORMS_INDEX, '803-(?P<date>\\d{8})\\.(?:rar|zip)',
)
F803_TABLE = FormSettings('cbr.reporting_forms.f803', '803', ('KORR_P', 'KORR_M', 'VSEGO'), ('RAZDEL', 'STR'), 'REGN_GKO', 'flow',
    required_fields=(('REGN_GKO', 'N', 4), ('RAZDEL', 'C', 3), ('STR', 'C', 5),
        ('KORR_P', 'N', 16), ('KORR_M', 'N', 16), ('VSEGO', 'N', 16)), require_measurement=True)
F803 = SeriesSpec(
    id='cbr.reporting_forms.f803',
    publication=F803_PUBLICATION,
    semantics=Semantics('reporting_period', ('report_date', 'credit_institution', 'form', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            F803_PUBLICATION, Applicability(source_ids=frozenset({'cbr.reporting_forms.f803'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            F803_PUBLICATION, Applicability(source_ids=frozenset({'cbr.reporting_forms.f803'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            F803_PUBLICATION, Applicability(source_ids=frozenset({'cbr.reporting_forms.f803'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            F803_PUBLICATION, Applicability(source_ids=frozenset({'cbr.reporting_forms.f803'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.reporting_forms.f803', ('rar', 'zip', 'dbf'), issue_required=True), Applicability(source_ids=frozenset({'cbr.reporting_forms.f803'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.reporting_forms.f803', ('rar', 'zip', 'dbf'), issue_required=True), Applicability(source_ids=frozenset({'cbr.reporting_forms.f803'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.reporting_forms.f803'), Applicability(source_ids=frozenset({'cbr.reporting_forms.f803'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.forms:extract"),
            F803_TABLE, Applicability(source_ids=frozenset({'cbr.reporting_forms.f803'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.forms:interpret"),
            F803_TABLE, Applicability(source_ids=frozenset({'cbr.reporting_forms.f803'})),
        ),
    }),
)

F805_PUBLICATION = Publication(
    'cbr.reporting_forms.f805', 'cbr.reporting_forms', 'Credit institution reporting form 805',
    'dated', ('rar', 'zip', 'dbf'), 'index', FORMS_INDEX, '805-(?P<date>\\d{8})\\.(?:rar|zip)',
)
F805_TABLE = FormSettings('cbr.reporting_forms.f805', '805')
F805 = SeriesSpec(
    id='cbr.reporting_forms.f805',
    publication=F805_PUBLICATION,
    semantics=Semantics('reporting_period', ('report_date', 'credit_institution', 'form', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            F805_PUBLICATION, Applicability(source_ids=frozenset({'cbr.reporting_forms.f805'})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            F805_PUBLICATION, Applicability(source_ids=frozenset({'cbr.reporting_forms.f805'})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            F805_PUBLICATION, Applicability(source_ids=frozenset({'cbr.reporting_forms.f805'})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            F805_PUBLICATION, Applicability(source_ids=frozenset({'cbr.reporting_forms.f805'})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement('cbr.reporting_forms.f805', ('rar', 'zip', 'dbf'), issue_required=True), Applicability(source_ids=frozenset({'cbr.reporting_forms.f805'})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement('cbr.reporting_forms.f805', ('rar', 'zip', 'dbf'), issue_required=True), Applicability(source_ids=frozenset({'cbr.reporting_forms.f805'})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules('cbr.reporting_forms.f805'), Applicability(source_ids=frozenset({'cbr.reporting_forms.f805'})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.forms:extract"),
            F805_TABLE, Applicability(source_ids=frozenset({'cbr.reporting_forms.f805'})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.forms:interpret"),
            F805_TABLE, Applicability(source_ids=frozenset({'cbr.reporting_forms.f805'})),
        ),
    }),
)

