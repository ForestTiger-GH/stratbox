"""Latent continuous SORS model.

The package intentionally keeps its ``__init__`` lightweight.  Publication-level
closure imports strict interval primitives, while optimization imports both layers;
eager re-exports here would create a circular dependency between those domains.
"""

from stratbox.macrobanks.cbr_sors_restoration.strict.certification import (
    IntervalCertification,
    certify_interval,
)
from stratbox.macrobanks.cbr_sors_restoration.strict.interval_closure import (
    SorsIntervalClosureConflictError,
    SorsIntervalClosureResult,
    SorsIntervalClosureState,
    run_interval_closure,
)
from stratbox.macrobanks.cbr_sors_restoration.strict.quantities import (
    SorsQuantityGraph,
    build_quantity_graph,
)

__all__ = [
    'IntervalCertification',
    'SorsIntervalClosureConflictError',
    'SorsIntervalClosureResult',
    'SorsIntervalClosureState',
    'SorsQuantityGraph',
    'build_quantity_graph',
    'certify_interval',
    'run_interval_closure',
]
