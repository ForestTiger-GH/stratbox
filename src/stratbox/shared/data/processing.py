"""Storage-independent data roles and explicit, editioned semantic schemas."""

from dataclasses import dataclass
from enum import Enum
import re

_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", re.ASCII)


class DataRole(str, Enum):
    ORIGINALS = "originals"
    READABLE = "readable"
    EXTRACTS = "extracts"
    INTEGRATED = "integrated"
    PRODUCTS = "products"


@dataclass(frozen=True, slots=True)
class DataContract:
    """A semantic schema identity, independent of format and physical location.

    A None role identifies a control value such as an index or comparison.
    Equal role names alone never establish schema compatibility.
    """

    schema_id: str
    version: int = 1
    role: DataRole | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.schema_id, str) or not _IDENTIFIER.fullmatch(
            self.schema_id
        ):
            raise ValueError("processing.invalid_schema")
        if type(self.version) is not int or self.version < 1:
            raise ValueError("processing.invalid_schema_version")
        if self.role is not None and not isinstance(self.role, DataRole):
            raise ValueError("processing.invalid_role")
