"""Explicit Bank of Russia exchange_rates source records and action settings."""
from types import MappingProxyType
from stratbox.capabilities.model.domains import SeriesSpec, CommandSpec, Applicability
from stratbox.capabilities.model.methods import MethodRef
from stratbox.domains.cbr.common.contracts import Publication, Semantics, StatisticalSettings, TableVariant, FormSettings, FamilySettings, SourceRequirement, MappingRules
from stratbox.domains.cbr.common.publications import SORS_INDEX, FORMS_INDEX, ESCROW_INDEX, OFFICES_PAGE, TERRITORIAL_INDEX

FAMILY_ID = 'cbr.exchange_rates'

EXCHANGE_RATE_PUBLICATION = Publication(
    'cbr.exchange_rates.exchange_rate', FAMILY_ID, 'Exchange rate indices',
    'rolling', ('xlsx',), 'fixed', 'https://cbr.ru/vfs/statistics/credit_statistics/ex_rate_ind/exchange_rate.xlsx', None,
)
EXCHANGE_RATE_TABLE = StatisticalSettings(
    EXCHANGE_RATE_PUBLICATION.series_id, (
        TableVariant('table_1', 'Ежемесячные', 'statistics', None, 'month', ('source_measure_or_country', 'frequency', 'reference_basis'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Nominal rates, averages, published indices and trade weights retain separate metric identities and reference bases.'),
        TableVariant('table_2', 'Ежеквартальные', 'statistics', None, 'quarter', ('source_measure_or_country', 'frequency', 'reference_basis'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Nominal rates, averages, published indices and trade weights retain separate metric identities and reference bases.'),
        TableVariant('table_3', 'Доли', 'statistics', 'ratio', 'year', ('source_measure_or_country', 'frequency', 'reference_basis'), 'Explicit row unit, otherwise unambiguous table unit; unresolved units are diagnostics.', 'Nominal rates, averages, published indices and trade weights retain separate metric identities and reference bases.'),
    ),
)
EXCHANGE_RATE = SeriesSpec(
    id=EXCHANGE_RATE_PUBLICATION.series_id,
    publication=EXCHANGE_RATE_PUBLICATION,
    semantics=Semantics('publisher_defined', ('publication', 'record', 'field'), 'Source-local complete physical evidence; semantic coverage is independently qualified.'),
    commands=MappingProxyType({
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.methods.actions.serialization:decode")),
        "command.request.prepare": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:prepare_request"),
            EXCHANGE_RATE_PUBLICATION, Applicability(source_ids=frozenset({EXCHANGE_RATE_PUBLICATION.series_id})),
        ),
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:scan"),
            EXCHANGE_RATE_PUBLICATION, Applicability(source_ids=frozenset({EXCHANGE_RATE_PUBLICATION.series_id})),
        ),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:select"),
            EXCHANGE_RATE_PUBLICATION, Applicability(source_ids=frozenset({EXCHANGE_RATE_PUBLICATION.series_id})),
        ),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:assess"),
            EXCHANGE_RATE_PUBLICATION, Applicability(source_ids=frozenset({EXCHANGE_RATE_PUBLICATION.series_id})),
        ),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.publications:identify"),
            SourceRequirement(EXCHANGE_RATE_PUBLICATION.series_id, EXCHANGE_RATE_PUBLICATION.formats, issue_required=EXCHANGE_RATE_PUBLICATION.issue_model == 'dated', locator=EXCHANGE_RATE_PUBLICATION.locator, filename_pattern=EXCHANGE_RATE_PUBLICATION.filename_pattern, publication_kind=EXCHANGE_RATE_PUBLICATION.kind), Applicability(source_ids=frozenset({EXCHANGE_RATE_PUBLICATION.series_id})),
        ),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:validate"),
            SourceRequirement(EXCHANGE_RATE_PUBLICATION.series_id, EXCHANGE_RATE_PUBLICATION.formats, issue_required=EXCHANGE_RATE_PUBLICATION.issue_model == 'dated', locator=EXCHANGE_RATE_PUBLICATION.locator, filename_pattern=EXCHANGE_RATE_PUBLICATION.filename_pattern, publication_kind=EXCHANGE_RATE_PUBLICATION.kind), Applicability(source_ids=frozenset({EXCHANGE_RATE_PUBLICATION.series_id})),
        ),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.observations:align"),
            MappingRules(EXCHANGE_RATE_PUBLICATION.series_id), Applicability(source_ids=frozenset({EXCHANGE_RATE_PUBLICATION.series_id})),
        ),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:extract"),
            EXCHANGE_RATE_TABLE, Applicability(source_ids=frozenset({EXCHANGE_RATE_PUBLICATION.series_id})),
        ),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.cbr.methods.actions.statistics:interpret"),
            EXCHANGE_RATE_TABLE, Applicability(source_ids=frozenset({EXCHANGE_RATE_PUBLICATION.series_id})),
        ),
    }),
)

