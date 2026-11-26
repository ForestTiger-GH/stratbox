"""The complete static FNS catalog; no registration or assembly side effects."""
from stratbox.capabilities.model.domains import DomainSpec
from .common.access import ACCESS
from .common.publications import SME_PUBLICATION, LEGAL_PUBLICATION
from .series.sme import SME
from .series.legal_entities import LEGAL_ENTITIES
from .calculations.rules import STOCK_CHANGE, STOCK_SHARE
from .products.specifications import SME_REGIONAL, LEGAL_ENTITIES_REGIONAL

DOMAIN = DomainSpec(
    id="fns",
    common={ACCESS.id: ACCESS, "fns.sme.publication": SME_PUBLICATION,
            "fns.1yur.publication": LEGAL_PUBLICATION},
    series={SME.id: SME, LEGAL_ENTITIES.id: LEGAL_ENTITIES},
    calculations={STOCK_CHANGE.id: STOCK_CHANGE, STOCK_SHARE.id: STOCK_SHARE},
    products={SME_REGIONAL.id: SME_REGIONAL, LEGAL_ENTITIES_REGIONAL.id: LEGAL_ENTITIES_REGIONAL},
)
