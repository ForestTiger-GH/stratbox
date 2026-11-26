"""Explicit lazy trusted-code references; there is no method registry."""
from dataclasses import dataclass
from importlib import import_module

@dataclass(frozen=True, slots=True)
class MethodRef:
    locator: str

    def __post_init__(self):
        module, sep, name = self.locator.partition(':')
        if not sep or not all(p.isidentifier() and not p.startswith('_') for p in module.split('.')) or not name.isidentifier() or name.startswith('_'):
            raise ValueError('method.invalid_locator')

    def resolve(self):
        module, name = self.locator.split(':')
        result = getattr(import_module(module), name)
        if not callable(result):
            raise TypeError('method.not_callable')
        return result
