"""Strict semantic ports and factual source requirements, without schema releases."""
from dataclasses import dataclass, field
from collections.abc import Mapping
from .immutable import freeze


def field(value, path):
    for part in path.split('.') if path else ():
        value = value[part] if isinstance(value, Mapping) else getattr(value, part)
    return value

@dataclass(frozen=True, slots=True)
class SemanticPredicate:
    path: str = ''
    operator: str = 'nonempty'
    expected: object = None
    code: str = 'acceptance.predicate'

    def __post_init__(self):
        if self.operator not in {'nonempty', 'equals', 'one_of', 'minimum', 'maximum', 'contains'}:
            raise ValueError('predicate.invalid_operator')
        if any(not p.isidentifier() or p.startswith('_') for p in self.path.split('.') if p):
            raise ValueError('predicate.invalid_path')
        object.__setattr__(self, 'expected', freeze(self.expected))

    def accepts(self, value):
        try:
            actual = field(value, self.path)
            if self.operator == 'nonempty': return actual is not None and bool(actual)
            if self.operator == 'equals': return actual == self.expected
            if self.operator == 'one_of': return actual in self.expected
            if self.operator == 'minimum': return actual >= self.expected
            if self.operator == 'maximum': return actual <= self.expected
            return self.expected in actual
        except (KeyError, AttributeError, TypeError, ValueError):
            return False

