"""Explicit static fiscal series declarations; no generated runtime operations."""
from stratbox.capabilities.model.domains import Applicability, CommandSpec, ObservationSemantics, PublicationSpec, SeriesSpec
from stratbox.capabilities.model.methods import MethodRef
from ..common.access import FEDERAL_INDEX, CONSOLIDATED_INDEX, REGIONAL_INDEX, FUND_INDEX
from ..common.publications import SourceRules, FEDERAL_ASSETS, CONSOLIDATED_ASSETS, REGIONAL_ASSETS, FUND_ASSETS
from ..common.semantics import TableRules, DocumentRules, BUDGET_ROWS, FUND_ROWS

FUND_SHARES_PUBLICATION = SourceRules("minfin.nwf.preferred_shares", "minfin.nwf", FUND_INDEX, FUND_ASSETS[2], FUND_ASSETS, "monthly", "stock", "document")
FUND_SHARES_TABLE = DocumentRules("minfin.nwf.preferred_shares")
FUND_SHARES = SeriesSpec(
    id="minfin.nwf.preferred_shares",
    publication=PublicationSpec("minfin.nwf.preferred_shares", "National Wealth Fund: fund_shares", FUND_INDEX, frozenset({"docx"}), "monthly", settings=FUND_SHARES_PUBLICATION),
    semantics=ObservationSemantics(("metric", "subject", "period", "unit", "perimeter"), "row_specific", units="row_specific", settings=FUND_SHARES_TABLE),
    commands={
        "command.request.prepare": CommandSpec(MethodRef("stratbox.domains.minfin.methods.publications:prepare_request"), FUND_SHARES_PUBLICATION, Applicability()),
        "command.publication.scan": CommandSpec(MethodRef("stratbox.domains.minfin.methods.publications:scan"), FUND_SHARES_PUBLICATION, Applicability()),
        "command.issue.select": CommandSpec(MethodRef("stratbox.domains.minfin.methods.publications:select"), FUND_SHARES_PUBLICATION, Applicability()),
        "command.source.assess": CommandSpec(MethodRef("stratbox.domains.minfin.methods.publications:assess"), FUND_SHARES_PUBLICATION, Applicability()),
        "command.table.extract": CommandSpec(MethodRef("stratbox.domains.minfin.methods.documents:extract"), FUND_SHARES_TABLE, Applicability(source_ids={"minfin.nwf.preferred_shares"})),
        "command.table.interpret": CommandSpec(MethodRef("stratbox.domains.minfin.methods.documents:interpret"), FUND_SHARES_TABLE, Applicability(source_ids={"minfin.nwf.preferred_shares"})),
        "command.observations.validate": CommandSpec(MethodRef("stratbox.domains.minfin.methods.documents:validate"), FUND_SHARES_TABLE, Applicability(source_ids={"minfin.nwf.preferred_shares"})),
        "command.observations.align": CommandSpec(MethodRef("stratbox.domains.minfin.methods.documents:align"), FUND_SHARES_TABLE, Applicability(source_ids={"minfin.nwf.preferred_shares"})),
    },
)
