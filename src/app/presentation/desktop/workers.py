from __future__ import annotations

from typing import Any

from PySide6.QtCore import QObject, Signal, Slot

from app.runtime.context import AppContext
from app.application.product.catalog.models import ProductOperationSpec
from app.application.product.execution.requests import ProductResult
from app.application.product.execution.runner import run_product_operation


class ProductWorker(QObject):
    finished = Signal(object)

    def __init__(self, *, spec: ProductOperationSpec, context: AppContext, params: dict[str, Any]):
        super().__init__()
        self._spec = spec
        self._context = context
        self._params = params

    @Slot()
    def run(self) -> None:
        try:
            result: ProductResult = run_product_operation(self._spec, context=self._context, params=self._params)
        except Exception as exc:  # pragma: no cover - defensive boundary
            self._context.logger.exception('Unhandled worker failure: %s', self._spec.id)
            result = ProductResult(
                ok=False,
                message=f'Unhandled worker failure: {exc}',
                outputs=tuple(),
                details={'error': str(exc), 'operation_id': self._spec.id},
            )
        self.finished.emit(result)