@dataclass(frozen=True, slots=True)
class SourceRequirement:
    series_ids: frozenset[str] = frozenset()
    issue_id: str | None = None
    attribution: str = 'identified'
    family_ids: frozenset[str] = frozenset()
    source_group_ids: frozenset[str] = frozenset()
    input_role: str | None = None
    qualifications: frozenset[str] = frozenset()
    asset_id: str | None = None
    material_identity: object = None
    layout_identity: str | None = None
    semantic_identity: str | None = None
    evidence_ref: str | None = None
    require_evidence: bool = True
    allow_additional_sources: bool = True
    declared_relations: tuple[tuple[str, str, str], ...] = ()

    def __post_init__(self):
        for name in ('series_ids', 'family_ids', 'source_group_ids', 'qualifications'):
            object.__setattr__(self, name, frozenset(getattr(self, name)))
            if any(not isinstance(item,str) or not item for item in getattr(self,name)):
                raise TypeError('source.invalid_requirement')
        if self.attribution not in {'identified', 'asserted', 'optional'}:
            raise ValueError('source.invalid_attribution')
        if any(type(getattr(self,name)) is not bool for name in ('require_evidence','allow_additional_sources')):
            raise TypeError('source.boolean_policy_required')
        relations = tuple(tuple(item) for item in self.declared_relations)
        if any(len(item) != 3 or any(not isinstance(x, str) or not x for x in item) for item in relations):
            raise ValueError('source.invalid_declared_relation')
        object.__setattr__(self, 'declared_relations', relations)

    def validate(self, value):
        if isinstance(value,tuple):
            for item in value: self.validate(item)
            return value
        nested = getattr(value, 'value', None)
        if hasattr(nested, 'source_uses'):
            return self.validate(nested)
        source = getattr(value, 'source_id', getattr(value, 'series_id', None))
        issue = getattr(value, 'issue_id', None)
        claim = getattr(value, 'claim', None)
        material = getattr(value, 'material', None)
        physical = material or value
        physical_source = getattr(physical, 'source_id', None)
        metadata = getattr(physical, 'metadata', {})
        asset = metadata.get('container_asset_id') or getattr(claim, 'asset_id', None) or metadata.get('asset_id')
        related = any(physical_source == feed and asset == member and series in self.series_ids
                      for feed, member, series in self.declared_relations)
        if source is None and hasattr(nested,'source_id'):
            source=getattr(nested,'source_id');issue=getattr(nested,'issue_id',issue)
        if claim is not None:
            source, issue = claim.source_id, claim.issue_id
        if material is not None:
            material_source = getattr(material, 'source_id', None)
            if self.series_ids and material_source is not None and material_source not in self.series_ids and not related:
                raise ValueError('source.context_conflict')
            if claim is not None and material_source is not None and material_source != claim.source_id:
                raise ValueError('source.context_conflict')
            if source is None: source = getattr(material, 'source_id', None)
            if not issue: issue = getattr(material,'metadata',{}).get('issue_id')
        if not issue: issue = getattr(value,'metadata',{}).get('issue_id')
        if self.series_ids and source is not None and source not in self.series_ids and not related:
            raise ValueError('source.context_conflict')
        if self.series_ids and source is None and self.attribution == 'identified' and not getattr(value, 'source_uses', ()):
            raise ValueError('source.attribution_required')
        if self.issue_id and issue != self.issue_id and (issue or not getattr(value, 'source_uses', ())):
            raise ValueError('source.issue_conflict')
        # Semantic values retain actual relational uses. A convenient source
        # label or a lineage string cannot establish their qualified origin.
        from stratbox.shared.data.values import Material, IdentifiedMaterial, ImmutableMaterialRef
        from stratbox.shared.data.materials import StagedMaterialRef
        readable = isinstance(value, (Material, IdentifiedMaterial, ImmutableMaterialRef, StagedMaterialRef))
        uses = tuple(getattr(value, 'source_uses', ()))
        if hasattr(value, 'source_uses') and (uses or not readable):
            from stratbox.shared.data.source_context import SourceUse
            if any(not isinstance(use, SourceUse) for use in uses):
                raise TypeError('source.typed_uses_required')
            if not uses and self.attribution == 'optional':
                return value
            matches = [use for use in uses if self._matches(use)]
            if not matches:
                raise ValueError('source.qualified_use_required')
            if not self.allow_additional_sources and any(not self._matches(use) for use in uses):
                raise ValueError('source.undeclared_use')
            return value
        if claim is not None and self.attribution == 'identified' and getattr(claim, 'attribution', None) not in {'recognized', 'verified', 'identified'}:
            raise ValueError('source.identified_attribution_required')
        if self.require_evidence:
            physical = value.material if isinstance(value, IdentifiedMaterial) else material or value
            if not isinstance(physical, (Material, StagedMaterialRef, ImmutableMaterialRef)):
                raise ValueError('source.evidence_required')
        # Physical evidence is admitted provisionally for domain recognition;
        # any explicitly requested relational constraints still need uses.
        if any((self.family_ids, self.source_group_ids, self.input_role,
                self.qualifications, self.material_identity, self.layout_identity,
                self.semantic_identity, self.evidence_ref, self.asset_id)):
            raise ValueError('source.qualified_use_required')
        return value

    def _matches(self, use):
        coordinate = use.coordinate
        for names, actual in ((self.series_ids, coordinate.source_id),
                              (self.family_ids, coordinate.family_id),
                              (self.source_group_ids, coordinate.source_group_id)):
            if names and actual not in names:
                related = names is self.series_ids and any(
                    coordinate.source_id == feed and coordinate.asset_id == asset and series in names
                    for feed,asset,series in self.declared_relations)
                if not related: return False
        for name in ('issue_id', 'asset_id', 'material_identity', 'layout_identity', 'semantic_identity'):
            required = getattr(self, name)
            if required is not None and getattr(coordinate, name) != required: return False
        if self.input_role and use.input_role != self.input_role: return False
        if self.qualifications and use.qualification not in self.qualifications: return False
        if self.evidence_ref and use.evidence_ref != self.evidence_ref: return False
        if self.attribution == 'identified' and use.qualification not in {
                'identified', 'recognized', 'verified', 'domain_validated',
                'caller_supplied_exact_material_rules', 'reviewed_layout',
                'caller_reviewed_exact_original'}: return False
        if self.require_evidence and coordinate.material_identity is None and use.evidence_ref is None:
            return False
        return True

    def accepts_declaration(self, supplied):
        if supplied is None: return False
        if self.declared_relations and not set(supplied.declared_relations) <= set(self.declared_relations):
            return False
        for name in ('series_ids', 'family_ids', 'source_group_ids'):
            required, actual = getattr(self, name), getattr(supplied, name)
            if required and (not actual or not actual <= required): return False
        for name in ('issue_id', 'asset_id', 'input_role', 'material_identity',
                     'layout_identity', 'semantic_identity', 'evidence_ref'):
            required = getattr(self, name)
            if required is not None and getattr(supplied, name) != required: return False
        if self.qualifications and (not supplied.qualifications or not supplied.qualifications <= self.qualifications): return False
        if self.attribution == 'identified' and supplied.attribution != 'identified': return False
        if self.require_evidence and not supplied.require_evidence: return False
        if not self.allow_additional_sources and supplied.allow_additional_sources: return False
        return True

