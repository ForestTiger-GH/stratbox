"""Continuing Form 1-YUR; historical source rules are ordinary shared data."""
from stratbox.capabilities.model.domains import Applicability, CommandSpec, ObservationSemantics, PublicationSpec, SeriesSpec
from stratbox.capabilities.model.methods import MethodRef
from ..common.publications import LEGAL_PUBLICATION
from ..common.semantics import LEGAL_RULES

LEGAL_ENTITIES = SeriesSpec(
    id="fns.1yur",
    publication=PublicationSpec("fns.1yur", "Form 1-YUR legal entities and registration statistics",
        LEGAL_PUBLICATION.index_url, frozenset({"xls", "xlsx", "zip", "rar"}), "monthly", settings=LEGAL_PUBLICATION),
    semantics=ObservationSemantics(("subject", "metric", "period", "perimeter", "legal_kind"),
        "metric_specific_stock_flow_or_unresolved", units="count", settings=LEGAL_RULES),
    commands={
        "command.request.prepare": CommandSpec(MethodRef("stratbox.domains.fns.methods.publications:prepare_request"),
            LEGAL_PUBLICATION, Applicability(date_from=LEGAL_PUBLICATION.earliest)),
        "command.publication.scan": CommandSpec(MethodRef("stratbox.domains.fns.methods.publications:scan_legal"),
            LEGAL_PUBLICATION, Applicability(formats={"html"})),
        "command.issue.select": CommandSpec(MethodRef("stratbox.domains.fns.methods.publications:select_issue"),
            LEGAL_PUBLICATION, Applicability()),
        "command.source.assess": CommandSpec(MethodRef("stratbox.domains.fns.methods.publications:assess"),
            LEGAL_PUBLICATION, Applicability()),
        "command.table.extract": CommandSpec(MethodRef("stratbox.domains.fns.methods.legal_entities:select_tables"),
            LEGAL_RULES, Applicability(source_ids={"fns.1yur"})),
        "command.table.interpret": CommandSpec(MethodRef("stratbox.domains.fns.methods.legal_entities:interpret"),
            LEGAL_RULES, Applicability(source_ids={"fns.1yur"})),
        "command.observations.validate": CommandSpec(MethodRef("stratbox.domains.fns.methods.validation:validate"),
            LEGAL_RULES, Applicability(source_ids={"fns.1yur"})),
        "command.observations.align": CommandSpec(MethodRef("stratbox.domains.fns.methods.legal_entities:align"),
            LEGAL_RULES, Applicability(source_ids={"fns.1yur"})),
    },
)
