"""Explicit continuing report declarations; business-layout gaps stay visible."""
from stratbox.capabilities.model.domains import Applicability, CommandSpec, ObservationSemantics, SeriesSpec
from stratbox.capabilities.model.methods import MethodRef
from ..common.delivery import DELIVERED_REPORTS
from ..methods.publications import DeliverySettings
from ..methods.tables import TableRules

FRG_REGIONAL_ISSUANCE_DELIVERY = DeliverySettings('frg.regional.issuance')
FRG_REGIONAL_ISSUANCE_TABLES = TableRules('frg.regional.issuance')
FRG_REGIONAL_ISSUANCE = SeriesSpec(id='frg.regional.issuance', publication=DELIVERED_REPORTS,
    semantics=ObservationSemantics(("metric", "subject_namespace", "subject", "period", "frequency", "perimeter"),
        "Explicit table-declared economic periods; filename identifies the publication only",
        settings={"title": 'Regional loan issuance', "reviewed_business_layout": False}),
    commands={
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:scan"),
            FRG_REGIONAL_ISSUANCE_DELIVERY, Applicability(source_ids=frozenset({'frg.regional.issuance'}))),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:select"),
            FRG_REGIONAL_ISSUANCE_DELIVERY, Applicability(source_ids=frozenset({'frg.regional.issuance'}))),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:assess"),
            FRG_REGIONAL_ISSUANCE_DELIVERY, Applicability(source_ids=frozenset({'frg.regional.issuance'}))),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:identify"),
            FRG_REGIONAL_ISSUANCE_DELIVERY, Applicability(source_ids=frozenset({'frg.regional.issuance'}))),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:extract"),
            FRG_REGIONAL_ISSUANCE_TABLES, Applicability(source_ids=frozenset({'frg.regional.issuance'}))),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:interpret"),
            FRG_REGIONAL_ISSUANCE_TABLES, Applicability(source_ids=frozenset({'frg.regional.issuance'}))),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:validate"),
            FRG_REGIONAL_ISSUANCE_TABLES, Applicability(source_ids=frozenset({'frg.regional.issuance'}))),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:align"),
            FRG_REGIONAL_ISSUANCE_TABLES, Applicability(source_ids=frozenset({'frg.regional.issuance'}))),
    })

FRG_REGIONAL_ISSUANCE_CARDS_DELIVERY = DeliverySettings('frg.regional.issuance_cards')
FRG_REGIONAL_ISSUANCE_CARDS_TABLES = TableRules('frg.regional.issuance_cards')
FRG_REGIONAL_ISSUANCE_CARDS = SeriesSpec(id='frg.regional.issuance_cards', publication=DELIVERED_REPORTS,
    semantics=ObservationSemantics(("metric", "subject_namespace", "subject", "period", "frequency", "perimeter"),
        "Explicit table-declared economic periods; filename identifies the publication only",
        settings={"title": 'Regional credit card issuance', "reviewed_business_layout": False}),
    commands={
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:scan"),
            FRG_REGIONAL_ISSUANCE_CARDS_DELIVERY, Applicability(source_ids=frozenset({'frg.regional.issuance_cards'}))),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:select"),
            FRG_REGIONAL_ISSUANCE_CARDS_DELIVERY, Applicability(source_ids=frozenset({'frg.regional.issuance_cards'}))),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:assess"),
            FRG_REGIONAL_ISSUANCE_CARDS_DELIVERY, Applicability(source_ids=frozenset({'frg.regional.issuance_cards'}))),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:identify"),
            FRG_REGIONAL_ISSUANCE_CARDS_DELIVERY, Applicability(source_ids=frozenset({'frg.regional.issuance_cards'}))),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:extract"),
            FRG_REGIONAL_ISSUANCE_CARDS_TABLES, Applicability(source_ids=frozenset({'frg.regional.issuance_cards'}))),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:interpret"),
            FRG_REGIONAL_ISSUANCE_CARDS_TABLES, Applicability(source_ids=frozenset({'frg.regional.issuance_cards'}))),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:validate"),
            FRG_REGIONAL_ISSUANCE_CARDS_TABLES, Applicability(source_ids=frozenset({'frg.regional.issuance_cards'}))),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:align"),
            FRG_REGIONAL_ISSUANCE_CARDS_TABLES, Applicability(source_ids=frozenset({'frg.regional.issuance_cards'}))),
    })

