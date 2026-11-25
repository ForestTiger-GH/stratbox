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
        from stratbox.composition.source import source_workflow
        options.setdefault("catalog", self.operations)
        return source_workflow(series_id, **options)


class StrategyBox:
    """Own one execution session for scripts, notebooks and application hosts.

    Catalog discovery does not start workers. A submitted run retains its
    qualified operation results; ``invoke`` returns the same graph result as
    ``run``. User-provided adapters remain owned by the caller.
    """

    def __init__(self, *, settings=None, providers=None, context=None, catalog=None,
                 capabilities=None, observer=None, result_resolver=None, operation_options=None):
        from stratbox.operations import operation_catalog
        from stratbox.core.execution.session import ExecutionSettings
        from .bootstrap import CapabilityRuntimeCatalog, default_snapshot
        self.capabilities = capabilities if capabilities is not None else default_snapshot()
        domains = catalog if catalog is not None else operation_catalog()
        self.operations = CapabilityRuntimeCatalog(self.capabilities, domains)
        self.commands = self.capabilities.commands
        self.scenarios = self.capabilities.scenarios
        self.cascades = self.capabilities.cascades
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

    def prepare(self, capability, *, inputs=None, parameters=None, outputs=None,
                supplied_outputs=None, method_id=None, profile_id=None, group_id=None, selection=None, recipe_id=None):
        """Resolve a canonical exact invocation and its complete obligations."""
        from stratbox.composition.prepare import prepare_invocation
        self._check_open()
        from stratbox.capabilities.model import CapabilityDefinition
        if isinstance(capability, CapabilityDefinition):
            self.operations.admit_local(capability)
            self.capabilities = self.operations.snapshot
            self.commands = self.capabilities.commands
            self.scenarios = self.capabilities.scenarios
            self.cascades = self.capabilities.cascades
        return prepare_invocation(capability, self.capabilities, self.operations,
            inputs=inputs, parameters=parameters, outputs=outputs,
            supplied_outputs=supplied_outputs, method_id=method_id,
            profile_id=profile_id, group_id=group_id, selection=selection, recipe_id=recipe_id)

    def discover(self, **filters):
        """Browse one metadata projection with explicit migration readiness."""
        self._check_open()
        return self.operations.discover(**filters)

    def describe(self, capability_id):
        self._check_open()
        return self.operations.describe(capability_id)

    def prepare_goal(self, goal, **options):
        from stratbox.composition.prepare import prepare_goal
        self._check_open()
        return prepare_goal(goal, self.capabilities, self.operations, **options)

    def compile(self, definition, *, inputs=None, parameters=None, outputs=None, selection=None):
        from stratbox.composition import compile_workflow
        from stratbox.capabilities.model import CapabilityDefinition
        from stratbox.composition.requests import InvocationRequest, GoalRequest
        self._check_open()
        if isinstance(definition, GoalRequest):
            if any(value is not None for value in (inputs, parameters, outputs, selection)):
                raise ValueError("composition.request_already_bound")
            return self.prepare_goal(definition)
        if isinstance(definition, (str, CapabilityDefinition, InvocationRequest)):
            return self.prepare(definition, inputs=inputs, parameters=parameters, outputs=outputs, selection=selection)
        if selection is not None:
            raise ValueError("composition.canonical_selection_required")
        return compile_workflow(definition, self.operations, inputs=inputs,
                                parameters=parameters, outputs=outputs)

    def submit(self, definition, *, inputs=None, parameters=None, outputs=None, selection=None, execution_timeout=None):
        from stratbox.composition import ExecutionPlan
        self._check_open()
        if isinstance(definition, ExecutionPlan):
            if any(value is not None for value in (inputs, parameters, outputs, selection)):
                raise ValueError("sdk.compiled_plan_already_bound")
            plan = definition
        else:
            plan = self.compile(definition, inputs=inputs, parameters=parameters, outputs=outputs, selection=selection)
        return self.session.submit(plan, execution_timeout=execution_timeout)

    def run(self, definition, *, inputs=None, parameters=None, outputs=None, timeout=None, selection=None, execution_timeout=None):
        """Wait up to timeout; execution_timeout separately bounds the live run."""
        return self.submit(definition, inputs=inputs, parameters=parameters,
                           outputs=outputs, selection=selection, execution_timeout=execution_timeout).result(timeout)

    def workflow(self, operation_id, *, inputs=None, parameters=None):
        """Bind a callable capability as a reusable explicit scenario."""
        from stratbox.composition.requests import InvocationRequest
        self._check_open()
        try:
            self.capabilities.definition(operation_id)
        except (KeyError, ValueError):
            pass
        else:
            return InvocationRequest(operation_id, inputs=inputs or {}, parameters=parameters or {})
        from stratbox.composition import OperationStep, PlanOutputRef, ScenarioDefinition
        self._check_open()
        call = self.operations.bind(operation_id, inputs=inputs, parameters=parameters)
        processing = call.definition.processing
        outputs = {port.name: PlanOutputRef("call", port.name)
                   for port in processing.outputs} if processing else {}
        return ScenarioDefinition("invoke", (
            OperationStep("call", operation_id, inputs=inputs or {}, parameters=parameters or {}),
        ), outputs=outputs)

    def invoke(self, operation_id, *, inputs=None, parameters=None, timeout=None, execution_timeout=None,
               outputs=None, supplied_outputs=None, method_id=None, profile_id=None, group_id=None, selection=None, recipe_id=None):
        """Invoke any canonical kind through the common session service."""
        from stratbox.capabilities.model import CapabilityDefinition
        from stratbox.composition.requests import InvocationRequest, GoalRequest
        if isinstance(operation_id, GoalRequest):
            if any(value is not None for value in (inputs, parameters, outputs, supplied_outputs, method_id, profile_id, group_id, selection, recipe_id)):
                raise ValueError("composition.request_already_bound")
            return self.run(self.prepare_goal(operation_id), timeout=timeout, execution_timeout=execution_timeout)
        canonical = isinstance(operation_id, (CapabilityDefinition, InvocationRequest))
        if isinstance(operation_id, str):
            try:
                self.capabilities.definition(operation_id)
                canonical = True
            except (KeyError, ValueError):
                pass
        if canonical:
            plan = self.prepare(operation_id, inputs=inputs, parameters=parameters, outputs=outputs,
                supplied_outputs=supplied_outputs, method_id=method_id, profile_id=profile_id, group_id=group_id,
                selection=selection, recipe_id=recipe_id)
            return self.run(plan, timeout=timeout, execution_timeout=execution_timeout)
        if any(value is not None for value in (selection, recipe_id, method_id, profile_id, group_id, supplied_outputs, outputs)):
            raise ValueError("composition.canonical_binding_required")
        return self.run(self.workflow(operation_id, inputs=inputs, parameters=parameters),
                        timeout=timeout, execution_timeout=execution_timeout)

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
