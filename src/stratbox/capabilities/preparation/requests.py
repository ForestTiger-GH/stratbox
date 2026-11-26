"""One request model for direct, temporary and composed invocation."""
from dataclasses import dataclass, field
from collections.abc import Mapping
from ..model import freeze

@dataclass(frozen=True, slots=True)
class InvocationRequest:
    capability_id: str
    inputs: Mapping[str, object] = field(default_factory=dict)
    parameters: Mapping[str, object] = field(default_factory=dict)
    target: object = None
    outputs: tuple[str, ...] | None = None

    def __post_init__(self):
        object.__setattr__(self, 'inputs', freeze(self.inputs))
        object.__setattr__(self, 'parameters', freeze(self.parameters))
