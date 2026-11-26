"""One continuing reviewed logical table, directly specialized by methods."""
from stratbox.capabilities.model.domains import Applicability, CommandSpec, ObservationSemantics, SeriesSpec
from stratbox.capabilities.model.methods import MethodRef
from ..common.publications import REGIONS
from ..methods.types import TableRules

RULES = TableRules('rosstat.socioeconomic_regions.industrial_production', 'rosstat.socioeconomic_regions', 'regional_industry')
REGIONAL_INDUSTRY = SeriesSpec(id='rosstat.socioeconomic_regions.industrial_production', publication=REGIONS,
    semantics=ObservationSemantics(("metric", "subject_namespace", "subject", "period", "frequency", "perimeter"), 'monthly and cumulative year-to-date industrial indices with explicit comparison bases'),
    commands={
        "command.material.identify": CommandSpec(MethodRef("stratbox.domains.rosstat.methods.materials:identify"),
            RULES, Applicability(source_ids=frozenset({'rosstat.socioeconomic_regions.industrial_production', 'rosstat.socioeconomic_regions'}))),
        "command.table.extract": CommandSpec(MethodRef("stratbox.domains.rosstat.methods.tables:extract"),
            RULES, Applicability(source_ids=frozenset({'rosstat.socioeconomic_regions.industrial_production', 'rosstat.socioeconomic_regions'}))),
        "command.table.interpret": CommandSpec(MethodRef("stratbox.domains.rosstat.methods.tables:interpret"),
            RULES, Applicability(source_ids=frozenset({'rosstat.socioeconomic_regions.industrial_production', 'rosstat.socioeconomic_regions'}))),
        "command.observations.validate": CommandSpec(MethodRef("stratbox.domains.rosstat.methods.tables:validate"),
            RULES, Applicability(source_ids=frozenset({'rosstat.socioeconomic_regions.industrial_production', 'rosstat.socioeconomic_regions'}))),
        "command.observations.align": CommandSpec(MethodRef("stratbox.domains.rosstat.methods.tables:align"),
            RULES, Applicability(source_ids=frozenset({'rosstat.socioeconomic_regions.industrial_production', 'rosstat.socioeconomic_regions'}))),
    })
