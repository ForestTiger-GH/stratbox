"""The single immutable Frank RG domain catalog; no operation generation."""
from stratbox.capabilities.model.domains import DomainSpec
from .common.delivery import DELIVERED_REPORTS
from .common.recognition import RULES
from .series.express import (FRG_EXPRESS_ISSUANCE, FRG_EXPRESS_ISSUANCE_CARDS, FRG_EXPRESS_ISSUANCE_WEEKLY, FRG_EXPRESS_PASSIVES, FRG_EXPRESS_PORTFOLIOS)
from .series.rbm import (FRG_RBM_PORTFOLIOS_Q, FRG_RBM_VOLUMES_CARDS_Q, FRG_RBM_VOLUMES_Q)
from .series.regional import (FRG_REGIONAL_ISSUANCE, FRG_REGIONAL_ISSUANCE_CARDS, FRG_REGIONAL_ISSUANCE_MORTGAGE, FRG_REGIONAL_PORTFOLIOS, FRG_REGIONAL_PORTFOLIOS_MORTGAGE)
from .series.special import (FRG_SPECIAL_MORTGAGE_REFINANCING)

DOMAIN = DomainSpec(id="frank_rg",
    common={"publications": {DELIVERED_REPORTS.id: DELIVERED_REPORTS}, "name_rules": RULES,
        "scientific_obligations": {
            "publisher_layouts": "All fourteen delivered identities are known; reviewed built-in business cell maps require retained publisher workbooks.",
            "cross_period_methods": "Filename periods, weekly issue markers and Q labels do not define numerical observation frequency or accumulation.",
            "source_delivery": "FileStore inventories and supplied bytes are supported; no automatic publisher website acquisition is claimed.",
        }},
    series={
        FRG_EXPRESS_ISSUANCE.id: FRG_EXPRESS_ISSUANCE,
        FRG_EXPRESS_ISSUANCE_CARDS.id: FRG_EXPRESS_ISSUANCE_CARDS,
        FRG_EXPRESS_ISSUANCE_WEEKLY.id: FRG_EXPRESS_ISSUANCE_WEEKLY,
        FRG_EXPRESS_PASSIVES.id: FRG_EXPRESS_PASSIVES,
        FRG_EXPRESS_PORTFOLIOS.id: FRG_EXPRESS_PORTFOLIOS,
        FRG_RBM_PORTFOLIOS_Q.id: FRG_RBM_PORTFOLIOS_Q,
        FRG_RBM_VOLUMES_CARDS_Q.id: FRG_RBM_VOLUMES_CARDS_Q,
        FRG_RBM_VOLUMES_Q.id: FRG_RBM_VOLUMES_Q,
        FRG_REGIONAL_ISSUANCE.id: FRG_REGIONAL_ISSUANCE,
        FRG_REGIONAL_ISSUANCE_CARDS.id: FRG_REGIONAL_ISSUANCE_CARDS,
        FRG_REGIONAL_ISSUANCE_MORTGAGE.id: FRG_REGIONAL_ISSUANCE_MORTGAGE,
        FRG_REGIONAL_PORTFOLIOS.id: FRG_REGIONAL_PORTFOLIOS,
        FRG_REGIONAL_PORTFOLIOS_MORTGAGE.id: FRG_REGIONAL_PORTFOLIOS_MORTGAGE,
        FRG_SPECIAL_MORTGAGE_REFINANCING.id: FRG_SPECIAL_MORTGAGE_REFINANCING,
    }, calculations={}, products={})
