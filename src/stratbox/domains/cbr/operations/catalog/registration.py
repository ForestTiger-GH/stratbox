"""Source-scoped catalog operations are part of the single CBR registration."""
from stratbox.core.execution.catalog import OperationRef

_BASE = "stratbox.domains.cbr.operations.catalog"
OPERATIONS = tuple(OperationRef("cbr." + name, 1, _BASE + ".definitions:" + definition,
                                _BASE + ".handlers:" + name)
                   for name, definition in (("describe_source", "DESCRIBE_SOURCE"), ("describe_family", "DESCRIBE_FAMILY")))
STAGES = ()
