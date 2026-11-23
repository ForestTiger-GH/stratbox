"""Statistical operation references, owned by the publisher CBR registration."""
from stratbox.core.execution.catalog import OperationRef

_BASE = "stratbox.domains.cbr.operations.statistics"
_ITEMS = (
    ("cbr.tables.extract", "EXTRACT", "extract"), ("cbr.tables.validate", "VALIDATE", "validate"),
    ("cbr.tables.compare", "COMPARE", "compare"), ("cbr.tables.readable", "READABLE", "readable"),
    ("cbr.tables.flake_snapshot", "FLAKE_SNAPSHOT", "build_flake_snapshot"),
    ("cbr.tables.read_flake_snapshot", "READ_FLAKE_SNAPSHOT", "read_flake_snapshot"),
    ("cbr.statistics.align", "ALIGN", "align"),
    ("cbr.statistics.calculate_change", "CHANGE", "calculate_change"),
    ("cbr.statistics.calculate_share", "SHARE", "calculate_share"),
    ("cbr.statistics.build_view", "BUILD_VIEW", "build_view"), ("cbr.statistics.render_view", "RENDER_VIEW", "render_view"),
    ("cbr.statistics.dataset_snapshot", "DATASET_SNAPSHOT", "build_dataset_snapshot"),
    ("cbr.statistics.read_dataset_snapshot", "READ_DATASET_SNAPSHOT", "read_dataset_snapshot"),
    ("cbr.statistics.view_snapshot", "VIEW_SNAPSHOT", "build_view_snapshot"),
    ("cbr.statistics.read_view_snapshot", "READ_VIEW_SNAPSHOT", "read_view_snapshot"),
)
OPERATIONS = tuple(OperationRef(name, 1, _BASE + ".definitions:" + definition, _BASE + ".handlers:" + handler)
                   for name, definition, handler in _ITEMS)
STAGES = ()