@dataclass(frozen=True, slots=True)
class PortContract:
    type_id: str
    value_type: type | tuple[type, ...] = object
    role: str | None = None
    required: bool = True
    source: SourceRequirement | None = None
    predicates: tuple[SemanticPredicate, ...] = ()
    outcomes: frozenset[str] = frozenset({'succeeded'})
    alternatives: frozenset[str] = frozenset()
    qualifications: frozenset[str] = frozenset()
    expected_coverage: frozenset[str] = frozenset()
    collection: bool = False
    element_types: tuple[type, ...] = ()
    expected_coordinates: tuple[object, ...] = ()

    def __post_init__(self):
        if not self.type_id or not isinstance(self.value_type, (type, tuple)):
            raise TypeError('port.invalid_type')
        if isinstance(self.value_type,tuple) and (not self.value_type or any(not isinstance(item,type) for item in self.value_type)):
            raise TypeError('port.invalid_type')
        for name in ('outcomes', 'alternatives', 'qualifications', 'expected_coverage'):
            object.__setattr__(self, name, frozenset(getattr(self, name)))
        if not self.outcomes or not self.outcomes <= {'succeeded', 'partial', 'failed', 'unknown', 'cancelled'}:
            raise ValueError('port.invalid_outcomes')
        object.__setattr__(self, 'predicates', tuple(self.predicates))
        object.__setattr__(self, 'element_types', tuple(self.element_types))
        object.__setattr__(self, 'expected_coordinates', tuple(self.expected_coordinates))
        if self.expected_coordinates:
            from stratbox.shared.data.assessment import CoverageCoordinate
            if any(not isinstance(item, CoverageCoordinate) for item in self.expected_coordinates):
                raise TypeError('port.invalid_coverage_coordinate')
            if len({item.identity for item in self.expected_coordinates}) != len(self.expected_coordinates):
                raise ValueError('port.duplicate_coverage_coordinate')

    def validate(self, value):
        if not isinstance(value, self.value_type) or self.value_type in (int, bool, float) and type(value) is not self.value_type:
            raise TypeError('acceptance.value_type_mismatch:' + self.type_id)
        if isinstance(value,tuple) and self.element_types and any(not isinstance(item,self.element_types) for item in value):
            raise TypeError('acceptance.collection_element_type_mismatch')
        if self.source: self.source.validate(value)
        for predicate in self.predicates:
            if not predicate.accepts(value): raise ValueError(predicate.code)
        assessment = getattr(value, 'assessment', None)
        if (self.expected_coverage or self.qualifications or self.expected_coordinates) and assessment is None:
            raise ValueError('acceptance.assessment_required')
        coverage = getattr(assessment, 'coverage', None)
        coverage_facts = set(getattr(coverage, 'facts', ()))
        # Reserved coverage facts come only from exact coverage assessment.
        observed = {item for item in getattr(assessment, 'observed', ())
                    if not item.startswith(('coverage.', 'axis_coverage.', 'membership.', 'source.selected'))}
        if self.expected_coverage and not self.expected_coverage <= observed | coverage_facts:
            raise ValueError('acceptance.coverage_missing')
        if self.expected_coordinates and (coverage is None or not coverage.membership_closed
                or not {item.identity for item in self.expected_coordinates} <= set(coverage.members)):
            raise ValueError('acceptance.coordinate_coverage_missing')
        if self.qualifications and not self.qualifications <= set(getattr(assessment, 'qualifications', ())):
            raise ValueError('acceptance.qualification_missing')
        return value

    def compatible_with(self, producer):
        if not isinstance(producer, PortContract): return False
        accepted = {self.type_id, *self.alternatives}
        mine = self.value_type if isinstance(self.value_type, tuple) else (self.value_type,)
        theirs = producer.value_type if isinstance(producer.value_type, tuple) else (producer.value_type,)
        if not all(any(issubclass(t, m) and (m not in (bool, int, float) or t is m) for m in mine) for t in theirs):
            return False
        if self.source:
            if not self.source.accepts_declaration(producer.source): return False
        return (producer.type_id in accepted and self.role in (None, producer.role)
                and self.collection == producer.collection
                and self.qualifications <= producer.qualifications
                and self.expected_coverage <= producer.expected_coverage
                and {item.identity for item in self.expected_coordinates} <= {item.identity for item in producer.expected_coordinates})

@dataclass(frozen=True, slots=True)
class AcceptanceContract:
    coherent_outputs: tuple[str, ...] = ()
    predicates: tuple[SemanticPredicate, ...] = ()
    required_checks: tuple[str, ...] = ()
    required_effects: tuple[str, ...] = ()
    partial_allowed: bool = False

    def __post_init__(self):
        for name in ('coherent_outputs', 'predicates', 'required_checks', 'required_effects'):
            object.__setattr__(self, name, tuple(getattr(self, name)))

    def validate(self, outputs):
        if not set(self.coherent_outputs) <= outputs.keys():
            raise ValueError('acceptance.coherent_outputs_missing')
        for predicate in self.predicates:
            if not predicate.accepts(outputs): raise ValueError(predicate.code)
        return outputs

    def assess_outputs(self, outputs, *, names=None, settled=()):
        """Settle each output without waiting for unrelated scope completion."""
        names=tuple(names or tuple(dict.fromkeys((*outputs,*self.coherent_outputs))))
        settled=frozenset(settled)
        errors={};pending=set()
        coherent=set(self.coherent_outputs)
        def reject(targets,code):
            for name in targets: errors.setdefault(name,[]).append(code)
        def ready(group): return all(name in outputs or name in settled for name in group)
        if coherent:
            if not ready(coherent): pending.update(coherent)
            elif not coherent<=outputs.keys(): reject(coherent,'acceptance.coherent_outputs_missing')
        for predicate in self.predicates:
            first=predicate.path.split('.',1)[0] if predicate.path else None
            dependencies=(first,) if first in names else names
            targets=coherent if first in coherent else (first,) if first in names else names
            if not ready(dependencies): pending.update(targets)
            elif not predicate.accepts(outputs): reject(targets,predicate.code)
        group_errors={code for name in coherent for code in errors.get(name,())}
        for code in group_errors: reject(coherent,code)
        pending.difference_update(errors)
        return {key:tuple(dict.fromkeys(values)) for key,values in errors.items()},frozenset(pending)
