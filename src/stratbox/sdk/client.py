"""A thin facade over the canonical catalogs, compiler and execution session."""
from __future__ import annotations

from dataclasses import replace
from threading import RLock
from collections.abc import Mapping

from stratbox.core.execution.contracts import ExecutionContext
from stratbox.core.runtime.capabilities import CapabilityRequirement, ProviderBinding


def _context(context, providers):
    context = context or ExecutionContext()
    if providers is None:
        return context
    from stratbox.core.runtime.providers import Providers
    if isinstance(providers, Providers):
        providers = {
            "http": providers.http, "filestore": providers.filestore,
            "output_filestore": providers.filestore, "secrets": providers.secrets,
        }
    if not isinstance(providers, Mapping):
        raise TypeError("sdk.providers_mapping_required")
    bindings = list(context.bindings)
    existing = {binding.capability.role for binding in bindings}
    for role, provider in providers.items():
        if role in existing:
            raise ValueError("sdk.provider_conflict")
        if isinstance(provider, ProviderBinding):
            if provider.capability.role != role:
                raise ValueError("sdk.provider_role_mismatch")
            bindings.append(provider)
        else:
            bindings.append(ProviderBinding("sdk", CapabilityRequirement(role), "ready", provider))
    return replace(context, bindings=tuple(bindings))


class SourceAPI:
    """Source discovery and supplied workflows share one canonical catalog."""

    def __init__(self, operations):
        self.operations = operations
        self.catalog = operations.source_catalog()

    def source(self, series_id):
        return self.catalog.source(series_id)

    def select(self, **filters):
        return self.catalog.select(**filters)

    def describe(self, series_id, **options):
        return self.catalog.describe(series_id, operations=self.operations, **options)

    def bind(self, series_id, **options):
        return self.operations.bind_source(series_id, **options)

    def workflow(self, series_id, **options):
        from stratbox.composition.builtins import source_workflow
        options.setdefault("catalog", self.operations)
        return source_workflow(series_id, **options)


class StrategyBox:
    """Own one execution session for scripts, notebooks and application hosts.

    Catalog discovery does not start workers. A submitted run retains its
    qualified operation results; ``invoke`` returns the same graph result as
    ``run``. User-provided adapters remain owned by the caller.
    """

    def __init__(self, *, settings=None, providers=None, context=None, catalog=None,
                 observer=None, result_resolver=None, operation_options=None):
        from stratbox.operations import operation_catalog
        from stratbox.core.execution.session import ExecutionSettings
        self.operations = catalog if catalog is not None else operation_catalog()
        self.sources = SourceAPI(self.operations)
        self.settings = settings if settings is not None else ExecutionSettings()
        self.context = _context(context, providers)
        self.observer = observer
        self.result_resolver = result_resolver
        self.operation_options = dict(operation_options or {})
        self._session = None
        self._closed = False
        self._lock = RLock()

    def _check_open(self):
        if self._closed:
            raise RuntimeError("sdk.closed")

    @property
    def session(self):
        with self._lock:
            self._check_open()
            if self._session is None:
                from stratbox.core.execution.session import ExecutionSession
                options = {"context": self.context, "observer": self.observer,
                           "result_resolver": self.result_resolver,
                           "operation_options": self.operation_options}
                if self.settings is not None:
                    options["settings"] = self.settings
                self._session = ExecutionSession(self.operations, **options)
            return self._session

    def compile(self, definition, *, inputs=None, parameters=None, outputs=None):
        from stratbox.composition import compile_workflow
        self._check_open()
        return compile_workflow(definition, self.operations, inputs=inputs,
                                parameters=parameters, outputs=outputs)

    def submit(self, definition, *, inputs=None, parameters=None, outputs=None):
        from stratbox.composition import ExecutionPlan
        self._check_open()
        if isinstance(definition, ExecutionPlan):
            if inputs is not None or parameters is not None or outputs is not None:
                raise ValueError("sdk.compiled_plan_already_bound")
            plan = definition
        else:
            plan = self.compile(definition, inputs=inputs, parameters=parameters, outputs=outputs)
        return self.session.submit(plan)

    def run(self, definition, *, inputs=None, parameters=None, outputs=None, timeout=None):
        return self.submit(definition, inputs=inputs, parameters=parameters,
                           outputs=outputs).result(timeout)

    def workflow(self, operation_id, *, inputs=None, parameters=None):
        """Bind a callable capability as a reusable explicit scenario."""
        from stratbox.composition import OperationStep, PlanOutputRef, ScenarioDefinition
        from stratbox.composition.builtins import expand_operation
        self._check_open()
        call = self.operations.bind(operation_id, inputs=inputs, parameters=parameters)
        workflow = expand_operation(operation_id, call.request)
        if workflow is None:
            processing = call.definition.processing
            outputs = {port.name: PlanOutputRef("call", port.name)
                       for port in processing.outputs} if processing else {}
            workflow = ScenarioDefinition("invoke", (
                OperationStep("call", operation_id, inputs=inputs or {}, parameters=parameters or {}),
            ), outputs=outputs)
        return workflow

    def invoke(self, operation_id, *, inputs=None, parameters=None, timeout=None):
        """Compile an operation or expand its supplied composition, then run it."""
        return self.run(self.workflow(operation_id, inputs=inputs, parameters=parameters),
                        timeout=timeout)

    def close(self, *, wait=True, cancel=False):
        with self._lock:
            if self._closed:
                return
            self._closed = True
            session = self._session
        if session is not None:
            session.close(wait=wait, cancel=cancel)

    def __enter__(self):
        self._check_open()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close(cancel=exc_type is not None)
