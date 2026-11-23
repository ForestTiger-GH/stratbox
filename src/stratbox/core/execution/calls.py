"""Named operation calls and source-route admission through the one runner.

Binding is a metadata and value check. It performs no acquisition, persistence,
decoding or scheduling. Each handler still owns its normal execution policy.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from functools import lru_cache
from typing import Any, get_args, get_origin, get_type_hints
from typing import Mapping

from stratbox.core.execution.handoff import (
    BoundRequest, HandoffError, adapt_input, bind_request,
)
from stratbox.shared.data.operations import OperationKey, ProcessingStage
from stratbox.shared.data.snapshots import DatasetAssembly, DatasetSnapshot
from stratbox.shared.materials import MaterialArtifact


@lru_cache(maxsize=512)
def _may_retain_values(kind):
    """Avoid traversing every cell of a typed table to look for wrappers."""
    active = set()
    def visit(annotation):
        if annotation in (Any, object, DatasetSnapshot, DatasetAssembly, MaterialArtifact):
            return True
        arguments = get_args(annotation)
        if arguments:
            return any(visit(item) for item in arguments if item is not Ellipsis)
        if not isinstance(annotation, type) or not is_dataclass(annotation):
            return False
        if annotation in active:
            return True
        active.add(annotation)
        try:
            hints = get_type_hints(annotation)
            return any(field.name not in hints or visit(hints[field.name]) for field in fields(annotation))
        except (TypeError, NameError):
            return True
        finally:
            active.remove(annotation)
    return visit(kind)


def _retained_values(value, seen=None, depth=0):
    """Find semantic retained wrappers without following their evidence history."""
    if depth > 32:
        raise HandoffError("source.input_structure_invalid")
    if not isinstance(value, (tuple, list, Mapping, DatasetSnapshot, DatasetAssembly, MaterialArtifact)):
        if isinstance(value, type) or not is_dataclass(value) or not _may_retain_values(type(value)):
            return
    seen = set() if seen is None else seen
    if id(value) in seen:
        return
    seen.add(id(value))
    if isinstance(value, (DatasetSnapshot, DatasetAssembly, MaterialArtifact)):
        yield value
    elif isinstance(value, (tuple, list)):
        for item in value:
            yield from _retained_values(item, seen, depth + 1)
    elif isinstance(value, Mapping):
        for item in value.values():
            yield from _retained_values(item, seen, depth + 1)
    elif is_dataclass(value) and not isinstance(value, type):
        module = type(value).__module__
        if module in {"stratbox.shared.evidence", "stratbox.shared.data.datasets"}:
            return
        for field in fields(value):
            yield from _retained_values(getattr(value, field.name), seen, depth + 1)


def _check_context(value, expected, *, allowed_sources=(), family_id=None, contract=None,
                   scope="source", primary_required=False):
    from stratbox.core.execution.value_context import value_context
    try:
        context = value_context(value, contract)
        if scope == "source":
            for retained in _retained_values(value):
                if not value_context(retained, contract).source_ids:
                    raise HandoffError("source.input_context_missing")
    except ValueError as error:
        raise HandoffError(str(error)) from None
    if scope == "catalog":
        return
    if scope == "source" and not set(context.source_ids) <= {expected, *allowed_sources}:
        raise HandoffError("source.input_series_mismatch")
    if scope == "source" and primary_required and context.source_ids and expected not in context.source_ids:
        raise HandoffError("source.input_series_mismatch")
    if family_id is not None and context.group_ids and family_id not in context.group_ids:
        raise HandoffError("source.input_group_mismatch")


@dataclass(frozen=True, slots=True)
class OperationCall:
    catalog: object
    key: OperationKey
    bound: BoundRequest
    series_id: str | None = None
    route_profile: str | None = None
    family_id: str | None = None
    auxiliary_sources: tuple[tuple[str, tuple[str, ...]], ...] = ()
    context_scope: str = "source"

    @property
    def request(self):
        return self.bound.request

    @property
    def definition(self):
        return self.bound.definition

    def invoke(self, *, context=None, **options):
        definition, handler, _ = self.catalog.resolve(
            self.key.operation_id,
        )
        if definition != self.definition:
            raise HandoffError("handoff.operation_mismatch")
        result = self.bound.invoke(handler, context=context, **options)
        if self.series_id is not None and result.value is not None:
            try:
                _check_context(result.value, self.series_id,
                    allowed_sources=tuple(source for _, sources in self.auxiliary_sources for source in sources),
                    family_id=self.family_id, scope=self.context_scope,
                    primary_required=True)
            except HandoffError as error:
                if error.code == "source.input_series_mismatch":
                    raise HandoffError("source.output_series_mismatch") from None
                if error.code == "source.input_group_mismatch":
                    raise HandoffError("source.output_group_mismatch") from None
                if error.code == "source.input_context_missing":
                    raise HandoffError("source.output_context_missing") from None
                raise
        return result


def bind_operation(catalog, operation_id, *, inputs=None, parameters=None):
    definition = catalog.get(operation_id)
    if inputs is not None and not isinstance(inputs, Mapping):
        raise HandoffError("handoff.input_unknown")
    admitted = {name: adapt_input(value) for name, value in (inputs or {}).items()}
    bound = bind_request(definition, admitted, parameters=parameters)
    return OperationCall(catalog, OperationKey(operation_id), bound)


@dataclass(frozen=True, slots=True)
class SourceBinding:
    catalog: object
    source: object
    route: object
    format: str | None = None

    def bind(self, operation_id, *, inputs=None,
             parameters=None, from_stage=None):
        candidates = tuple(binding for binding in self.source.operations
                           if binding.operation_id == operation_id)
        if len(candidates) != 1:
            raise HandoffError("source.operation_unbound")
        binding = candidates[0]
        if (self.format is None and binding.formats
                and not set(self.source.formats) <= set(binding.formats)):
            raise HandoffError("source.format_required")
        if self.format is not None and binding.formats and self.format not in binding.formats:
            raise HandoffError("source.operation_format_unavailable")
        if parameters is not None and not isinstance(parameters, Mapping):
            raise HandoffError("handoff.parameter_unknown")
        supplied = {} if parameters is None else dict(parameters)
        for name, value in binding.parameters:
            if name in supplied and supplied[name] != value:
                raise HandoffError("source.parameter_conflict")
            supplied[name] = value
        definition = self.catalog.get(operation_id)
        semantics = definition.processing
        if semantics is None:
            raise HandoffError("handoff.processing_unavailable")
        # The source declaration selects the request field explicitly. The
        # request annotation controls its scalar/collection shape.
        identity_parameter = binding.identity_parameter
        if identity_parameter is not None:
            if identity_parameter not in semantics.parameters:
                raise HandoffError("source.identity_parameter_invalid")
            annotation = get_type_hints(definition.request_type).get(identity_parameter)
            selected = ((self.source.series_id,) if get_origin(annotation) is tuple
                        else self.source.series_id)
            if identity_parameter in supplied and supplied[identity_parameter] != selected:
                raise HandoffError("source.parameter_conflict")
            supplied[identity_parameter] = selected
        if from_stage is not None:
            try:
                previous = ProcessingStage(from_stage)
            except (TypeError, ValueError):
                raise HandoffError("source.stage_unknown") from None
            if previous not in self.route.stages:
                raise HandoffError("source.stage_unavailable")
        # Exact named ports admit handoff. A stage graph is a useful display
        # projection, but cannot reject an otherwise compatible value.
        call = bind_operation(self.catalog, operation_id, inputs=inputs, parameters=supplied)
        auxiliary = dict(binding.auxiliary_sources)
        for name, value in call.bound.inputs:
            _check_context(value.value, self.source.series_id,
                allowed_sources=auxiliary.get(name, ()), family_id=self.source.family_id,
                contract=value.contract, scope=binding.context_scope)
        return OperationCall(self.catalog, call.key, call.bound,
                             self.source.series_id, self.route.profile_id,
                             self.source.family_id, binding.auxiliary_sources,
                             binding.context_scope)


def bind_source(catalog, series_id, *, format=None):
    from stratbox.core.registry.sources import source_route
    source = catalog.source_catalog().source(series_id)
    if source is None:
        raise HandoffError("source.unknown")
    if format is not None and (not isinstance(format, str) or format not in source.formats):
        raise HandoffError("source.format_unavailable")
    return SourceBinding(catalog, source, source_route(series_id), format)
