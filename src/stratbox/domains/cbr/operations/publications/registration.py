"""Publisher operations, collected by the sole CBR operation owner."""
from stratbox.core.execution.catalog import OperationRef

_BASE = "stratbox.domains.cbr.operations.publications"
OPERATIONS = tuple(OperationRef("cbr.publications." + name, 1,
    _BASE + ".definitions:" + definition, _BASE + ".handlers:" + name)
    for name, definition in (("list_sources", "LIST"), ("discover", "DISCOVER"), ("identify", "IDENTIFY"),
                            ("select", "SELECT"), ("acquire", "ACQUIRE"), ("assess_updates", "ASSESS_UPDATES")))
STAGES = ()
