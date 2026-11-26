"""Opaque targets select knowledge without exposing it to standard graphs."""
from dataclasses import dataclass
@dataclass(frozen=True, slots=True)
class SeriesTarget:
    id: str
@dataclass(frozen=True, slots=True)
class FeedTarget:
    id: str
@dataclass(frozen=True, slots=True)
class CalculationTarget:
    id: str
@dataclass(frozen=True, slots=True)
class ProductTarget:
    id: str
