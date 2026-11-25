"""Pure retained 1-YUR workbook evidence, independent of decoder backends."""
from dataclasses import dataclass

from stratbox.shared.data.snapshots import SnapshotCoverage
from stratbox.shared.data.workbooks import WorkbookExtract
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.identity import ByteIdentity

from ...publications.contracts import ReleaseContext

PROFILE = "fns.1yur.all-workbook-cells"


@dataclass(frozen=True, slots=True)
class MemberInventory:
    name: str
    identity: ByteIdentity
    disposition: str
    reason: str


@dataclass(frozen=True, slots=True)
class WorkbookBundle:
    context: ReleaseContext
    source_identity: ByteIdentity
    container_format: str
    members: tuple[tuple[str, WorkbookExtract], ...]
    inventory: tuple[MemberInventory, ...]
    lineage: tuple[UsedInputReceipt, ...]
    coverage: SnapshotCoverage
    qualifications: tuple[str, ...]
    profile_id: str = PROFILE

    @property
    def identity(self):
        from .snapshots import flake_snapshot
        return flake_snapshot(self).identity
