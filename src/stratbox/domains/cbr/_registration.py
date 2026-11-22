"""Publisher-wide publication operations shared by the CBR family owners."""
from stratbox.core.execution.catalog import OperationRef, OperationRegistration

REGISTRATION = OperationRegistration("cbr", tuple(
    OperationRef("cbr.publications." + name, 1,
        "stratbox.domains.cbr.publications.definitions:" + definition,
        "stratbox.domains.cbr.publications.operations:" + name)
    for name, definition in (("list_sources", "LIST"), ("discover", "DISCOVER"), ("identify", "IDENTIFY"))
))
