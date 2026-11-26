"""Explicit static fiscal series declarations; no generated runtime operations."""
from stratbox.capabilities.model.domains import Applicability, CommandSpec, ObservationSemantics, PublicationSpec, SeriesSpec
from stratbox.capabilities.model.methods import MethodRef
from ..common.access import FEDERAL_INDEX, CONSOLIDATED_INDEX, REGIONAL_INDEX, FUND_INDEX
from ..common.publications import SourceRules, FEDERAL_ASSETS, CONSOLIDATED_ASSETS, REGIONAL_ASSETS, FUND_ASSETS
from ..common.semantics import TableRules, DocumentRules, BUDGET_ROWS, FUND_ROWS

FUND_MOVEMENT_PUBLICATION = SourceRules("minfin.nwf.flows", "minfin.nwf", FUND_INDEX, FUND_ASSETS[0], FUND_ASSETS, "monthly", "stock", "table")
FUND_MOVEMENT_TABLE = TableRules("minfin.nwf.flows", "minfin.nwf", "monthly", "stock", "russian_national_wealth_fund", FUND_ROWS)
FUND_MOVEMENT = SeriesSpec(
    id="minfin.nwf.flows",
    publication=PublicationSpec("minfin.nwf.flows", "National Wealth Fund: fund_movement", FUND_INDEX, frozenset({"xlsx"}), "monthly", settings=FUND_MOVEMENT_PUBLICATION),
    semantics=ObservationSemantics(("metric", "subject", "period", "unit", "perimeter"), "row_specific", units="row_specific", settings=FUND_MOVEMENT_TABLE),
    commands={
        "command.request.prepare": CommandSpec(MethodRef("stratbox.domains.minfin.methods.publications:prepare_request"), FUND_MOVEMENT_PUBLICATION, Applicability()),
        "command.publication.scan": CommandSpec(MethodRef("stratbox.domains.minfin.methods.publications:scan"), FUND_MOVEMENT_PUBLICATION, Applicability()),
        "command.issue.select": CommandSpec(MethodRef("stratbox.domains.minfin.methods.publications:select"), FUND_MOVEMENT_PUBLICATION, Applicability()),
        "command.source.assess": CommandSpec(MethodRef("stratbox.domains.minfin.methods.publications:assess"), FUND_MOVEMENT_PUBLICATION, Applicability()),
        "command.table.extract": CommandSpec(MethodRef("stratbox.domains.minfin.methods.budget:extract"), FUND_MOVEMENT_TABLE, Applicability(source_ids={"minfin.nwf.flows"})),
        "command.table.interpret": CommandSpec(MethodRef("stratbox.domains.minfin.methods.budget:interpret"), FUND_MOVEMENT_TABLE, Applicability(source_ids={"minfin.nwf.flows"})),
        "command.observations.validate": CommandSpec(MethodRef("stratbox.domains.minfin.methods.budget:validate"), FUND_MOVEMENT_TABLE, Applicability(source_ids={"minfin.nwf.flows"})),
        "command.observations.align": CommandSpec(MethodRef("stratbox.domains.minfin.methods.budget:align"), FUND_MOVEMENT_TABLE, Applicability(source_ids={"minfin.nwf.flows"})),
    },
)
