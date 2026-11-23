"""Registry, discovery and original-format admission at the publisher boundary."""
from stratbox.core.execution import OperationDefinition
from stratbox.core.execution.semantics import InputPort, OperationSemantics, OutputPort, ProcessingStage
from stratbox.core.limits import ExecutionBudget
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.domains.cbr.publications.contracts import DiscoverRequest, IdentifiedOriginal, IdentifyRequest, ListSourcesRequest, PublicationInventory
from stratbox.domains.cbr.publications.contracts import (AcquirePublicationRequest, AssessUpdatesRequest,
    PublicationAsset, PublicationUpdatePlan, SelectPublicationRequest)

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

SELECT = OperationDefinition("cbr.publications.select", 1, "cbr-publication-selection-v1",
    SelectPublicationRequest, PublicationAsset,
    processing=OperationSemantics((ProcessingStage.INSPECT,),
        inputs=(InputPort("inventory", DataContract("cbr.publications.inventory"), "inventory"),),
        outputs=(OutputPort("asset", DataContract("cbr.publications.asset")),),
        parameters=("issue_id", "format", "asset_id", "url"),
        summary="Select one publication and one physical route; ambiguous candidates require an explicit selection."))
ACQUIRE = OperationDefinition("cbr.publications.acquire", 1, "cbr-publication-acquisition-v1",
    AcquirePublicationRequest, IdentifiedOriginal, required_capabilities=frozenset({"http"}), limits=LIMITS,
    processing=OperationSemantics((ProcessingStage.ACQUIRE, ProcessingStage.INSPECT),
        inputs=(InputPort("asset", DataContract("cbr.publications.asset"), "asset"),),
        outputs=IDENTIFY.processing.outputs, parameters=("issue_id",), composition=True,
        summary="Acquire and admit one selected original with explicit issue or capture context."))
ASSESS_UPDATES = OperationDefinition("cbr.publications.assess_updates", 1, "cbr-publication-update-plan-v1",
    AssessUpdatesRequest, PublicationUpdatePlan,
    processing=OperationSemantics((ProcessingStage.COMPARE,),
        inputs=(InputPort("original", DataContract("cbr.publication.original", 1, DataRole.ORIGINALS), "original"),),
        outputs=(OutputPort("plan", DataContract("cbr.publications.update_plan")),),
        parameters=("processing_signature", "checkpoint", "target", "destinations"),
        summary="Separate confirmed byte changes, processing changes and destination readiness without executing effects."))
