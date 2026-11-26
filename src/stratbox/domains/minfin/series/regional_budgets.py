"""Explicit static fiscal series declarations; no generated runtime operations."""
from stratbox.capabilities.model.domains import Applicability, CommandSpec, ObservationSemantics, PublicationSpec, SeriesSpec
from stratbox.capabilities.model.methods import MethodRef
from ..common.access import FEDERAL_INDEX, CONSOLIDATED_INDEX, REGIONAL_INDEX, FUND_INDEX
from ..common.publications import SourceRules, FEDERAL_ASSETS, CONSOLIDATED_ASSETS, REGIONAL_ASSETS, FUND_ASSETS
from ..common.semantics import TableRules, DocumentRules, BUDGET_ROWS, FUND_ROWS

SUB_MONTHLY_PUBLICATION = SourceRules("minfin.subbud.monthly", "minfin.subbud", REGIONAL_INDEX, REGIONAL_ASSETS[0], REGIONAL_ASSETS, "monthly", "ytd")
SUB_MONTHLY_TABLE = TableRules("minfin.subbud.monthly", "minfin.subbud", "monthly", "ytd", "russian_regional_budgets", BUDGET_ROWS)
SUB_MONTHLY = SeriesSpec(
    id="minfin.subbud.monthly",
    publication=PublicationSpec("minfin.subbud.monthly", "Regional budgets: monthly", REGIONAL_INDEX, frozenset({"xlsx"}), "monthly", settings=SUB_MONTHLY_PUBLICATION),
    semantics=ObservationSemantics(("metric", "subject", "period", "perimeter"), "ytd", "flow", "RUB", SUB_MONTHLY_TABLE),
    commands={
        "command.request.prepare": CommandSpec(MethodRef("stratbox.domains.minfin.methods.publications:prepare_request"), SUB_MONTHLY_PUBLICATION, Applicability()),
        "command.publication.scan": CommandSpec(MethodRef("stratbox.domains.minfin.methods.publications:scan"), SUB_MONTHLY_PUBLICATION, Applicability()),
        "command.issue.select": CommandSpec(MethodRef("stratbox.domains.minfin.methods.publications:select"), SUB_MONTHLY_PUBLICATION, Applicability()),
        "command.source.assess": CommandSpec(MethodRef("stratbox.domains.minfin.methods.publications:assess"), SUB_MONTHLY_PUBLICATION, Applicability()),
        "command.table.extract": CommandSpec(MethodRef("stratbox.domains.minfin.methods.budget:extract"), SUB_MONTHLY_TABLE, Applicability(source_ids={"minfin.subbud.monthly"})),
        "command.table.interpret": CommandSpec(MethodRef("stratbox.domains.minfin.methods.budget:interpret"), SUB_MONTHLY_TABLE, Applicability(source_ids={"minfin.subbud.monthly"})),
        "command.observations.validate": CommandSpec(MethodRef("stratbox.domains.minfin.methods.budget:validate"), SUB_MONTHLY_TABLE, Applicability(source_ids={"minfin.subbud.monthly"})),
        "command.observations.align": CommandSpec(MethodRef("stratbox.domains.minfin.methods.budget:align"), SUB_MONTHLY_TABLE, Applicability(source_ids={"minfin.subbud.monthly"})),
    },
)

