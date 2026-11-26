"""Explicit static fiscal series declarations; no generated runtime operations."""
from stratbox.capabilities.model.domains import Applicability, CommandSpec, ObservationSemantics, PublicationSpec, SeriesSpec
from stratbox.capabilities.model.methods import MethodRef
from ..common.access import FEDERAL_INDEX, CONSOLIDATED_INDEX, REGIONAL_INDEX, FUND_INDEX
from ..common.publications import SourceRules, FEDERAL_ASSETS, CONSOLIDATED_ASSETS, REGIONAL_ASSETS, FUND_ASSETS
from ..common.semantics import TableRules, DocumentRules, BUDGET_ROWS, FUND_ROWS

CON_MONTHLY_PUBLICATION = SourceRules("minfin.conbud.monthly", "minfin.conbud", CONSOLIDATED_INDEX, CONSOLIDATED_ASSETS[0], CONSOLIDATED_ASSETS, "monthly", "ytd")
CON_MONTHLY_TABLE = TableRules("minfin.conbud.monthly", "minfin.conbud", "monthly", "ytd", "russian_consolidated_budget", BUDGET_ROWS)
CON_MONTHLY = SeriesSpec(
    id="minfin.conbud.monthly",
    publication=PublicationSpec("minfin.conbud.monthly", "Consolidated budget: monthly", CONSOLIDATED_INDEX, frozenset({"xlsx"}), "monthly", settings=CON_MONTHLY_PUBLICATION),
    semantics=ObservationSemantics(("metric", "subject", "period", "perimeter"), "ytd", "flow", "RUB", CON_MONTHLY_TABLE),
    commands={
        "command.request.prepare": CommandSpec(MethodRef("stratbox.domains.minfin.methods.publications:prepare_request"), CON_MONTHLY_PUBLICATION, Applicability()),
        "command.publication.scan": CommandSpec(MethodRef("stratbox.domains.minfin.methods.publications:scan"), CON_MONTHLY_PUBLICATION, Applicability()),
        "command.issue.select": CommandSpec(MethodRef("stratbox.domains.minfin.methods.publications:select"), CON_MONTHLY_PUBLICATION, Applicability()),
        "command.source.assess": CommandSpec(MethodRef("stratbox.domains.minfin.methods.publications:assess"), CON_MONTHLY_PUBLICATION, Applicability()),
        "command.table.extract": CommandSpec(MethodRef("stratbox.domains.minfin.methods.budget:extract"), CON_MONTHLY_TABLE, Applicability(source_ids={"minfin.conbud.monthly"})),
        "command.table.interpret": CommandSpec(MethodRef("stratbox.domains.minfin.methods.budget:interpret"), CON_MONTHLY_TABLE, Applicability(source_ids={"minfin.conbud.monthly"})),
        "command.observations.validate": CommandSpec(MethodRef("stratbox.domains.minfin.methods.budget:validate"), CON_MONTHLY_TABLE, Applicability(source_ids={"minfin.conbud.monthly"})),
        "command.observations.align": CommandSpec(MethodRef("stratbox.domains.minfin.methods.budget:align"), CON_MONTHLY_TABLE, Applicability(source_ids={"minfin.conbud.monthly"})),
    },
)

