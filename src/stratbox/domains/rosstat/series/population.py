"""One continuing reviewed logical table, directly specialized by methods."""
from stratbox.capabilities.model.domains import Applicability, CommandSpec, ObservationSemantics, SeriesSpec
from stratbox.capabilities.model.methods import MethodRef
from ..common.publications import POPULATION_PUBLICATION
from ..methods.types import TableRules

RULES = TableRules('rosstat.population_municipalities', 'rosstat.population_municipalities.publications', 'population')
POPULATION = SeriesSpec(id='rosstat.population_municipalities', publication=POPULATION_PUBLICATION,
    semantics=ObservationSemantics(("metric", "subject_namespace", "subject", "period", "frequency", "perimeter"), 'annual population stocks at January 1; native source territory identity'),
    commands={
        "command.material.identify": CommandSpec(MethodRef("stratbox.domains.rosstat.methods.materials:identify"),
            RULES, Applicability(source_ids=frozenset({'rosstat.population_municipalities', 'rosstat.population_municipalities.publications'}))),
        "command.table.extract": CommandSpec(MethodRef("stratbox.domains.rosstat.methods.tables:extract"),
            RULES, Applicability(source_ids=frozenset({'rosstat.population_municipalities', 'rosstat.population_municipalities.publications'}))),
        "command.table.interpret": CommandSpec(MethodRef("stratbox.domains.rosstat.methods.tables:interpret"),
            RULES, Applicability(source_ids=frozenset({'rosstat.population_municipalities', 'rosstat.population_municipalities.publications'}))),
        "command.observations.validate": CommandSpec(MethodRef("stratbox.domains.rosstat.methods.tables:validate"),
            RULES, Applicability(source_ids=frozenset({'rosstat.population_municipalities', 'rosstat.population_municipalities.publications'}))),
        "command.observations.align": CommandSpec(MethodRef("stratbox.domains.rosstat.methods.tables:align"),
            RULES, Applicability(source_ids=frozenset({'rosstat.population_municipalities', 'rosstat.population_municipalities.publications'}))),
    })
