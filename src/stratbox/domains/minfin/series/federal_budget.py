"""Explicit static fiscal series declarations; no generated runtime operations."""
from stratbox.capabilities.model.domains import Applicability, CommandSpec, ObservationSemantics, PublicationSpec, SeriesSpec
from stratbox.capabilities.model.methods import MethodRef
from ..common.access import FEDERAL_INDEX, CONSOLIDATED_INDEX, REGIONAL_INDEX, FUND_INDEX
from ..common.publications import SourceRules, FEDERAL_ASSETS, CONSOLIDATED_ASSETS, REGIONAL_ASSETS, FUND_ASSETS
from ..common.semantics import TableRules, DocumentRules, BUDGET_ROWS, FUND_ROWS

FED_MONTHLY_PUBLICATION = SourceRules("minfin.fedbud.annex3.monthly", "minfin.fedbud", FEDERAL_INDEX, FEDERAL_ASSETS[0], FEDERAL_ASSETS, "monthly", "ytd")
FED_MONTHLY_TABLE = TableRules("minfin.fedbud.annex3.monthly", "minfin.fedbud", "monthly", "ytd", "russian_federal_budget", BUDGET_ROWS)
FED_MONTHLY = SeriesSpec(
    id="minfin.fedbud.annex3.monthly",
    publication=PublicationSpec("minfin.fedbud.annex3.monthly", "Federal budget, annex 3: monthly", FEDERAL_INDEX, frozenset({"xlsx"}), "monthly", settings=FED_MONTHLY_PUBLICATION),
    semantics=ObservationSemantics(("metric", "subject", "period", "perimeter"), "ytd", "flow", "RUB", FED_MONTHLY_TABLE),
    commands={
        "command.request.prepare": CommandSpec(MethodRef("stratbox.domains.minfin.methods.publications:prepare_request"), FED_MONTHLY_PUBLICATION, Applicability()),
        "command.publication.scan": CommandSpec(MethodRef("stratbox.domains.minfin.methods.publications:scan"), FED_MONTHLY_PUBLICATION, Applicability()),
        "command.issue.select": CommandSpec(MethodRef("stratbox.domains.minfin.methods.publications:select"), FED_MONTHLY_PUBLICATION, Applicability()),
        "command.source.assess": CommandSpec(MethodRef("stratbox.domains.minfin.methods.publications:assess"), FED_MONTHLY_PUBLICATION, Applicability()),
        "command.table.extract": CommandSpec(MethodRef("stratbox.domains.minfin.methods.budget:extract"), FED_MONTHLY_TABLE, Applicability(source_ids={"minfin.fedbud.annex3.monthly"})),
        "command.table.interpret": CommandSpec(MethodRef("stratbox.domains.minfin.methods.budget:interpret"), FED_MONTHLY_TABLE, Applicability(source_ids={"minfin.fedbud.annex3.monthly"})),
        "command.observations.validate": CommandSpec(MethodRef("stratbox.domains.minfin.methods.budget:validate"), FED_MONTHLY_TABLE, Applicability(source_ids={"minfin.fedbud.annex3.monthly"})),
        "command.observations.align": CommandSpec(MethodRef("stratbox.domains.minfin.methods.budget:align"), FED_MONTHLY_TABLE, Applicability(source_ids={"minfin.fedbud.annex3.monthly"})),
    },
)