CON_QUARTERLY_PUBLICATION = SourceRules("minfin.conbud.quarterly", "minfin.conbud", CONSOLIDATED_INDEX, CONSOLIDATED_ASSETS[1], CONSOLIDATED_ASSETS, "quarterly", "ytd")
CON_QUARTERLY_TABLE = TableRules("minfin.conbud.quarterly", "minfin.conbud", "quarterly", "ytd", "russian_consolidated_budget", BUDGET_ROWS)
CON_QUARTERLY = SeriesSpec(
    id="minfin.conbud.quarterly",
    publication=PublicationSpec("minfin.conbud.quarterly", "Consolidated budget: quarterly", CONSOLIDATED_INDEX, frozenset({"xlsx"}), "quarterly", settings=CON_QUARTERLY_PUBLICATION),
    semantics=ObservationSemantics(("metric", "subject", "period", "perimeter"), "ytd", "flow", "RUB", CON_QUARTERLY_TABLE),
    commands={
        "command.request.prepare": CommandSpec(MethodRef("stratbox.domains.minfin.methods.publications:prepare_request"), CON_QUARTERLY_PUBLICATION, Applicability()),
        "command.publication.scan": CommandSpec(MethodRef("stratbox.domains.minfin.methods.publications:scan"), CON_QUARTERLY_PUBLICATION, Applicability()),
        "command.issue.select": CommandSpec(MethodRef("stratbox.domains.minfin.methods.publications:select"), CON_QUARTERLY_PUBLICATION, Applicability()),
        "command.source.assess": CommandSpec(MethodRef("stratbox.domains.minfin.methods.publications:assess"), CON_QUARTERLY_PUBLICATION, Applicability()),
        "command.table.extract": CommandSpec(MethodRef("stratbox.domains.minfin.methods.budget:extract"), CON_QUARTERLY_TABLE, Applicability(source_ids={"minfin.conbud.quarterly"})),
        "command.table.interpret": CommandSpec(MethodRef("stratbox.domains.minfin.methods.budget:interpret"), CON_QUARTERLY_TABLE, Applicability(source_ids={"minfin.conbud.quarterly"})),
        "command.observations.validate": CommandSpec(MethodRef("stratbox.domains.minfin.methods.budget:validate"), CON_QUARTERLY_TABLE, Applicability(source_ids={"minfin.conbud.quarterly"})),
        "command.observations.align": CommandSpec(MethodRef("stratbox.domains.minfin.methods.budget:align"), CON_QUARTERLY_TABLE, Applicability(source_ids={"minfin.conbud.quarterly"})),
    },
)

CON_ANNUAL_PUBLICATION = SourceRules("minfin.conbud.annual", "minfin.conbud", CONSOLIDATED_INDEX, CONSOLIDATED_ASSETS[2], CONSOLIDATED_ASSETS, "annual", "annual")
CON_ANNUAL_TABLE = TableRules("minfin.conbud.annual", "minfin.conbud", "annual", "annual", "russian_consolidated_budget", BUDGET_ROWS)
CON_ANNUAL = SeriesSpec(
    id="minfin.conbud.annual",
    publication=PublicationSpec("minfin.conbud.annual", "Consolidated budget: annual", CONSOLIDATED_INDEX, frozenset({"xlsx"}), "annual", settings=CON_ANNUAL_PUBLICATION),
    semantics=ObservationSemantics(("metric", "subject", "period", "perimeter"), "annual", "flow", "RUB", CON_ANNUAL_TABLE),
    commands={
        "command.request.prepare": CommandSpec(MethodRef("stratbox.domains.minfin.methods.publications:prepare_request"), CON_ANNUAL_PUBLICATION, Applicability()),
        "command.publication.scan": CommandSpec(MethodRef("stratbox.domains.minfin.methods.publications:scan"), CON_ANNUAL_PUBLICATION, Applicability()),
        "command.issue.select": CommandSpec(MethodRef("stratbox.domains.minfin.methods.publications:select"), CON_ANNUAL_PUBLICATION, Applicability()),
        "command.source.assess": CommandSpec(MethodRef("stratbox.domains.minfin.methods.publications:assess"), CON_ANNUAL_PUBLICATION, Applicability()),
        "command.table.extract": CommandSpec(MethodRef("stratbox.domains.minfin.methods.budget:extract"), CON_ANNUAL_TABLE, Applicability(source_ids={"minfin.conbud.annual"})),
        "command.table.interpret": CommandSpec(MethodRef("stratbox.domains.minfin.methods.budget:interpret"), CON_ANNUAL_TABLE, Applicability(source_ids={"minfin.conbud.annual"})),
        "command.observations.validate": CommandSpec(MethodRef("stratbox.domains.minfin.methods.budget:validate"), CON_ANNUAL_TABLE, Applicability(source_ids={"minfin.conbud.annual"})),
        "command.observations.align": CommandSpec(MethodRef("stratbox.domains.minfin.methods.budget:align"), CON_ANNUAL_TABLE, Applicability(source_ids={"minfin.conbud.annual"})),
    },
)

