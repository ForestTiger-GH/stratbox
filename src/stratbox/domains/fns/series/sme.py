"""The one continuing SME statistical table, specialized action by action."""
from stratbox.capabilities.model.domains import Applicability, CommandSpec, ObservationSemantics, PublicationSpec, SeriesSpec
from stratbox.capabilities.model.methods import MethodRef
from ..common.publications import SME_PUBLICATION
from ..common.semantics import SME_RULES

SME = SeriesSpec(
    id="fns.sme",
    publication=PublicationSpec("fns.sme", "Unified SME register statistics",
        SME_PUBLICATION.index_url, frozenset({"json"}), "monthly", settings=SME_PUBLICATION),
    semantics=ObservationSemantics(("subject_namespace", "subject", "metric", "period", "perimeter"),
        "stock_at_published_date", "stock", "count", SME_RULES),
    commands={
        "command.request.prepare": CommandSpec(MethodRef("stratbox.domains.fns.methods.publications:prepare_request"),
            SME_PUBLICATION, Applicability(date_from=SME_PUBLICATION.earliest)),
        "command.publication.scan": CommandSpec(MethodRef("stratbox.domains.fns.methods.publications:scan_sme"),
            SME_PUBLICATION, Applicability(formats={"html"})),
        "command.issue.select": CommandSpec(MethodRef("stratbox.domains.fns.methods.publications:select_issue"),
            SME_PUBLICATION, Applicability()),
        "command.source.assess": CommandSpec(MethodRef("stratbox.domains.fns.methods.publications:assess"),
            SME_PUBLICATION, Applicability()),
        "command.table.extract": CommandSpec(MethodRef("stratbox.domains.fns.methods.sme:select_records"),
            SME_RULES, Applicability(formats={"json"}, source_ids={"fns.sme"})),
        "command.table.interpret": CommandSpec(MethodRef("stratbox.domains.fns.methods.sme:interpret_counters"),
            SME_RULES, Applicability(source_ids={"fns.sme"})),
        "command.observations.validate": CommandSpec(MethodRef("stratbox.domains.fns.methods.validation:validate"),
            SME_RULES, Applicability(source_ids={"fns.sme"})),
        "command.observations.align": CommandSpec(MethodRef("stratbox.domains.fns.methods.sme:align_observations"),
            SME_RULES, Applicability(source_ids={"fns.sme"})),
    },
)