FRG_REGIONAL_ISSUANCE_MORTGAGE_DELIVERY = DeliverySettings('frg.regional.issuance_mortgage')
FRG_REGIONAL_ISSUANCE_MORTGAGE_TABLES = TableRules('frg.regional.issuance_mortgage')
FRG_REGIONAL_ISSUANCE_MORTGAGE = SeriesSpec(id='frg.regional.issuance_mortgage', publication=DELIVERED_REPORTS,
    semantics=ObservationSemantics(("metric", "subject_namespace", "subject", "period", "frequency", "perimeter"),
        "Explicit table-declared economic periods; filename identifies the publication only",
        settings={"title": 'Regional mortgage issuance', "reviewed_business_layout": False}),
    commands={
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:scan"),
            FRG_REGIONAL_ISSUANCE_MORTGAGE_DELIVERY, Applicability(source_ids=frozenset({'frg.regional.issuance_mortgage'}))),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:select"),
            FRG_REGIONAL_ISSUANCE_MORTGAGE_DELIVERY, Applicability(source_ids=frozenset({'frg.regional.issuance_mortgage'}))),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:assess"),
            FRG_REGIONAL_ISSUANCE_MORTGAGE_DELIVERY, Applicability(source_ids=frozenset({'frg.regional.issuance_mortgage'}))),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:identify"),
            FRG_REGIONAL_ISSUANCE_MORTGAGE_DELIVERY, Applicability(source_ids=frozenset({'frg.regional.issuance_mortgage'}))),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:extract"),
            FRG_REGIONAL_ISSUANCE_MORTGAGE_TABLES, Applicability(source_ids=frozenset({'frg.regional.issuance_mortgage'}))),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:interpret"),
            FRG_REGIONAL_ISSUANCE_MORTGAGE_TABLES, Applicability(source_ids=frozenset({'frg.regional.issuance_mortgage'}))),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:validate"),
            FRG_REGIONAL_ISSUANCE_MORTGAGE_TABLES, Applicability(source_ids=frozenset({'frg.regional.issuance_mortgage'}))),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:align"),
            FRG_REGIONAL_ISSUANCE_MORTGAGE_TABLES, Applicability(source_ids=frozenset({'frg.regional.issuance_mortgage'}))),
    })

FRG_REGIONAL_PORTFOLIOS_DELIVERY = DeliverySettings('frg.regional.portfolios')
FRG_REGIONAL_PORTFOLIOS_TABLES = TableRules('frg.regional.portfolios')
FRG_REGIONAL_PORTFOLIOS = SeriesSpec(id='frg.regional.portfolios', publication=DELIVERED_REPORTS,
    semantics=ObservationSemantics(("metric", "subject_namespace", "subject", "period", "frequency", "perimeter"),
        "Explicit table-declared economic periods; filename identifies the publication only",
        settings={"title": 'Regional loan portfolios', "reviewed_business_layout": False}),
    commands={
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:scan"),
            FRG_REGIONAL_PORTFOLIOS_DELIVERY, Applicability(source_ids=frozenset({'frg.regional.portfolios'}))),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:select"),
            FRG_REGIONAL_PORTFOLIOS_DELIVERY, Applicability(source_ids=frozenset({'frg.regional.portfolios'}))),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:assess"),
            FRG_REGIONAL_PORTFOLIOS_DELIVERY, Applicability(source_ids=frozenset({'frg.regional.portfolios'}))),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:identify"),
            FRG_REGIONAL_PORTFOLIOS_DELIVERY, Applicability(source_ids=frozenset({'frg.regional.portfolios'}))),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:extract"),
            FRG_REGIONAL_PORTFOLIOS_TABLES, Applicability(source_ids=frozenset({'frg.regional.portfolios'}))),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:interpret"),
            FRG_REGIONAL_PORTFOLIOS_TABLES, Applicability(source_ids=frozenset({'frg.regional.portfolios'}))),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:validate"),
            FRG_REGIONAL_PORTFOLIOS_TABLES, Applicability(source_ids=frozenset({'frg.regional.portfolios'}))),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:align"),
            FRG_REGIONAL_PORTFOLIOS_TABLES, Applicability(source_ids=frozenset({'frg.regional.portfolios'}))),
    })

FRG_REGIONAL_PORTFOLIOS_MORTGAGE_DELIVERY = DeliverySettings('frg.regional.portfolios_mortgage')
FRG_REGIONAL_PORTFOLIOS_MORTGAGE_TABLES = TableRules('frg.regional.portfolios_mortgage')
FRG_REGIONAL_PORTFOLIOS_MORTGAGE = SeriesSpec(id='frg.regional.portfolios_mortgage', publication=DELIVERED_REPORTS,
    semantics=ObservationSemantics(("metric", "subject_namespace", "subject", "period", "frequency", "perimeter"),
        "Explicit table-declared economic periods; filename identifies the publication only",
        settings={"title": 'Regional mortgage portfolios', "reviewed_business_layout": False}),
    commands={
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:scan"),
            FRG_REGIONAL_PORTFOLIOS_MORTGAGE_DELIVERY, Applicability(source_ids=frozenset({'frg.regional.portfolios_mortgage'}))),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:select"),
            FRG_REGIONAL_PORTFOLIOS_MORTGAGE_DELIVERY, Applicability(source_ids=frozenset({'frg.regional.portfolios_mortgage'}))),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:assess"),
            FRG_REGIONAL_PORTFOLIOS_MORTGAGE_DELIVERY, Applicability(source_ids=frozenset({'frg.regional.portfolios_mortgage'}))),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:identify"),
            FRG_REGIONAL_PORTFOLIOS_MORTGAGE_DELIVERY, Applicability(source_ids=frozenset({'frg.regional.portfolios_mortgage'}))),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:extract"),
            FRG_REGIONAL_PORTFOLIOS_MORTGAGE_TABLES, Applicability(source_ids=frozenset({'frg.regional.portfolios_mortgage'}))),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:interpret"),
            FRG_REGIONAL_PORTFOLIOS_MORTGAGE_TABLES, Applicability(source_ids=frozenset({'frg.regional.portfolios_mortgage'}))),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:validate"),
            FRG_REGIONAL_PORTFOLIOS_MORTGAGE_TABLES, Applicability(source_ids=frozenset({'frg.regional.portfolios_mortgage'}))),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:align"),
            FRG_REGIONAL_PORTFOLIOS_MORTGAGE_TABLES, Applicability(source_ids=frozenset({'frg.regional.portfolios_mortgage'}))),
    })
