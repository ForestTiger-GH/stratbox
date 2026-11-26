"""Static domain records with direct immutable command settings."""
from dataclasses import dataclass, field
from datetime import date
from collections.abc import Mapping
from .immutable import freeze
from .methods import MethodRef

@dataclass(frozen=True, slots=True)
class Applicability:
    formats: frozenset[str] = frozenset()
    source_ids: frozenset[str] = frozenset()
    date_from: date | None = None
    date_until: date | None = None
    predicates: tuple = ()
    required_providers: frozenset[str] = frozenset()

    def __post_init__(self):
        for name in ('formats', 'source_ids', 'required_providers'):
            object.__setattr__(self, name, frozenset(getattr(self, name)))
        object.__setattr__(self, 'predicates', tuple(self.predicates))
        if self.date_from and self.date_until and self.date_from > self.date_until:
            raise ValueError('applicability.date_range')

    def assess(self, facts):
        for key, accepted in (('format', self.formats), ('source_id', self.source_ids)):
            if accepted and facts.get(key) is not None and facts[key] not in accepted:
                raise ValueError('applicability.' + key)
        period = facts.get('date')
        if period and (self.date_from and period < self.date_from or self.date_until and period > self.date_until):
            raise ValueError('applicability.date')
        for predicate in self.predicates:
            if hasattr(predicate, 'accepts') and not predicate.accepts(facts):
                raise ValueError('applicability.predicate')
        return self

@dataclass(frozen=True, slots=True)
class CommandSpec:
    method: MethodRef
    settings: object = None
    applicability: Applicability = field(default_factory=Applicability)

    def __post_init__(self):
        if not isinstance(self.method, MethodRef) or not isinstance(self.applicability, Applicability):
            raise TypeError('domain.invalid_command_spec')
        object.__setattr__(self, 'settings', freeze(self.settings))

@dataclass(frozen=True, slots=True)
class PublicationSpec:
    id: str
    title: str = ''
    landing_url: str | None = None
    formats: frozenset[str] = frozenset()
    frequency: str | None = None
    issue_model: str = 'publisher'
    settings: object = None
    commands: Mapping[str, CommandSpec] = field(default_factory=dict)

    def __post_init__(self):
        _commands(self)
        object.__setattr__(self, 'formats', frozenset(self.formats))
        object.__setattr__(self, 'settings', freeze(self.settings))

@dataclass(frozen=True, slots=True)
class ObservationSemantics:
    grain: tuple[str, ...] = ()
    period_model: str = ''
    measure_kind: str | None = None
    units: object = None
    settings: object = None

    def __post_init__(self):
        object.__setattr__(self, 'grain', tuple(self.grain))
        object.__setattr__(self, 'units', freeze(self.units))
        object.__setattr__(self, 'settings', freeze(self.settings))


def _commands(record):
    commands = freeze(record.commands)
    if any(not key.startswith('command.') or not isinstance(value, CommandSpec) for key, value in commands.items()):
        raise TypeError('domain.invalid_commands')
    object.__setattr__(record, 'commands', commands)

@dataclass(frozen=True, slots=True)
class SeriesSpec:
    id: str
    publication: object
    semantics: object
    commands: Mapping[str, CommandSpec]

    def __post_init__(self):
        if not self.id:
            raise ValueError('domain.id_required')
        _commands(self)
        object.__setattr__(self, 'publication', freeze(self.publication))
        object.__setattr__(self, 'semantics', freeze(self.semantics))

@dataclass(frozen=True, slots=True)
class CalculationSpec:
    id: str
    commands: Mapping[str, CommandSpec]
    inputs: Mapping[str, object] = field(default_factory=dict)
    semantics: object = None
    input_topology: str = 'independent_series'
    settings: object = None

    def __post_init__(self):
        _commands(self)
        if self.input_topology not in {'single_series', 'independent_series', 'coupled'}:
            raise ValueError('calculation.input_topology')
        for name in ('inputs', 'semantics', 'settings'):
            object.__setattr__(self, name, freeze(getattr(self, name)))

@dataclass(frozen=True, slots=True)
class ProductSpec:
    id: str
    commands: Mapping[str, CommandSpec]
    inputs: Mapping[str, object] = field(default_factory=dict)
    settings: object = None
    semantics: object = None

    def __post_init__(self):
        _commands(self)
        for name in ('inputs', 'settings', 'semantics'):
            object.__setattr__(self, name, freeze(getattr(self, name)))

@dataclass(frozen=True, slots=True)
class DomainSpec:
    id: str
    common: Mapping[str, object]
    series: Mapping[str, SeriesSpec]
    calculations: Mapping[str, CalculationSpec] = field(default_factory=dict)
    products: Mapping[str, ProductSpec] = field(default_factory=dict)

    def __post_init__(self):
        if not self.id:
            raise ValueError('domain.id_required')
        for name, cls in (('series', SeriesSpec), ('calculations', CalculationSpec), ('products', ProductSpec)):
            values = freeze(getattr(self, name))
            if any(not isinstance(value, cls) or key != value.id for key, value in values.items()):
                raise ValueError('domain.record_identity:' + name)
            object.__setattr__(self, name, values)
        object.__setattr__(self, 'common', freeze(self.common))
