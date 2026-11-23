"""Named operation calls and source-route admission through the one runner.

Binding is a metadata and value check. It performs no acquisition, persistence,
decoding or scheduling. Each handler still owns its normal execution policy.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
from functools import lru_cache
from typing import Any, get_args, get_origin, get_type_hints
from typing import Mapping

from stratbox.core.execution.handoff import (
    BoundRequest, HandoffError, adapt_input, bind_request,
)
from stratbox.shared.data.operations import OperationKey
from stratbox.core.execution.admission import ResultAdmission
from stratbox.core.execution.contracts import Diagnostic, ExecutionContext
from stratbox.shared.data.source_context import ValueContext
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


def _coordinate_context(value, contract=None, supplied=None):
    from stratbox.core.execution.value_context import value_context
    actual = value_context(value, contract)
    if supplied is None:
        return actual
    if not isinstance(supplied, ValueContext):
        raise HandoffError("source.context_invalid")
    # External preparation can add qualified coordinates, but cannot contradict
    # a positive source/issue/material claim in the typed value itself.
    for actual_use in actual.uses:
        coordinate = actual_use.coordinate
        matching = [use.coordinate for use in supplied.uses
                    if use.coordinate.source_id == coordinate.source_id]
        if coordinate.source_id is not None and not matching:
            raise HandoffError("source.context_claim_mismatch")
        for name in ("family_id", "source_group_id", "issue_id", "asset_id", "material_identity"):
            known = getattr(coordinate, name)
            if known is not None and matching and all(getattr(member, name) not in {None, known} for member in matching):
                raise HandoffError("source.context_claim_mismatch")
    return ValueContext((*actual.uses, *supplied.uses))


def _check_context(value, expected, *, allowed_sources=(), family_id=None, contract=None,
                   scope="source", primary_required=False, source_catalog=None,
                   group_id=None, edition=None, supplied=None, retained_required=True):
    from stratbox.core.execution.value_context import value_context, validate_retained_context
    try:
        context = _coordinate_context(value, contract, supplied)
        if scope == "source" and retained_required:
            for retained in _retained_values(value):
                validate_retained_context(retained)
                if not value_context(retained, contract).source_ids:
                    raise HandoffError("source.input_context_missing")
    except ValueError as error:
        raise HandoffError(str(error)) from None
    for use in context.uses:
        coordinate = use.coordinate
        card = source_catalog.source(coordinate.source_id) if source_catalog is not None and coordinate.source_id is not None else None
        if source_catalog is not None and coordinate.source_id is not None and card is None:
            raise HandoffError("source.context_source_unknown")
        if card is not None:
            if coordinate.family_id is not None and coordinate.family_id != card.family_id:
                raise HandoffError("source.context_family_mismatch")
            if coordinate.source_group_id is not None and not any(
                group.group_id == coordinate.source_group_id for group in card.source_groups
            ):
                raise HandoffError("source.context_group_unknown")
        if scope == "catalog":
            continue
        if scope == "family":
            if coordinate.family_id is not None and coordinate.family_id != family_id:
                raise HandoffError("source.input_group_mismatch")
            if card is not None and card.family_id != family_id:
                raise HandoffError("source.input_group_mismatch")
        elif coordinate.source_id is not None and coordinate.source_id not in {expected, *allowed_sources}:
            raise HandoffError("source.input_series_mismatch")
        elif coordinate.source_id is None and coordinate.family_id is not None and coordinate.family_id != family_id:
            raise HandoffError("source.input_group_mismatch")
        if coordinate.source_id == expected:
            if group_id is not None and coordinate.source_group_id != group_id:
                raise HandoffError("source.input_group_mismatch")
            known_editions = tuple(member for member in (coordinate.layout_edition, coordinate.semantic_profile_edition) if member is not None)
            if edition is not None and known_editions and edition not in known_editions:
                raise HandoffError("source.input_edition_mismatch")
    if primary_required and expected not in context.source_ids:
        raise HandoffError("source.input_context_missing" if not context.source_ids else "source.input_series_mismatch")
    return context


def _output_value(value, path):
    for name in path.split(".") if path else ():
        if value is None:
            return None
        if not is_dataclass(value) or name not in {field.name for field in fields(value)}:
            raise HandoffError("source.output_path_invalid")
        value = getattr(value, name)
    return value


def _output_diagnostic(error):
    code = str(error)
    code = {"source.input_series_mismatch": "source.output_series_mismatch",
            "source.input_context_missing": "source.output_context_missing",
            "source.input_group_mismatch": "source.output_group_mismatch",
            "source.input_edition_mismatch": "source.output_edition_mismatch"}.get(code, code)
    from stratbox.shared.identifiers import safe_token
    try:
        safe_token(code)
        if not code.startswith(("source.", "registry.")):
            raise ValueError
    except ValueError:
        code = "source.output_context_invalid"
    return Diagnostic(code, "result_admission", "source", "source")


@dataclass(frozen=True, slots=True)
class SourceResultAdmission(ResultAdmission):
    """One bound operation's source obligations inside the trusted runner."""
    definition: object
    source_id: str
    family_id: str
    source_catalog: object
    auxiliary_sources: tuple[tuple[str, tuple[str, ...]], ...] = ()
    input_uses: tuple[tuple[str, ValueContext], ...] = ()
    context_scope: str = "source"
    group_id: str | None = None
    edition: str | None = None
    request_source_context: ValueContext | None = None
    policy_id: str = "source.context"

    def _continue_coordinates(self, context):
        """Preserve known publication pairs while allowing a selected subset."""
        actual = tuple(use.coordinate for _, supplied in self.input_uses for use in supplied.uses)
        requested = tuple(use.coordinate for use in self.request_source_context.uses) if self.request_source_context is not None else ()
        for source_id in context.source_ids:
            incoming = tuple(coordinate for coordinate in actual if coordinate.source_id == source_id)
            request = tuple(coordinate for coordinate in requested if coordinate.source_id == source_id)
            # An actual material/index constrains selection. Request identity
            # establishes a coordinate only when it was not known on entry.
            issues = {coordinate.issue_id for coordinate in incoming if coordinate.issue_id is not None}
            if not issues:
                issues = {coordinate.issue_id for coordinate in request if coordinate.issue_id is not None}
            outgoing = tuple(use.coordinate for use in context.uses if use.coordinate.source_id == source_id)
            detailed = tuple(coordinate for coordinate in outgoing if coordinate.issue_id is not None)
            if issues and not detailed:
                raise HandoffError("source.output_issue_missing")
            for coordinate in detailed:
                if issues and coordinate.issue_id not in issues:
                    raise HandoffError("source.output_issue_mismatch")
            for coordinate in outgoing:
                if coordinate.issue_id is None and detailed:
                    continue  # Source-level summaries can accompany full pairs.
                matches = tuple(member for member in incoming
                    if member.issue_id in {None, coordinate.issue_id})
                assets = {member.asset_id for member in matches if member.asset_id is not None}
                if not assets:
                    assets = {member.asset_id for member in request if member.issue_id in {None, coordinate.issue_id}
                              and member.asset_id is not None}
                same_issue = tuple(member for member in outgoing if member.issue_id == coordinate.issue_id)
                if assets and not any(member.asset_id is not None for member in same_issue):
                    raise HandoffError("source.output_asset_missing")
                if assets and coordinate.asset_id is not None and coordinate.asset_id not in assets:
                    raise HandoffError("source.output_asset_mismatch")

    def _supporting_roles(self, context):
        if self.context_scope != "source":
            return
        for use in context.uses:
            source = use.coordinate.source_id
            if source is None or source == self.source_id:
                continue
            permitted = [role for role, sources in self.auxiliary_sources if source in sources]
            role = use.input_role
            if not any(role == name or role.startswith(name + ".") or "." + name + "." in role
                       or role.endswith("." + name) or role.startswith(name + ":") for name in permitted):
                raise HandoffError("source.auxiliary_role_mismatch")

    def assess(self, definition, value, *, phase, outcome=None):
        # A composed handler can execute other operations with the same context.
        # Its child contracts retain their own output paths and obligations.
        if definition != self.definition:
            return ()
        allowed = tuple(source for _, sources in self.auxiliary_sources for source in sources)
        try:
            if phase == "precommit":
                context = _check_context(value, self.source_id, allowed_sources=allowed,
                    family_id=self.family_id, source_catalog=self.source_catalog,
                    scope=self.context_scope, primary_required=self.context_scope == "source",
                    group_id=self.group_id, edition=self.edition)
                self._continue_coordinates(context)
                self._supporting_roles(context)
                return ()
            for port in definition.processing.outputs if definition.processing else ():
                if outcome in {"succeeded", "partial"} and outcome not in port.outcomes:
                    continue
                policy = port.source_policy
                if policy == "source_inapplicable":
                    continue
                member = _output_value(value, port.path)
                if member is None and policy in {"source_optional", "source_collection"}:
                    continue
                carrier = (_output_value(value, port.source_context_path)
                    if port.source_context_path is not None else member)
                context = _check_context(carrier, self.source_id,
                    contract=port.contract if port.source_context_path is None else None,
                    allowed_sources=allowed, family_id=self.family_id,
                    source_catalog=self.source_catalog, scope=self.context_scope,
                    primary_required=policy == "primary_source_required",
                    group_id=self.group_id, edition=self.edition,
                    retained_required=policy != "source_optional")
                empty_collection = member is None or isinstance(member, (tuple, list)) and not member
                if policy == "source_collection" and not context.source_ids and not empty_collection:
                    raise HandoffError("source.output_context_missing")
                if policy in {"primary_source_required", "source_collection"}:
                    self._continue_coordinates(context)
                self._supporting_roles(context)
            return ()
        except (ValueError, TypeError) as error:
            return (_output_diagnostic(error),)


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
    source_admission: SourceResultAdmission | None = None

    @property
    def request(self):
        return self.bound.request

    @property
    def definition(self):
        return self.bound.definition

    def invoke(self, *, context=None, **options):
        definition, handler, _ = self.catalog.resolve(self.key.operation_id)
        if definition != self.definition:
            raise HandoffError("handoff.operation_mismatch")
        if self.source_admission is not None:
            context = context or ExecutionContext()
            context = replace(context, result_admissions=(*context.result_admissions, self.source_admission))
        return self.bound.invoke(handler, context=context, **options)