FED_QUARTERLY_PUBLICATION = SourceRules("minfin.fedbud.annex3.quarterly", "minfin.fedbud", FEDERAL_INDEX, FEDERAL_ASSETS[1], FEDERAL_ASSETS, "quarterly", "ytd")
FED_QUARTERLY_TABLE = TableRules("minfin.fedbud.annex3.quarterly", "minfin.fedbud", "quarterly", "ytd", "russian_federal_budget", BUDGET_ROWS)
FED_QUARTERLY = SeriesSpec(
    id="minfin.fedbud.annex3.quarterly",
    publication=PublicationSpec("minfin.fedbud.annex3.quarterly", "Federal budget, annex 3: quarterly", FEDERAL_INDEX, frozenset({"xlsx"}), "quarterly", settings=FED_QUARTERLY_PUBLICATION),
    semantics=ObservationSemantics(("metric", "subject", "period", "perimeter"), "ytd", "flow", "RUB", FED_QUARTERLY_TABLE),
    commands={
        "command.request.prepare": CommandSpec(MethodRef("stratbox.domains.minfin.methods.publications:prepare_request"), FED_QUARTERLY_PUBLICATION, Applicability()),
        "command.publication.scan": CommandSpec(MethodRef("stratbox.domains.minfin.methods.publications:scan"), FED_QUARTERLY_PUBLICATION, Applicability()),
        "command.issue.select": CommandSpec(MethodRef("stratbox.domains.minfin.methods.publications:select"), FED_QUARTERLY_PUBLICATION, Applicability()),
        "command.source.assess": CommandSpec(MethodRef("stratbox.domains.minfin.methods.publications:assess"), FED_QUARTERLY_PUBLICATION, Applicability()),
        "command.table.extract": CommandSpec(MethodRef("stratbox.domains.minfin.methods.budget:extract"), FED_QUARTERLY_TABLE, Applicability(source_ids={"minfin.fedbud.annex3.quarterly"})),
        "command.table.interpret": CommandSpec(MethodRef("stratbox.domains.minfin.methods.budget:interpret"), FED_QUARTERLY_TABLE, Applicability(source_ids={"minfin.fedbud.annex3.quarterly"})),
        "command.observations.validate": CommandSpec(MethodRef("stratbox.domains.minfin.methods.budget:validate"), FED_QUARTERLY_TABLE, Applicability(source_ids={"minfin.fedbud.annex3.quarterly"})),
        "command.observations.align": CommandSpec(MethodRef("stratbox.domains.minfin.methods.budget:align"), FED_QUARTERLY_TABLE, Applicability(source_ids={"minfin.fedbud.annex3.quarterly"})),
    },
)

FED_ANNUAL_PUBLICATION = SourceRules("minfin.fedbud.annex3.annual", "minfin.fedbud", FEDERAL_INDEX, FEDERAL_ASSETS[2], FEDERAL_ASSETS, "annual", "annual")
FED_ANNUAL_TABLE = TableRules("minfin.fedbud.annex3.annual", "minfin.fedbud", "annual", "annual", "russian_federal_budget", BUDGET_ROWS)
FED_ANNUAL = SeriesSpec(
    id="minfin.fedbud.annex3.annual",
    publication=PublicationSpec("minfin.fedbud.annex3.annual", "Federal budget, annex 3: annual", FEDERAL_INDEX, frozenset({"xlsx"}), "annual", settings=FED_ANNUAL_PUBLICATION),
    semantics=ObservationSemantics(("metric", "subject", "period", "perimeter"), "annual", "flow", "RUB", FED_ANNUAL_TABLE),
    commands={
        "command.request.prepare": CommandSpec(MethodRef("stratbox.domains.minfin.methods.publications:prepare_request"), FED_ANNUAL_PUBLICATION, Applicability()),
        "command.publication.scan": CommandSpec(MethodRef("stratbox.domains.minfin.methods.publications:scan"), FED_ANNUAL_PUBLICATION, Applicability()),
        "command.issue.select": CommandSpec(MethodRef("stratbox.domains.minfin.methods.publications:select"), FED_ANNUAL_PUBLICATION, Applicability()),
        "command.source.assess": CommandSpec(MethodRef("stratbox.domains.minfin.methods.publications:assess"), FED_ANNUAL_PUBLICATION, Applicability()),
        "command.table.extract": CommandSpec(MethodRef("stratbox.domains.minfin.methods.budget:extract"), FED_ANNUAL_TABLE, Applicability(source_ids={"minfin.fedbud.annex3.annual"})),
        "command.table.interpret": CommandSpec(MethodRef("stratbox.domains.minfin.methods.budget:interpret"), FED_ANNUAL_TABLE, Applicability(source_ids={"minfin.fedbud.annex3.annual"})),
        "command.observations.validate": CommandSpec(MethodRef("stratbox.domains.minfin.methods.budget:validate"), FED_ANNUAL_TABLE, Applicability(source_ids={"minfin.fedbud.annex3.annual"})),
        "command.observations.align": CommandSpec(MethodRef("stratbox.domains.minfin.methods.budget:align"), FED_ANNUAL_TABLE, Applicability(source_ids={"minfin.fedbud.annex3.annual"})),
    },
)

