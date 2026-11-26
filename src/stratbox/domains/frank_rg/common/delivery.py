"""Caller-selected delivered reports; no automatic publisher web download."""
from stratbox.capabilities.model.domains import Applicability, CommandSpec, PublicationSpec
from stratbox.capabilities.model.methods import MethodRef
from ..methods.publications import DeliverySettings

DELIVERY = DeliverySettings()
DELIVERED_REPORTS = PublicationSpec(
    id="frank_rg.delivered_reports",
    title="Delivered Frank RG workbooks",
    formats=frozenset({"xlsx", "xlsm", "xls", "xlsb"}),
    issue_model="dated", publisher_id="frank_rg", delivery_mode="delivered_inventory",
    artifact_category="workbook", family_ids=("frank_rg.delivered_reports",), settings=DELIVERY,
    commands={
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:scan"), DELIVERY, Applicability()),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:select"), DELIVERY, Applicability()),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:assess"), DELIVERY, Applicability()),
    },
)