def bind_operation(catalog, operation_id, *, inputs=None, parameters=None,
                   source_resolver=None, domain_admitter=None):
    definition = catalog.get(operation_id)
    if inputs is not None and not isinstance(inputs, Mapping):
        raise HandoffError("handoff.input_unknown")
    supplied = {} if inputs is None else dict(inputs)
    requirements = catalog.requirements(operation_id)
    names = {requirement.input_name for requirement in requirements}
    if names and set(supplied) & names:
        from stratbox.domains.registry.requirements import bind_requirement_inputs
        role_keys = set(supplied) & names
        direct = {name: value for name, value in supplied.items() if name not in role_keys}
        roles = {name: value for name, value in supplied.items() if name in role_keys}
        try:
            resolved = bind_requirement_inputs(catalog, operation_id, roles,
                resolver=source_resolver, domain_admitter=domain_admitter, parameters=parameters)
        except ValueError as error:
            raise HandoffError(str(error)) from None
        if set(direct) & set(resolved):
            raise HandoffError("handoff.input_parameter_conflict")
        supplied = {**direct, **resolved}
    admitted = {name: adapt_input(value) for name, value in supplied.items()}
    bound = bind_request(definition, admitted, parameters=parameters)
    return OperationCall(catalog, OperationKey(operation_id), bound)