SUB_QUARTERLY_PUBLICATION = SourceRules("minfin.subbud.quarterly", "minfin.subbud", REGIONAL_INDEX, REGIONAL_ASSETS[1], REGIONAL_ASSETS, "quarterly", "ytd")
SUB_QUARTERLY_TABLE = TableRules("minfin.subbud.quarterly", "minfin.subbud", "quarterly", "ytd", "russian_regional_budgets", BUDGET_ROWS)
SUB_QUARTERLY = SeriesSpec(
    id="minfin.subbud.quarterly",
    publication=PublicationSpec("minfin.subbud.quarterly", "Regional budgets: quarterly", REGIONAL_INDEX, frozenset({"xlsx"}), "quarterly", settings=SUB_QUARTERLY_PUBLICATION),
    semantics=ObservationSemantics(("metric", "subject", "period", "perimeter"), "ytd", "flow", "RUB", SUB_QUARTERLY_TABLE),
    commands={
        "command.request.prepare": CommandSpec(MethodRef("stratbox.domains.minfin.methods.publications:prepare_request"), SUB_QUARTERLY_PUBLICATION, Applicability()),
        "command.publication.scan": CommandSpec(MethodRef("stratbox.domains.minfin.methods.publications:scan"), SUB_QUARTERLY_PUBLICATION, Applicability()),
        "command.issue.select": CommandSpec(MethodRef("stratbox.domains.minfin.methods.publications:select"), SUB_QUARTERLY_PUBLICATION, Applicability()),
        "command.source.assess": CommandSpec(MethodRef("stratbox.domains.minfin.methods.publications:assess"), SUB_QUARTERLY_PUBLICATION, Applicability()),
        "command.table.extract": CommandSpec(MethodRef("stratbox.domains.minfin.methods.budget:extract"), SUB_QUARTERLY_TABLE, Applicability(source_ids={"minfin.subbud.quarterly"})),
        "command.table.interpret": CommandSpec(MethodRef("stratbox.domains.minfin.methods.budget:interpret"), SUB_QUARTERLY_TABLE, Applicability(source_ids={"minfin.subbud.quarterly"})),
        "command.observations.validate": CommandSpec(MethodRef("stratbox.domains.minfin.methods.budget:validate"), SUB_QUARTERLY_TABLE, Applicability(source_ids={"minfin.subbud.quarterly"})),
        "command.observations.align": CommandSpec(MethodRef("stratbox.domains.minfin.methods.budget:align"), SUB_QUARTERLY_TABLE, Applicability(source_ids={"minfin.subbud.quarterly"})),
    },
)

SUB_ANNUAL_PUBLICATION = SourceRules("minfin.subbud.annual", "minfin.subbud", REGIONAL_INDEX, REGIONAL_ASSETS[2], REGIONAL_ASSETS, "annual", "annual")
SUB_ANNUAL_TABLE = TableRules("minfin.subbud.annual", "minfin.subbud", "annual", "annual", "russian_regional_budgets", BUDGET_ROWS)
SUB_ANNUAL = SeriesSpec(
    id="minfin.subbud.annual",
    publication=PublicationSpec("minfin.subbud.annual", "Regional budgets: annual", REGIONAL_INDEX, frozenset({"xlsx"}), "annual", settings=SUB_ANNUAL_PUBLICATION),
    semantics=ObservationSemantics(("metric", "subject", "period", "perimeter"), "annual", "flow", "RUB", SUB_ANNUAL_TABLE),
    commands={
        "command.request.prepare": CommandSpec(MethodRef("stratbox.domains.minfin.methods.publications:prepare_request"), SUB_ANNUAL_PUBLICATION, Applicability()),
        "command.publication.scan": CommandSpec(MethodRef("stratbox.domains.minfin.methods.publications:scan"), SUB_ANNUAL_PUBLICATION, Applicability()),
        "command.issue.select": CommandSpec(MethodRef("stratbox.domains.minfin.methods.publications:select"), SUB_ANNUAL_PUBLICATION, Applicability()),
        "command.source.assess": CommandSpec(MethodRef("stratbox.domains.minfin.methods.publications:assess"), SUB_ANNUAL_PUBLICATION, Applicability()),
        "command.table.extract": CommandSpec(MethodRef("stratbox.domains.minfin.methods.budget:extract"), SUB_ANNUAL_TABLE, Applicability(source_ids={"minfin.subbud.annual"})),
        "command.table.interpret": CommandSpec(MethodRef("stratbox.domains.minfin.methods.budget:interpret"), SUB_ANNUAL_TABLE, Applicability(source_ids={"minfin.subbud.annual"})),
        "command.observations.validate": CommandSpec(MethodRef("stratbox.domains.minfin.methods.budget:validate"), SUB_ANNUAL_TABLE, Applicability(source_ids={"minfin.subbud.annual"})),
        "command.observations.align": CommandSpec(MethodRef("stratbox.domains.minfin.methods.budget:align"), SUB_ANNUAL_TABLE, Applicability(source_ids={"minfin.subbud.annual"})),
    },
)

