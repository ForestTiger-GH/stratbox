"""Explicit static fiscal series declarations; no generated runtime operations."""
from stratbox.capabilities.model.domains import Applicability, CommandSpec, ObservationSemantics, PublicationSpec, SeriesSpec
from stratbox.capabilities.model.methods import MethodRef
from ..common.access import FEDERAL_INDEX, CONSOLIDATED_INDEX, REGIONAL_INDEX, FUND_INDEX
from ..common.publications import SourceRules, FEDERAL_ASSETS, CONSOLIDATED_ASSETS, REGIONAL_ASSETS, FUND_ASSETS
from ..common.semantics import TableRules, DocumentRules, BUDGET_ROWS, FUND_ROWS

FUND_DEPOSITS_PUBLICATION = SourceRules("minfin.nwf.veb_deposits", "minfin.nwf", FUND_INDEX, FUND_ASSETS[3], FUND_ASSETS, "monthly", "stock", "document")
FUND_DEPOSITS_TABLE = DocumentRules("minfin.nwf.veb_deposits")
FUND_DEPOSITS = SeriesSpec(
    id="minfin.nwf.veb_deposits",
    publication=PublicationSpec("minfin.nwf.veb_deposits", "National Wealth Fund: fund_deposits", FUND_INDEX, frozenset({"doc"}), "monthly", settings=FUND_DEPOSITS_PUBLICATION),
    semantics=ObservationSemantics(("metric", "subject", "period", "unit", "perimeter"), "row_specific", units="row_specific", settings=FUND_DEPOSITS_TABLE),
    commands={
        "command.request.prepare": CommandSpec(MethodRef("stratbox.domains.minfin.methods.publications:prepare_request"), FUND_DEPOSITS_PUBLICATION, Applicability()),
        "command.publication.scan": CommandSpec(MethodRef("stratbox.domains.minfin.methods.publications:scan"), FUND_DEPOSITS_PUBLICATION, Applicability()),
        "command.issue.select": CommandSpec(MethodRef("stratbox.domains.minfin.methods.publications:select"), FUND_DEPOSITS_PUBLICATION, Applicability()),
        "command.source.assess": CommandSpec(MethodRef("stratbox.domains.minfin.methods.publications:assess"), FUND_DEPOSITS_PUBLICATION, Applicability()),
        "command.table.extract": CommandSpec(MethodRef("stratbox.domains.minfin.methods.documents:extract"), FUND_DEPOSITS_TABLE, Applicability(source_ids={"minfin.nwf.veb_deposits"})),
        "command.table.interpret": CommandSpec(MethodRef("stratbox.domains.minfin.methods.documents:interpret"), FUND_DEPOSITS_TABLE, Applicability(source_ids={"minfin.nwf.veb_deposits"})),
        "command.observations.validate": CommandSpec(MethodRef("stratbox.domains.minfin.methods.documents:validate"), FUND_DEPOSITS_TABLE, Applicability(source_ids={"minfin.nwf.veb_deposits"})),
        "command.observations.align": CommandSpec(MethodRef("stratbox.domains.minfin.methods.documents:align"), FUND_DEPOSITS_TABLE, Applicability(source_ids={"minfin.nwf.veb_deposits"})),
    },
)