@dataclass(frozen=True, slots=True)
class SourceBinding:
    catalog: object
    source: object
    route: object
    format: str | None = None
    group_id: str | None = None
    edition: str | None = None

    def bind(self, operation_id, *, inputs=None, parameters=None,
             source_resolver=None, domain_admitter=None):
        selection = self.catalog.source_catalog().selection(self.source.series_id,
            format=self.format, group_id=self.group_id, edition=self.edition)
        candidates = tuple(binding for binding in selection.bindings if binding.operation_id == operation_id)
        if len(candidates) != 1:
            rejected = next((item for item in selection.assessments
                if item.binding.operation_id == operation_id and item.state == "inapplicable"), None)
            if rejected is not None and rejected.reasons:
                raise HandoffError(rejected.reasons[0])
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
        # Exact named ports admit handoff. A stage graph is a useful display
        # projection, but cannot reject an otherwise compatible value.
        call = bind_operation(self.catalog, operation_id, inputs=inputs, parameters=supplied,
            source_resolver=source_resolver, domain_admitter=domain_admitter)
        auxiliary = {name: set(sources) for name, sources in binding.auxiliary_sources}
        output_roles = {name: set(sources) for name, sources in binding.auxiliary_sources}
        # Canonical source requirements already own the supporting-source fact.
        # Derive per-port admission and per-role output obligations from them.
        for requirement in self.catalog.requirements(operation_id):
            support = set(requirement.source_ids) - {self.source.series_id}
            if support:
                auxiliary.setdefault(requirement.port, set()).update(support)
                output_roles.setdefault(requirement.input_name, set()).update(support)
        from stratbox.core.execution.value_context import context_requirements_refs
        for name, prepared in call.bound.inputs:
            for reference in context_requirements_refs(prepared.value):
                for requirement in self.catalog.requirements(reference):
                    support = set(requirement.source_ids) - {self.source.series_id}
                    if support:
                        auxiliary.setdefault(name, set()).update(support)
                        output_roles.setdefault(requirement.input_name, set()).update(support)
        contexts = []
        for name, value in call.bound.inputs:
            context = _check_context(value.value, self.source.series_id,
                allowed_sources=auxiliary.get(name, ()), family_id=self.source.family_id,
                contract=value.contract, scope=binding.context_scope,
                source_catalog=self.catalog.source_catalog(), group_id=self.group_id,
                edition=self.edition, supplied=value.source_context)
            contexts.append((name, context))
        admission = SourceResultAdmission(call.definition, self.source.series_id,
            self.source.family_id, self.catalog.source_catalog(),
            tuple((name, tuple(sorted(sources))) for name, sources in sorted(output_roles.items())),
            tuple(contexts), binding.context_scope, self.group_id, self.edition)
        from stratbox.core.execution.value_context import value_context
        admission = replace(admission, request_source_context=value_context(call.request))
        return OperationCall(self.catalog, call.key, call.bound,
            self.source.series_id, self.route.profile_id, self.source.family_id,
            binding.auxiliary_sources, binding.context_scope, admission)


def bind_source(catalog, series_id, *, format=None, group_id=None, edition=None):
    from stratbox.domains.registry.declarations import source_route
    source = catalog.source_catalog().source(series_id)
    if source is None:
        raise HandoffError("source.unknown")
    if format is not None and (not isinstance(format, str) or format not in source.formats):
        raise HandoffError("source.format_unavailable")
    selected = catalog.source_catalog().selection(series_id, format=format, group_id=group_id, edition=edition)
    if selected.state == "inapplicable":
        raise HandoffError(selected.reasons[0])
    return SourceBinding(catalog, source, source_route(series_id), format, group_id, edition)
