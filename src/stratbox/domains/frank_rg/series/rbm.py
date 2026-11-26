"""Explicit continuing report declarations; business-layout gaps stay visible."""
from stratbox.capabilities.model.domains import Applicability, CommandSpec, ObservationSemantics, SeriesSpec
from stratbox.capabilities.model.methods import MethodRef
from ..common.delivery import DELIVERED_REPORTS
from ..methods.publications import DeliverySettings
from ..methods.tables import TableRules

FRG_RBM_PORTFOLIOS_Q_DELIVERY = DeliverySettings('frg.rbm.portfolios_q')
FRG_RBM_PORTFOLIOS_Q_TABLES = TableRules('frg.rbm.portfolios_q')
FRG_RBM_PORTFOLIOS_Q = SeriesSpec(id='frg.rbm.portfolios_q', publication=DELIVERED_REPORTS,
    semantics=ObservationSemantics(("metric", "subject_namespace", "subject", "period", "frequency", "perimeter"),
        "Explicit table-declared economic periods; filename identifies the publication only",
        settings={"title": 'Loan portfolios with Q marker', "reviewed_business_layout": False}),
    commands={
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:scan"),
            FRG_RBM_PORTFOLIOS_Q_DELIVERY, Applicability(source_ids=frozenset({'frg.rbm.portfolios_q'}))),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:select"),
            FRG_RBM_PORTFOLIOS_Q_DELIVERY, Applicability(source_ids=frozenset({'frg.rbm.portfolios_q'}))),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:assess"),
            FRG_RBM_PORTFOLIOS_Q_DELIVERY, Applicability(source_ids=frozenset({'frg.rbm.portfolios_q'}))),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:identify"),
            FRG_RBM_PORTFOLIOS_Q_DELIVERY, Applicability(source_ids=frozenset({'frg.rbm.portfolios_q'}))),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:extract"),
            FRG_RBM_PORTFOLIOS_Q_TABLES, Applicability(source_ids=frozenset({'frg.rbm.portfolios_q'}))),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:interpret"),
            FRG_RBM_PORTFOLIOS_Q_TABLES, Applicability(source_ids=frozenset({'frg.rbm.portfolios_q'}))),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:validate"),
            FRG_RBM_PORTFOLIOS_Q_TABLES, Applicability(source_ids=frozenset({'frg.rbm.portfolios_q'}))),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:align"),
            FRG_RBM_PORTFOLIOS_Q_TABLES, Applicability(source_ids=frozenset({'frg.rbm.portfolios_q'}))),
    })

FRG_RBM_VOLUMES_CARDS_Q_DELIVERY = DeliverySettings('frg.rbm.volumes_cards_q')
FRG_RBM_VOLUMES_CARDS_Q_TABLES = TableRules('frg.rbm.volumes_cards_q')
FRG_RBM_VOLUMES_CARDS_Q = SeriesSpec(id='frg.rbm.volumes_cards_q', publication=DELIVERED_REPORTS,
    semantics=ObservationSemantics(("metric", "subject_namespace", "subject", "period", "frequency", "perimeter"),
        "Explicit table-declared economic periods; filename identifies the publication only",
        settings={"title": 'Credit card volumes with Q marker', "reviewed_business_layout": False}),
    commands={
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:scan"),
            FRG_RBM_VOLUMES_CARDS_Q_DELIVERY, Applicability(source_ids=frozenset({'frg.rbm.volumes_cards_q'}))),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:select"),
            FRG_RBM_VOLUMES_CARDS_Q_DELIVERY, Applicability(source_ids=frozenset({'frg.rbm.volumes_cards_q'}))),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:assess"),
            FRG_RBM_VOLUMES_CARDS_Q_DELIVERY, Applicability(source_ids=frozenset({'frg.rbm.volumes_cards_q'}))),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:identify"),
            FRG_RBM_VOLUMES_CARDS_Q_DELIVERY, Applicability(source_ids=frozenset({'frg.rbm.volumes_cards_q'}))),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:extract"),
            FRG_RBM_VOLUMES_CARDS_Q_TABLES, Applicability(source_ids=frozenset({'frg.rbm.volumes_cards_q'}))),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:interpret"),
            FRG_RBM_VOLUMES_CARDS_Q_TABLES, Applicability(source_ids=frozenset({'frg.rbm.volumes_cards_q'}))),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:validate"),
            FRG_RBM_VOLUMES_CARDS_Q_TABLES, Applicability(source_ids=frozenset({'frg.rbm.volumes_cards_q'}))),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:align"),
            FRG_RBM_VOLUMES_CARDS_Q_TABLES, Applicability(source_ids=frozenset({'frg.rbm.volumes_cards_q'}))),
    })

FRG_RBM_VOLUMES_Q_DELIVERY = DeliverySettings('frg.rbm.volumes_q')
FRG_RBM_VOLUMES_Q_TABLES = TableRules('frg.rbm.volumes_q')
FRG_RBM_VOLUMES_Q = SeriesSpec(id='frg.rbm.volumes_q', publication=DELIVERED_REPORTS,
    semantics=ObservationSemantics(("metric", "subject_namespace", "subject", "period", "frequency", "perimeter"),
        "Explicit table-declared economic periods; filename identifies the publication only",
        settings={"title": 'Loan volumes with Q marker', "reviewed_business_layout": False}),
    commands={
        "command.publication.scan": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:scan"),
            FRG_RBM_VOLUMES_Q_DELIVERY, Applicability(source_ids=frozenset({'frg.rbm.volumes_q'}))),
        "command.issue.select": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:select"),
            FRG_RBM_VOLUMES_Q_DELIVERY, Applicability(source_ids=frozenset({'frg.rbm.volumes_q'}))),
        "command.source.assess": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:assess"),
            FRG_RBM_VOLUMES_Q_DELIVERY, Applicability(source_ids=frozenset({'frg.rbm.volumes_q'}))),
        "command.material.identify": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.publications:identify"),
            FRG_RBM_VOLUMES_Q_DELIVERY, Applicability(source_ids=frozenset({'frg.rbm.volumes_q'}))),
        "command.table.extract": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:extract"),
            FRG_RBM_VOLUMES_Q_TABLES, Applicability(source_ids=frozenset({'frg.rbm.volumes_q'}))),
        "command.table.interpret": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:interpret"),
            FRG_RBM_VOLUMES_Q_TABLES, Applicability(source_ids=frozenset({'frg.rbm.volumes_q'}))),
        "command.observations.validate": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:validate"),
            FRG_RBM_VOLUMES_Q_TABLES, Applicability(source_ids=frozenset({'frg.rbm.volumes_q'}))),
        "command.observations.align": CommandSpec(
            MethodRef("stratbox.domains.frank_rg.methods.tables:align"),
            FRG_RBM_VOLUMES_Q_TABLES, Applicability(source_ids=frozenset({'frg.rbm.volumes_q'}))),
    })
