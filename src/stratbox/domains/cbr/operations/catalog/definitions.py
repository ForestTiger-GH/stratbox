"""Catalog descriptions are read-only projections of existing registrations."""
from stratbox.core.execution import OperationDefinition
from stratbox.core.execution.semantics import OperationSemantics, OutputPort, ProcessingStage
from stratbox.shared.data.processing import DataContract
from .contracts import DescribeSourceRequest, DescribeFamilyRequest, SourceDescription, FamilyDescription

DESCRIBE_SOURCE = OperationDefinition("cbr.describe_source", 1, "cbr-scoped-source-catalog-1", DescribeSourceRequest, SourceDescription,
    processing=OperationSemantics((ProcessingStage.INSPECT,),
        outputs=(OutputPort("source", DataContract("cbr.catalog.source")),),
        parameters=("series_id", "format", "table_id", "edition"),
        summary="Describe reviewed source tables, editions, exact operation contracts and source-specific gaps."))
DESCRIBE_FAMILY = OperationDefinition("cbr.describe_family", 1, "cbr-scoped-family-catalog-1", DescribeFamilyRequest, FamilyDescription,
    processing=OperationSemantics((ProcessingStage.INSPECT,),
        outputs=(OutputPort("family", DataContract("cbr.catalog.family")),),
        parameters=("family_id",),
        summary="Describe each publication's processing scope and multi-source methods without flattening coverage."))
