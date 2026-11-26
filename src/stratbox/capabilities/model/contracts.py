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

    def __post_init__(self):
        object.__setattr__(self, 'series_ids', frozenset(self.series_ids))
        if self.attribution not in {'identified', 'asserted', 'optional'}:
            raise ValueError('source.invalid_attribution')

    def validate(self, value):
        source = getattr(value, 'source_id', getattr(value, 'series_id', None))
        issue = getattr(value, 'issue_id', None)
        claim = getattr(value, 'claim', None)
        material = getattr(value, 'material', None)
        if claim is not None:
            source, issue = claim.source_id, claim.issue_id
        if source is None and material is not None:
            source = getattr(material, 'source_id', None)
        if self.series_ids and source is not None and source not in self.series_ids:
            raise ValueError('source.context_conflict')
        if self.series_ids and source is None and self.attribution == 'identified':
            raise ValueError('source.attribution_required')
        if self.issue_id and issue != self.issue_id:
            raise ValueError('source.issue_conflict')
        if claim is not None and self.attribution == 'identified' and getattr(claim, 'attribution', None) not in {'recognized', 'verified', 'identified'}:
            raise ValueError('source.identified_attribution_required')
        return value

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

    def __post_init__(self):
        if not self.type_id or not isinstance(self.value_type, (type, tuple)):
            raise TypeError('port.invalid_type')
        for name in ('outcomes', 'alternatives', 'qualifications', 'expected_coverage'):
            object.__setattr__(self, name, frozenset(getattr(self, name)))
        if not self.outcomes or not self.outcomes <= {'succeeded', 'partial'}:
            raise ValueError('port.invalid_outcomes')

    def validate(self, value):
        if not isinstance(value, self.value_type) or self.value_type in (int, bool, float) and type(value) is not self.value_type:
            raise TypeError('acceptance.value_type_mismatch:' + self.type_id)
        if self.source: self.source.validate(value)
        for predicate in self.predicates:
            if not predicate.accepts(value): raise ValueError(predicate.code)
        assessment = getattr(value, 'assessment', None)
        if self.expected_coverage and assessment is not None and not self.expected_coverage <= set(getattr(assessment, 'observed', ())):
            raise ValueError('acceptance.coverage_missing')
        if self.qualifications and assessment is not None and not self.qualifications <= set(getattr(assessment, 'qualifications', ())):
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
            supplied = producer.source
            if supplied is None or self.source.series_ids and (not supplied.series_ids or not supplied.series_ids <= self.source.series_ids): return False
            if self.source.issue_id and supplied.issue_id != self.source.issue_id: return False
            if self.source.attribution == 'identified' and supplied.attribution != 'identified': return False
        return (producer.type_id in accepted and self.role in (None, producer.role)
                and self.collection == producer.collection
                and self.qualifications <= producer.qualifications
                and self.expected_coverage <= producer.expected_coverage)

@dataclass(frozen=True, slots=True)
class AcceptanceContract:
    coherent_outputs: tuple[str, ...] = ()
    predicates: tuple[SemanticPredicate, ...] = ()
    required_checks: tuple[str, ...] = ()
    required_effects: tuple[str, ...] = ()
    partial_allowed: bool = False

    def validate(self, outputs):
        if not set(self.coherent_outputs) <= outputs.keys():
            raise ValueError('acceptance.coherent_outputs_missing')
        for predicate in self.predicates:
            if not predicate.accepts(outputs): raise ValueError(predicate.code)
        return outputs
