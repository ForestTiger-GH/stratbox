"""Immutable standard definitions, with explicit temporary overlays."""
from dataclasses import dataclass
from collections.abc import Mapping
from ..model import CapabilityDefinition, freeze

@dataclass(frozen=True)
class Catalog:
    definitions: Mapping[str, CapabilityDefinition]

    def __post_init__(self):
        values = freeze(self.definitions)
        if any(not isinstance(v, CapabilityDefinition) or key != v.id for key, v in values.items()):
            raise ValueError('catalog.definition_identity')
        object.__setattr__(self, 'definitions', values)

    def get(self, identifier):
        try: return self.definitions[identifier]
        except KeyError: raise ValueError('catalog.unknown_capability:' + identifier) from None

    def with_definitions(self, *definitions):
        values = dict(self.definitions)
        for definition in definitions:
            if definition.id in values and values[definition.id] != definition:
                raise ValueError('catalog.conflicting_definition:' + definition.id)
            values[definition.id] = definition
        return Catalog(values)

    def describe(self, identifier):
        from ..model.immutable import canonical
        return canonical(self.get(identifier))

    def list(self, *, kind=None):
        return tuple(v for v in self.definitions.values() if kind is None or v.kind == kind)


def standard_catalog():
    from ..commands.standard import COMMANDS
    from ..operations.standard import OPERATIONS
    from ..scenarios.standard import SCENARIOS
    from ..cascades.standard import CASCADES
    values = (*COMMANDS, *OPERATIONS, *SCENARIOS, *CASCADES)
    if len({v.id for v in values}) != len(values): raise ValueError('catalog.duplicate_id')
    return Catalog({v.id: v for v in values})
