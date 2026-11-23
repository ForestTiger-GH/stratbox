"""Named operation calls and source-route admission through the one runner.

Binding is a metadata and value check. It performs no acquisition, persistence,
decoding or scheduling. Each handler still owns its normal execution policy.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from typing import Mapping

from stratbox.core.execution.handoff import (
    BoundRequest, HandoffError, ProjectedOutput, adapt_input, bind_request,
)
from stratbox.shared.data.operations import OperationKey, ProcessingStage


def _check_series(value, expected, depth=0, seen=None):
    if not isinstance(value, (tuple, list, Mapping)) and (
            isinstance(value, type) or not is_dataclass(value)):
        return
    seen = set() if seen is None else seen
    if id(value) in seen:
        return
    seen.add(id(value))
    if depth > 32:
        raise HandoffError("source.input_structure_invalid")
    if isinstance(value, (tuple, list)):
        for member in value:
            _check_series(member, expected, depth + 1, seen)
    elif isinstance(value, Mapping):
        for member in value.values():
            _check_series(member, expected, depth + 1, seen)
    elif is_dataclass(value) and not isinstance(value, type):
        series_id = (getattr(value, "series_id")
                     if any(field.name == "series_id" for field in fields(value)) else None)
        if series_id is not None and series_id != expected:
            raise HandoffError("source.input_series_mismatch")
        for field in fields(value):
            if field.name != "series_id":
                _check_series(getattr(value, field.name), expected, depth + 1, seen)


@dataclass(frozen=True, slots=True)
class OperationCall:
    catalog: object
    key: OperationKey
    bound: BoundRequest
    series_id: str | None = None
    route_profile: str | None = None

    @property
    def request(self):
        return self.bound.request

    @property
    def definition(self):
        return self.bound.definition

    def invoke(self, *, context=None, **options):
        definition, handler, _ = self.catalog.resolve(
            self.key.operation_id, self.key.contract_version,
        )
        if definition != self.definition:
            raise HandoffError("handoff.operation_mismatch")
        return self.bound.invoke(handler, context=context, **options)


def bind_operation(catalog, operation_id, contract_version, *, inputs=None, parameters=None):
    definition = catalog.get(operation_id, contract_version)
    if inputs is not None and not isinstance(inputs, Mapping):
        raise HandoffError("handoff.input_unknown")
    admitted = {name: adapt_input(value) for name, value in (inputs or {}).items()}
    bound = bind_request(definition, admitted, parameters=parameters)
    return OperationCall(catalog, OperationKey(operation_id, contract_version), bound)


@dataclass(frozen=True, slots=True)
class SourceBinding:
    catalog: object
    source: object
    route: object
    format: str | None = None

    def bind(self, operation_id, contract_version=None, *, inputs=None,
             parameters=None, from_stage=None):
        candidates = tuple(binding for binding in self.source.operations
                           if binding.operation_id == operation_id and (
                               contract_version is None or binding.contract_version == contract_version))
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
        definition = self.catalog.get(operation_id, binding.contract_version)
        semantics = definition.processing
        if semantics is None:
            raise HandoffError("handoff.processing_unavailable")
        # An explicit source selector is pinned even when the operation uses a
        # generic request type shared by many publications.
        if "series_id" in semantics.parameters:
            if "series_id" in supplied and supplied["series_id"] != self.source.series_id:
                raise HandoffError("source.parameter_conflict")
            supplied["series_id"] = self.source.series_id
        stages = semantics.stages
        if any(stage not in self.route.stages for stage in stages):
            raise HandoffError("source.stage_unavailable")
        if from_stage is not None:
            try:
                previous = ProcessingStage(from_stage)
            except (TypeError, ValueError):
                raise HandoffError("source.stage_unknown") from None
            if previous not in self.route.stages:
                raise HandoffError("source.stage_unavailable")
            if stages and not any(self.route.allows(previous, stage) for stage in stages):
                raise HandoffError("source.transition_unavailable")
        call = bind_operation(self.catalog, operation_id, binding.contract_version,
                              inputs=inputs, parameters=supplied)
        for _, value in call.bound.inputs:
            # Series identity is checked only where the typed value explicitly
            # carries one; physical filenames and URLs never imply identity.
            _check_series(value.value, self.source.series_id)
            if isinstance(value, ProjectedOutput):
                producer = self.catalog.get(value.producer.operation_id,
                                            value.producer.contract_version)
                before = producer.processing.stages if producer.processing else ()
                if before and stages and not any(
                    self.route.allows(left, right) for left in before for right in stages
                ):
                    raise HandoffError("source.transition_unavailable")
        return OperationCall(self.catalog, call.key, call.bound,
                             self.source.series_id, self.route.profile_id)


def bind_source(catalog, series_id, *, format=None):
    from stratbox.core.registry.sources import source_route
    source = catalog.source_catalog().source(series_id)
    if source is None:
        raise HandoffError("source.unknown")
    if format is not None and (not isinstance(format, str) or format not in source.formats):
        raise HandoffError("source.format_unavailable")
    return SourceBinding(catalog, source, source_route(series_id), format)
