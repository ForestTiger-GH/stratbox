"""The sole static Rosstat catalog: publications, actual table series and gaps."""
from stratbox.capabilities.model.domains import Applicability, CalculationSpec, CommandSpec, DomainSpec, ProductSpec
from stratbox.capabilities.model.methods import MethodRef
from .common.publications import RUSSIA, REGIONS, KEP2_PUBLICATION, POPULATION_PUBLICATION
from .common.kep2 import KEP2_INDICATORS
from .series.kep2 import KEP2
from .series.population import POPULATION
from .series.regional_industry import REGIONAL_INDUSTRY

DOMAIN = DomainSpec(
    id="rosstat",
    common={
        "publications": {RUSSIA.id: RUSSIA, REGIONS.id: REGIONS,
            KEP2_PUBLICATION.id: KEP2_PUBLICATION, POPULATION_PUBLICATION.id: POPULATION_PUBLICATION},
        "indicators": KEP2_INDICATORS,
        "scientific_obligations": {
            "national_pdf_tables": "Reviewed numerical table geometry and economic mappings remain required; text decoding is physical evidence only.",
            "regional_table_census": "Industrial production is reviewed; the remaining actual archive tables require their own inspected declarations.",
            "population_geography": "2022/2023 source rows and 2024 TERSON-MO are preserved; a canonical municipal crosswalk requires independent evidence.",
            "historical_layouts": "Population 2022/2023/2024 and regional industrial June/August 2026 layouts have bounded reviewed support.",
        },
    },
    series={KEP2.id: KEP2, POPULATION.id: POPULATION, REGIONAL_INDUSTRY.id: REGIONAL_INDUSTRY},
    calculations={"rosstat.index_growth": CalculationSpec(
        id="rosstat.index_growth",
        commands={"command.calculate.index": CommandSpec(
            MethodRef("stratbox.core.commands.standard:calculate_index"),
            {"mode": "growth"}, Applicability())},
        inputs={"observations": "Published percent indices with explicit comparison bases"},
        semantics={"unit": "percent", "measure_kind": "index"},
    )},
    products={
        "rosstat.kep2.monthly": ProductSpec(id="rosstat.kep2.monthly", commands={
            "command.view.prepare": CommandSpec(
                MethodRef("stratbox.domains.rosstat.methods.products:monthly"), None,
                Applicability(source_ids=frozenset({"rosstat.short_term_indicators"})))},
            settings={"format": "csv"}),
        "rosstat.kep2.monthly.xlsx": ProductSpec(id="rosstat.kep2.monthly.xlsx", commands={
            "command.view.prepare": CommandSpec(
                MethodRef("stratbox.domains.rosstat.methods.products:monthly"), None,
                Applicability(source_ids=frozenset({"rosstat.short_term_indicators"}))),
            "command.product.render": CommandSpec(
                MethodRef("stratbox.domains.rosstat.methods.products:render_monthly_workbook"), None,
                Applicability(required_providers=frozenset()))},
            settings={"format": "xlsx"}),
    },
)
