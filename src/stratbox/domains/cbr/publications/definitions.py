"""Registry, discovery and original-format admission at the publisher boundary."""
from stratbox.core.execution import OperationDefinition
from stratbox.core.execution.semantics import InputPort, OperationSemantics, OutputPort, ProcessingStage
from stratbox.core.limits import ExecutionBudget
from stratbox.shared.data.processing import DataContract, DataRole
from .contracts import DiscoverRequest, IdentifiedOriginal, IdentifyRequest, ListSourcesRequest, PublicationInventory

LIMITS = ExecutionBudget(input_bytes=256 * 1024**2, output_bytes=256 * 1024**2,
                        temporary_bytes=256 * 1024**2, cells=5_000_000)
LIST = OperationDefinition("cbr.publications.list_sources", 1, "cbr-publication-registry-v1",
    ListSourcesRequest, tuple,
    processing=OperationSemantics((ProcessingStage.DISCOVER,),
        outputs=(OutputPort("sources", DataContract("cbr.publications.series")),), parameters=("family_id",),
        summary="List logical publication families and processing profiles independently of acquisition routes."))
DISCOVER = OperationDefinition("cbr.publications.discover", 1, "cbr-publication-inventory-v1",
    DiscoverRequest, PublicationInventory, optional_capabilities=frozenset({"http"}), limits=LIMITS,
    processing=OperationSemantics((ProcessingStage.DISCOVER,),
        inputs=(InputPort("index", DataContract("material.payload"), "index", required=False,
                          alternatives=(DataContract("source.payload", 1, DataRole.ORIGINALS),)),),
        outputs=(OutputPort("inventory", DataContract("cbr.publications.inventory")),),
        parameters=("series_id", "page_url", "max_links"),
        summary="Enumerate registered routes or matching publisher links with explicit unknown historical coverage."))
IDENTIFY = OperationDefinition("cbr.publications.identify", 1, "cbr-original-admission-v1",
    IdentifyRequest, IdentifiedOriginal, limits=LIMITS,
    processing=OperationSemantics((ProcessingStage.INSPECT,),
        inputs=(InputPort("material", DataContract("material.payload"), "payload",
                          alternatives=(DataContract("source.payload", 1, DataRole.ORIGINALS),)),),
        outputs=(OutputPort("original", DataContract("cbr.publication.original", 1, DataRole.ORIGINALS)),
                 OutputPort("payload", DataContract("source.payload", 1, DataRole.ORIGINALS), "payload"),
                 OutputPort("artifact", DataContract("material.artifact"), "artifact")),
        parameters=("series_id", "issue_id", "format", "asset_id"),
        summary="Validate a supplied format and retain explicit series/issue context without asserting network provenance."))
