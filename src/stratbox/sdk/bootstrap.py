"""Bind authored command contracts to the common execution service."""
from __future__ import annotations

from dataclasses import field, make_dataclass
from hashlib import sha256
from importlib import import_module
from typing import Mapping
from threading import RLock
from functools import lru_cache


def _symbol(reference):
    module, name = reference.split(":", 1)
    value = import_module(module)
    for part in name.split("."):
        value = getattr(value, part)
    if not callable(value):
        raise ValueError("capability.implementation_not_callable")
    return value


class CapabilityRuntimeCatalog:
    """Execution binding for one immutable capability snapshot.

    Domain operations awaiting their scheduled migration are contributed by
    their existing catalog. New command leaves use the same runner, session,
    provider admission, budgets, effects and result evidence.
    """

    def __init__(self, snapshot, domain_catalog=None):
        self.snapshot = snapshot
        self.domain_catalog = domain_catalog
        self._definitions = {}
        self._handlers = {}
        self._requests = {}
        self._results = {}
        self._lock = RLock()

    def __getattr__(self, name):
        domain = self.__dict__.get("domain_catalog")
        if domain is None:
            raise AttributeError(name)
        return getattr(domain, name)

    def admit_local(self, definition):
        """Add a trusted local definition without rebinding live identities."""
        from stratbox.capabilities.catalog import CatalogContribution, CatalogError
        from stratbox.capabilities.model import CapabilityDefinition
        if not isinstance(definition, CapabilityDefinition):
            raise ValueError("capability.definition_required")
        with self._lock:
            try:
                current = self.snapshot.definition(definition.capability_id)
            except CatalogError:
                current = None
            if current is not None:
                if current.fingerprint != definition.fingerprint:
                    raise ValueError("capability.live_identity_conflict")
                return self.snapshot
            if self.domain_catalog is not None:
                try:
                    self.domain_catalog.reference(definition.capability_id)
                except (KeyError, ValueError):
                    pass
                else:
                    raise ValueError("capability.domain_identity_conflict")
            self.snapshot = self.snapshot.overlay(CatalogContribution(definitions=(definition,)))
            return self.snapshot

    def describe(self, capability_id=None):
        """One metadata route includes explicit domain migration readiness."""
        if capability_id is None:
            result = []
            offset = 0
            while True:
                page = self.discover(offset=offset)
                result.extend(page.entries)
                if page.next_offset is None:
                    return tuple(result)
                offset = page.next_offset
        try:
            description = self.snapshot.describe(capability_id)
        except (KeyError, ValueError):
            if self.domain_catalog is None:
                raise ValueError("capability.unavailable") from None
            from stratbox.operations.discovery import describe_operation
            description = describe_operation(self.domain_catalog, self.domain_catalog.reference(capability_id))
            return {**description, "capability_id": capability_id, "kind": "operation",
                "migration_status": "domain_pending_migration",
                "readiness": {"metadata": True, "typed": "requires_admission",
                    "executable": "domain_contract_requires_admission", "machine": description["machine_schema_admission"]}}
        return {**description, "migration_status": "canonical",
            "readiness": {"metadata": True, "typed": True,
                "executable": "requires_provider_and_implementation_admission", "machine": "requires_wire_contract"}}

    def discover(self, *, kind=None, query=None, offset=0, limit=200):
        """Bounded stable catalog projection; never imports domain handlers."""
        if kind is not None and kind not in {"command", "operation", "scenario", "cascade"}:
            raise ValueError("capability.kind_invalid")
        if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 200:
            raise ValueError("capability.page_invalid")
        if query is not None and (not isinstance(query, str) or len(query) > 256):
            raise ValueError("capability.query_invalid")
        identifiers = {item.capability_id: item.kind for item in self.snapshot.definitions}
        if self.domain_catalog is not None:
            identifiers.update({ref.operation_id: "operation" for ref in self.domain_catalog.list_refs()
                                if ref.operation_id not in identifiers})
        selected = [identifier for identifier, actual_kind in sorted(identifiers.items())
                    if (kind is None or actual_kind == kind) and (query is None or query.casefold() in identifier.casefold())]
        from stratbox.operations.discovery import CatalogPage
        stop = min(len(selected), offset + limit)
        return CatalogPage(tuple(self.describe(identifier) for identifier in selected[offset:stop]),
                           offset, len(selected), stop if stop < len(selected) else None)

    def _command(self, capability_id):
        try:
            definition = self.snapshot.definition(capability_id)
        except (KeyError, ValueError):
            return None
        return definition if definition.kind == "command" else None

    def get(self, capability_id):
        with self._lock:
            return self._get(capability_id)

    def _get(self, capability_id):
        command = self._command(capability_id)
        if command is None:
            if self.domain_catalog is None:
                raise ValueError("capability.command_required")
            return self.domain_catalog.get(capability_id)
        if capability_id in self._definitions:
            return self._definitions[capability_id]
        from stratbox.core.execution.contracts import OperationDefinition
        from stratbox.shared.data.operations import InputPort, OutputPort, OperationSemantics, ProcessingFunction, RequestField
        from stratbox.shared.data.processing import DataContract

        names = set(command.inputs) | set(command.parameters) | set(command.fixed) | set(command.required_parameters)
        if any(not name.isidentifier() or name.startswith("_") for name in names):
            raise ValueError("capability.invalid_request_field")
        suffix = sha256((capability_id + ":" + command.fingerprint).encode()).hexdigest()[:16]
        request_type = make_dataclass("CommandRequest_" + suffix,
            [(name, object, field(default_factory=lambda default=command.fixed.get(name, command.parameters.get(name)): default)) for name in sorted(names)],
            frozen=True, namespace={"__module__": __name__})
        # Stable module ownership supports typed request and method inspection.
        globals()[request_type.__name__] = request_type
        self._requests[capability_id] = request_type
        output_names = tuple(command.outputs)
        if len(output_names) > 1:
            output_type = make_dataclass("CommandOutputs_" + suffix,
                [(name, object, field(default=None)) for name in output_names],
                frozen=True, namespace={"__module__": __name__})
            globals()[output_type.__name__] = output_type
            self._results[capability_id] = output_type
        schema = lambda port: port.schema or DataContract("capability.value")
        semantics = OperationSemantics((),
            inputs=tuple(InputPort(name, schema(port), path=name, required=port.required,
                qualifications=port.qualifications, coverage=port.expected_coverage, collection=port.collection,
                outcomes=port.outcomes, alternatives=port.alternatives,
                accepts_any_contract=port.schema is None)
                for name, port in command.inputs.items()),
            outputs=tuple(OutputPort(name, schema(port), path=name if len(output_names) > 1 else "",
                qualifications=port.qualifications, coverage=port.expected_coverage, collection=port.collection,
                evidence_policy="value", outcomes=port.outcomes)
                for name, port in command.outputs.items()),
            parameters=tuple(sorted(names - set(command.inputs))),
            required_parameters=command.required_parameters,
            summary=command.summary or command.capability_id, function=ProcessingFunction.INSPECT)
        definition = OperationDefinition(command.capability_id, "command." + suffix, request_type,
            self._results.get(capability_id, object), required_capabilities=command.required_capabilities,
            optional_capabilities=command.optional_capabilities,
            possible_effects=command.effects, partial_allowed=command.acceptance.partial_allowed,
            processing=semantics, method_refs=(command.implementation_ref,),
            request_fields=tuple(RequestField(name, "input" if name in command.inputs else "parameter") for name in sorted(names)))
        self._definitions[capability_id] = definition
        return definition

    def metadata(self, capability_id):
        return self.get(capability_id)

    def reference(self, capability_id):
        command = self._command(capability_id)
        if command is None:
            return self.domain_catalog.reference(capability_id)
        from stratbox.operations.catalog import OperationRef
        return OperationRef(capability_id, command.implementation_ref, definition=self.get(capability_id))

    def resolve(self, capability_id):
        with self._lock:
            return self._resolve(capability_id)

    def _resolve(self, capability_id):
        command = self._command(capability_id)
        if command is None:
            return self.domain_catalog.resolve(capability_id)
        definition = self.get(capability_id)
        if capability_id not in self._handlers:
            implementation = _symbol(command.implementation_ref)

            def work(request, invocation):
                values = {name: getattr(request, name) for name in self._requests[capability_id].__dataclass_fields__}
                from stratbox.core.execution.contracts import OperationFailure
                for name, expected in command.fixed.items():
                    if values.get(name) != expected:
                        raise OperationFailure("capability.fixed_parameter_conflict")
                for name in command.required_parameters:
                    if values.get(name) is None:
                        raise OperationFailure("capability.parameter_required")
                try:
                    for name, port in command.inputs.items():
                        if values.get(name) is not None or port.required:
                            port.validate(values.get(name))
                except ValueError as error:
                    raise OperationFailure(str(error)) from None
                answer = implementation(values, invocation)
                from stratbox.core.execution.runner import Completion
                value = answer.value if isinstance(answer, Completion) else answer
                outcome = answer.outcome if isinstance(answer, Completion) else "succeeded"
                if len(command.outputs) == 1:
                    outputs = {next(iter(command.outputs)): value}
                elif isinstance(value, Mapping):
                    outputs = dict(value)
                else:
                    outputs = {name: getattr(value, name) for name in command.outputs if hasattr(value, name)}
                try:
                    if set(outputs) - command.outputs.keys():
                        raise ValueError("acceptance.output_unknown")
                    for name, port in command.outputs.items():
                        if outcome not in port.outcomes:
                            continue
                        if name not in outputs:
                            if port.required:
                                raise ValueError("acceptance.output_missing")
                            continue
                        if outputs[name] is None and not port.required:
                            continue
                        port.validate(outputs[name])
                    if outcome in {"succeeded", "partial"}:
                        command.acceptance.validate({name: value for name, value in outputs.items()
                            if outcome in command.outputs[name].outcomes
                            and (value is not None or command.outputs[name].required)})
                except ValueError as error:
                    raise OperationFailure(str(error)) from None
                if capability_id in self._results:
                    value = self._results[capability_id](**outputs)
                    if isinstance(answer, Completion):
                        return Completion(value, answer.outcome, *answer.diagnostics)
                    return value
                return answer

            def execute(request, *, context=None, **options):
                from stratbox.core.execution.runner import run
                return run(definition, request, work, context=context, **options)

            self._handlers[capability_id] = execute
        return definition, self._handlers[capability_id], None

    def resource_requirements(self, capability_id, parameters=None):
        """Resolve declared capacity coordinates before admitting physical work."""
        command = self._command(capability_id)
        if command is None:
            method = getattr(self.domain_catalog, "resource_requirements", None)
            return {} if method is None else method(capability_id, parameters)
        if not command.resource_parameters:
            return {}
        values = self.snapshot.resolve(capability_id, parameters=parameters).parameters
        requirements = {}
        for resource, parameter in command.resource_parameters.items():
            if parameter not in values:
                raise ValueError("capability.resource_parameter_required")
            amount = values[parameter]
            if type(amount) is not int or amount < 0:
                raise ValueError("capability.resource_parameter_invalid")
            requirements[resource] = amount
        return requirements

    def requirements(self, capability_id):
        return () if self._command(capability_id) is not None else self.domain_catalog.requirements(capability_id)

    def bind(self, capability_id, *, inputs=None, parameters=None, **options):
        command = self._command(capability_id)
        if command is None:
            return self.domain_catalog.bind(capability_id, inputs=inputs, parameters=parameters, **options)
        from stratbox.core.execution.calls import bind_operation
        if parameters is not None and not isinstance(parameters, Mapping):
            raise ValueError("capability.parameters_mapping_required")
        bound_parameters = dict(self.snapshot.resolve(capability_id, parameters=parameters).parameters)
        if any(bound_parameters.get(name) is None for name in command.required_parameters):
            raise ValueError("capability.parameter_required")
        return bind_operation(self, capability_id, inputs=inputs, parameters=bound_parameters, **options)


@lru_cache(maxsize=1)
def default_snapshot():
    """Compose independent metadata contributions at the SDK bootstrap boundary."""
    from stratbox.capabilities.manifest import catalog_snapshot
    from stratbox.domains.cbr.capabilities import contribution as cbr
    from stratbox.domains.fns.capabilities import contribution as fns
    from stratbox.domains.minfin.capabilities import contribution as minfin
    from stratbox.domains.frank_rg.capabilities import contribution as frank
    from stratbox.domains.rosstat.capabilities import contribution as rosstat
    return catalog_snapshot().overlay(cbr(), fns(), minfin(), frank(), rosstat())
