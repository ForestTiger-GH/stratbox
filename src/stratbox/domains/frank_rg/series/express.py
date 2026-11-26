"""Explicit continuing report declarations; business-layout gaps stay visible."""
from stratbox.capabilities.model.domains import Applicability, CommandSpec, ObservationSemantics, SeriesSpec
from stratbox.capabilities.model.methods import MethodRef
from ..common.delivery import DELIVERED_REPORTS
from ..methods.publications import DeliverySettings
from ..methods.tables import TableRules

FRG_EXPRESS_ISSUANCE_DELIVERY = DeliverySettings('frg.express.issuance')
FRG_EXPRESS_ISSUANCE_TABLES = TableRules('frg.express.issuance')
FRG_EXPRESS_ISSUANCE = SeriesSpec(id='frg.express.issuance', publication=DELIVERED_REPORTS,
    semantics=ObservationSemantics(("metric", "subject_namespace", "subject", "period", "frequency", "perimeter"),
        "Explicit table-declared economic periods; filename identifies the publication only",
        settings={"title": 'Loan issuance', "reviewed_business_layout": False}),
    commands={
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:scan"),
            FRG_EXPRESS_ISSUANCE_DELIVERY, Applicability(source_ids=frozenset({'frg.express.issuance'}))),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:select"),
            FRG_EXPRESS_ISSUANCE_DELIVERY, Applicability(source_ids=frozenset({'frg.express.issuance'}))),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:assess"),
            FRG_EXPRESS_ISSUANCE_DELIVERY, Applicability(source_ids=frozenset({'frg.express.issuance'}))),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:identify"),
            FRG_EXPRESS_ISSUANCE_DELIVERY, Applicability(source_ids=frozenset({'frg.express.issuance'}))),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:extract"),
            FRG_EXPRESS_ISSUANCE_TABLES, Applicability(source_ids=frozenset({'frg.express.issuance'}))),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:interpret"),
            FRG_EXPRESS_ISSUANCE_TABLES, Applicability(source_ids=frozenset({'frg.express.issuance'}))),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:validate"),
            FRG_EXPRESS_ISSUANCE_TABLES, Applicability(source_ids=frozenset({'frg.express.issuance'}))),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:align"),
            FRG_EXPRESS_ISSUANCE_TABLES, Applicability(source_ids=frozenset({'frg.express.issuance'}))),
    })

FRG_EXPRESS_ISSUANCE_CARDS_DELIVERY = DeliverySettings('frg.express.issuance_cards')
FRG_EXPRESS_ISSUANCE_CARDS_TABLES = TableRules('frg.express.issuance_cards')
FRG_EXPRESS_ISSUANCE_CARDS = SeriesSpec(id='frg.express.issuance_cards', publication=DELIVERED_REPORTS,
    semantics=ObservationSemantics(("metric", "subject_namespace", "subject", "period", "frequency", "perimeter"),
        "Explicit table-declared economic periods; filename identifies the publication only",
        settings={"title": 'Credit card issuance', "reviewed_business_layout": False}),
    commands={
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:scan"),
            FRG_EXPRESS_ISSUANCE_CARDS_DELIVERY, Applicability(source_ids=frozenset({'frg.express.issuance_cards'}))),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:select"),
            FRG_EXPRESS_ISSUANCE_CARDS_DELIVERY, Applicability(source_ids=frozenset({'frg.express.issuance_cards'}))),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:assess"),
            FRG_EXPRESS_ISSUANCE_CARDS_DELIVERY, Applicability(source_ids=frozenset({'frg.express.issuance_cards'}))),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:identify"),
            FRG_EXPRESS_ISSUANCE_CARDS_DELIVERY, Applicability(source_ids=frozenset({'frg.express.issuance_cards'}))),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:extract"),
            FRG_EXPRESS_ISSUANCE_CARDS_TABLES, Applicability(source_ids=frozenset({'frg.express.issuance_cards'}))),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:interpret"),
            FRG_EXPRESS_ISSUANCE_CARDS_TABLES, Applicability(source_ids=frozenset({'frg.express.issuance_cards'}))),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:validate"),
            FRG_EXPRESS_ISSUANCE_CARDS_TABLES, Applicability(source_ids=frozenset({'frg.express.issuance_cards'}))),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:align"),
            FRG_EXPRESS_ISSUANCE_CARDS_TABLES, Applicability(source_ids=frozenset({'frg.express.issuance_cards'}))),
    })

