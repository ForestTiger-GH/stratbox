"""Explicit static fiscal series declarations; no generated runtime operations."""
from stratbox.capabilities.model.domains import Applicability, CommandSpec, ObservationSemantics, PublicationSpec, SeriesSpec
from stratbox.capabilities.model.methods import MethodRef
from ..common.access import FEDERAL_INDEX, CONSOLIDATED_INDEX, REGIONAL_INDEX, FUND_INDEX
from ..common.publications import SourceRules, FEDERAL_ASSETS, CONSOLIDATED_ASSETS, REGIONAL_ASSETS, FUND_ASSETS
from ..common.semantics import TableRules, DocumentRules, BUDGET_ROWS, FUND_ROWS

FUND_VOLUME_PUBLICATION = SourceRules("minfin.nwf.volume", "minfin.nwf", FUND_INDEX, FUND_ASSETS[1], FUND_ASSETS, "monthly", "stock", "document")
FUND_VOLUME_TABLE = DocumentRules("minfin.nwf.volume")
FUND_VOLUME = SeriesSpec(
    id="minfin.nwf.volume",
    publication=PublicationSpec("minfin.nwf.volume", "National Wealth Fund: fund_volume", FUND_INDEX, frozenset({"docx"}), "monthly", settings=FUND_VOLUME_PUBLICATION),
    semantics=ObservationSemantics(("metric", "subject", "period", "unit", "perimeter"), "row_specific", units="row_specific", settings=FUND_VOLUME_TABLE),
    commands={
        "command.request.prepare": CommandSpec(MethodRef("stratbox.domains.minfin.methods.publications:prepare_request"), FUND_VOLUME_PUBLICATION, Applicability()),
        "command.publication.scan": CommandSpec(MethodRef("stratbox.domains.minfin.methods.publications:scan"), FUND_VOLUME_PUBLICATION, Applicability()),
        "command.issue.select": CommandSpec(MethodRef("stratbox.domains.minfin.methods.publications:select"), FUND_VOLUME_PUBLICATION, Applicability()),
        "command.source.assess": CommandSpec(MethodRef("stratbox.domains.minfin.methods.publications:assess"), FUND_VOLUME_PUBLICATION, Applicability()),
        "command.table.extract": CommandSpec(MethodRef("stratbox.domains.minfin.methods.documents:extract"), FUND_VOLUME_TABLE, Applicability(source_ids={"minfin.nwf.volume"})),
        "command.table.interpret": CommandSpec(MethodRef("stratbox.domains.minfin.methods.documents:interpret"), FUND_VOLUME_TABLE, Applicability(source_ids={"minfin.nwf.volume"})),
        "command.observations.validate": CommandSpec(MethodRef("stratbox.domains.minfin.methods.documents:validate"), FUND_VOLUME_TABLE, Applicability(source_ids={"minfin.nwf.volume"})),
        "command.observations.align": CommandSpec(MethodRef("stratbox.domains.minfin.methods.documents:align"), FUND_VOLUME_TABLE, Applicability(source_ids={"minfin.nwf.volume"})),
    },
)
