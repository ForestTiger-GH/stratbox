"""Explicit continuing report declarations; business-layout gaps stay visible."""
from stratbox.capabilities.model.domains import Applicability, CommandSpec, ObservationSemantics, SeriesSpec
from stratbox.capabilities.model.methods import MethodRef
from ..common.delivery import DELIVERED_REPORTS
from ..methods.publications import DeliverySettings
from ..methods.tables import TableRules

FRG_SPECIAL_MORTGAGE_REFINANCING_DELIVERY = DeliverySettings('frg.special.mortgage_refinancing')
FRG_SPECIAL_MORTGAGE_REFINANCING_TABLES = TableRules('frg.special.mortgage_refinancing')
FRG_SPECIAL_MORTGAGE_REFINANCING = SeriesSpec(id='frg.special.mortgage_refinancing', publication=DELIVERED_REPORTS,
    semantics=ObservationSemantics(("metric", "subject_namespace", "subject", "period", "frequency", "perimeter"),
        "Explicit table-declared economic periods; filename identifies the publication only",
        settings={"title": 'Mortgage refinancing', "reviewed_business_layout": False}),
    commands={
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:scan"),
            FRG_SPECIAL_MORTGAGE_REFINANCING_DELIVERY, Applicability(source_ids=frozenset({'frg.special.mortgage_refinancing'}))),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:select"),
            FRG_SPECIAL_MORTGAGE_REFINANCING_DELIVERY, Applicability(source_ids=frozenset({'frg.special.mortgage_refinancing'}))),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:assess"),
            FRG_SPECIAL_MORTGAGE_REFINANCING_DELIVERY, Applicability(source_ids=frozenset({'frg.special.mortgage_refinancing'}))),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:identify"),
            FRG_SPECIAL_MORTGAGE_REFINANCING_DELIVERY, Applicability(source_ids=frozenset({'frg.special.mortgage_refinancing'}))),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:extract"),
            FRG_SPECIAL_MORTGAGE_REFINANCING_TABLES, Applicability(source_ids=frozenset({'frg.special.mortgage_refinancing'}))),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:interpret"),
            FRG_SPECIAL_MORTGAGE_REFINANCING_TABLES, Applicability(source_ids=frozenset({'frg.special.mortgage_refinancing'}))),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:validate"),
            FRG_SPECIAL_MORTGAGE_REFINANCING_TABLES, Applicability(source_ids=frozenset({'frg.special.mortgage_refinancing'}))),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:align"),
            FRG_SPECIAL_MORTGAGE_REFINANCING_TABLES, Applicability(source_ids=frozenset({'frg.special.mortgage_refinancing'}))),
    })