FRG_EXPRESS_ISSUANCE_WEEKLY_DELIVERY = DeliverySettings('frg.express.issuance_weekly')
FRG_EXPRESS_ISSUANCE_WEEKLY_TABLES = TableRules('frg.express.issuance_weekly')
FRG_EXPRESS_ISSUANCE_WEEKLY = SeriesSpec(id='frg.express.issuance_weekly', publication=DELIVERED_REPORTS,
    semantics=ObservationSemantics(("metric", "subject_namespace", "subject", "period", "frequency", "perimeter"),
        "Explicit table-declared economic periods; filename identifies the publication only",
        settings={"title": 'Weekly loan issuance', "reviewed_business_layout": False}),
    commands={
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:scan"),
            FRG_EXPRESS_ISSUANCE_WEEKLY_DELIVERY, Applicability(source_ids=frozenset({'frg.express.issuance_weekly'}))),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:select"),
            FRG_EXPRESS_ISSUANCE_WEEKLY_DELIVERY, Applicability(source_ids=frozenset({'frg.express.issuance_weekly'}))),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:assess"),
            FRG_EXPRESS_ISSUANCE_WEEKLY_DELIVERY, Applicability(source_ids=frozenset({'frg.express.issuance_weekly'}))),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:identify"),
            FRG_EXPRESS_ISSUANCE_WEEKLY_DELIVERY, Applicability(source_ids=frozenset({'frg.express.issuance_weekly'}))),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:extract"),
            FRG_EXPRESS_ISSUANCE_WEEKLY_TABLES, Applicability(source_ids=frozenset({'frg.express.issuance_weekly'}))),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:interpret"),
            FRG_EXPRESS_ISSUANCE_WEEKLY_TABLES, Applicability(source_ids=frozenset({'frg.express.issuance_weekly'}))),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:validate"),
            FRG_EXPRESS_ISSUANCE_WEEKLY_TABLES, Applicability(source_ids=frozenset({'frg.express.issuance_weekly'}))),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:align"),
            FRG_EXPRESS_ISSUANCE_WEEKLY_TABLES, Applicability(source_ids=frozenset({'frg.express.issuance_weekly'}))),
    })

FRG_EXPRESS_PASSIVES_DELIVERY = DeliverySettings('frg.express.passives')
FRG_EXPRESS_PASSIVES_TABLES = TableRules('frg.express.passives')
FRG_EXPRESS_PASSIVES = SeriesSpec(id='frg.express.passives', publication=DELIVERED_REPORTS,
    semantics=ObservationSemantics(("metric", "subject_namespace", "subject", "period", "frequency", "perimeter"),
        "Explicit table-declared economic periods; filename identifies the publication only",
        settings={"title": 'Retail liabilities', "reviewed_business_layout": False}),
    commands={
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:scan"),
            FRG_EXPRESS_PASSIVES_DELIVERY, Applicability(source_ids=frozenset({'frg.express.passives'}))),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:select"),
            FRG_EXPRESS_PASSIVES_DELIVERY, Applicability(source_ids=frozenset({'frg.express.passives'}))),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:assess"),
            FRG_EXPRESS_PASSIVES_DELIVERY, Applicability(source_ids=frozenset({'frg.express.passives'}))),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:identify"),
            FRG_EXPRESS_PASSIVES_DELIVERY, Applicability(source_ids=frozenset({'frg.express.passives'}))),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:extract"),
            FRG_EXPRESS_PASSIVES_TABLES, Applicability(source_ids=frozenset({'frg.express.passives'}))),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:interpret"),
            FRG_EXPRESS_PASSIVES_TABLES, Applicability(source_ids=frozenset({'frg.express.passives'}))),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:validate"),
            FRG_EXPRESS_PASSIVES_TABLES, Applicability(source_ids=frozenset({'frg.express.passives'}))),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:align"),
            FRG_EXPRESS_PASSIVES_TABLES, Applicability(source_ids=frozenset({'frg.express.passives'}))),
    })

FRG_EXPRESS_PORTFOLIOS_DELIVERY = DeliverySettings('frg.express.portfolios')
FRG_EXPRESS_PORTFOLIOS_TABLES = TableRules('frg.express.portfolios')
FRG_EXPRESS_PORTFOLIOS = SeriesSpec(id='frg.express.portfolios', publication=DELIVERED_REPORTS,
    semantics=ObservationSemantics(("metric", "subject_namespace", "subject", "period", "frequency", "perimeter"),
        "Explicit table-declared economic periods; filename identifies the publication only",
        settings={"title": 'Loan portfolios', "reviewed_business_layout": False}),
    commands={
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:scan"),
            FRG_EXPRESS_PORTFOLIOS_DELIVERY, Applicability(source_ids=frozenset({'frg.express.portfolios'}))),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:select"),
            FRG_EXPRESS_PORTFOLIOS_DELIVERY, Applicability(source_ids=frozenset({'frg.express.portfolios'}))),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:assess"),
            FRG_EXPRESS_PORTFOLIOS_DELIVERY, Applicability(source_ids=frozenset({'frg.express.portfolios'}))),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:identify"),
            FRG_EXPRESS_PORTFOLIOS_DELIVERY, Applicability(source_ids=frozenset({'frg.express.portfolios'}))),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:extract"),
            FRG_EXPRESS_PORTFOLIOS_TABLES, Applicability(source_ids=frozenset({'frg.express.portfolios'}))),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:interpret"),
            FRG_EXPRESS_PORTFOLIOS_TABLES, Applicability(source_ids=frozenset({'frg.express.portfolios'}))),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:validate"),
            FRG_EXPRESS_PORTFOLIOS_TABLES, Applicability(source_ids=frozenset({'frg.express.portfolios'}))),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:align"),
            FRG_EXPRESS_PORTFOLIOS_TABLES, Applicability(source_ids=frozenset({'frg.express.portfolios'}))),
    })
