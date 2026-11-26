"""One continuing reviewed logical table, directly specialized by methods."""
from stratbox.capabilities.model.domains import Applicability, CommandSpec, ObservationSemantics, SeriesSpec
from stratbox.capabilities.model.methods import MethodRef
from ..common.publications import KEP2_PUBLICATION
from ..methods.types import TableRules

RULES = TableRules('rosstat.short_term_indicators', 'rosstat.short_term_indicators', 'kep2')
KEP2 = SeriesSpec(id='rosstat.short_term_indicators', publication=KEP2_PUBLICATION,
    semantics=ObservationSemantics(("metric", "subject_namespace", "subject", "period", "frequency", "perimeter"), 'source intervals; annual, quarterly and monthly; native percent index bases'),
    commands={
        "command.material.identify": CommandSpec(MethodRef("stratbox.domains.rosstat.methods.materials:identify"),
            RULES, Applicability(source_ids=frozenset({'rosstat.short_term_indicators', 'rosstat.short_term_indicators'}))),
        "command.table.extract": CommandSpec(MethodRef("stratbox.domains.rosstat.methods.tables:extract"),
            RULES, Applicability(source_ids=frozenset({'rosstat.short_term_indicators', 'rosstat.short_term_indicators'}))),
        "command.table.interpret": CommandSpec(MethodRef("stratbox.domains.rosstat.methods.tables:interpret"),
            RULES, Applicability(source_ids=frozenset({'rosstat.short_term_indicators', 'rosstat.short_term_indicators'}))),
        "command.observations.validate": CommandSpec(MethodRef("stratbox.domains.rosstat.methods.tables:validate"),
            RULES, Applicability(source_ids=frozenset({'rosstat.short_term_indicators', 'rosstat.short_term_indicators'}))),
        "command.observations.align": CommandSpec(MethodRef("stratbox.domains.rosstat.methods.tables:align"),
            RULES, Applicability(source_ids=frozenset({'rosstat.short_term_indicators', 'rosstat.short_term_indicators'}))),
    })
