"""Universal material operations, admitted independently of domain registration."""
from stratbox.core.execution.catalog import OperationRef, OperationRegistration

REGISTRATION = OperationRegistration("core.materials", tuple(
    OperationRef(name, 1, f"stratbox.core.operations.materials.definitions:{definition}",
                 f"stratbox.core.operations.materials.operations:{handler}")
    for name, definition, handler in (
        ("material.read_location", "READ_LOCATION", "read_location"),
        ("material.transfer", "TRANSFER", "transfer_material"),
        ("material.save_artifact", "SAVE_ARTIFACT", "save_artifact"),
        ("material.read_artifact", "READ_ARTIFACT", "read_artifact"),
        ("material.transfer_artifact", "TRANSFER_ARTIFACT", "transfer_artifact"),
    )
) + (OperationRef("material.archive", 1, "stratbox.core.operations.materials.archive_definitions:ARCHIVE",
                  "stratbox.core.operations.materials.archive:archive_materials"),))
