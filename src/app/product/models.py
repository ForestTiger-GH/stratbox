"""Compatibility facade for product-layer models.

Canonical modules live under:
- app.product.catalog.models
- app.product.forms.models
- app.product.execution.requests
"""

from app.product.catalog.models import ProductOperationSpec, ProductRegistry
from app.product.execution.requests import ProductLaunchRequest, ProductOperationContext, ProductResult
from app.product.forms.models import FieldSection, ParamType, ProductParamSpec

__all__ = [
    'FieldSection',
    'ParamType',
    'ProductLaunchRequest',
    'ProductOperationContext',
    'ProductOperationSpec',
    'ProductParamSpec',
    'ProductRegistry',
    'ProductResult',
]
