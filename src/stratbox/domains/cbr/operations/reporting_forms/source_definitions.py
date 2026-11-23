"""Source-local extraction, normalization and portable form history contracts."""

from stratbox.core.execution.contracts import OperationDefinition
from stratbox.core.execution.semantics import InputPort, OperationSemantics, OutputPort, ProcessingStage
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.snapshots import DatasetSnapshot

from stratbox.domains.cbr.tables.reporting_forms.contracts import DiscoverFormsRequest, ExtractFormRequest, FormFlakes, FormFlakeSnapshotRequest, FormInventory, FormSnapshot, FormHistoryRequest, NormalizeFormRequest, FormFlakeExport, RenderFormFlakesRequest, ReadFormFlakeExportRequest
from stratbox.domains.cbr.analytics.reporting_forms.contracts import FormData
from stratbox.domains.cbr.operations.reporting_forms.contracts import FormResultSnapshotRequest
from stratbox.domains.cbr.products.reporting_forms.contracts import FormViews
from stratbox.domains.cbr.operations.reporting_forms.definitions import _TABLES

_BYTES = DataContract("material.payload", 1)
_ORIGINAL = DataContract("cbr.forms.original", 1, DataRole.ORIGINALS)
_PAYLOAD = DataContract("source.payload", 1, DataRole.ORIGINALS)
_FLAKES = DataContract("cbr.forms.flakes", 1, DataRole.EXTRACTS)
_SNAPSHOT = DataContract("dataset.snapshot", 1)
_NORMALIZED = DataContract("cbr.forms.snapshot", 1, DataRole.EXTRACTS)
_DATA = DataContract("cbr.forms.data", 1, DataRole.INTEGRATED)
_VIEWS = DataContract("cbr.forms.views", 1, DataRole.PRODUCTS)
_OUTCOMES = frozenset({"succeeded", "partial"})

DISCOVER = OperationDefinition("cbr.forms.discover_sources", 1, "cbr-forms-index-1",
    DiscoverFormsRequest, FormInventory, optional_capabilities=frozenset({"http"}), limits=_TABLES,
    processing=OperationSemantics((ProcessingStage.DISCOVER,),
        inputs=(InputPort("index", _BYTES, path="payload", required=False, alternatives=(_PAYLOAD,)),),
        outputs=(OutputPort("inventory", DataContract("cbr.forms.inventory", 1)),),
        parameters=("date_from", "date_to", "form_codes"),
        summary="Select published reporting-form archives from a supplied or acquired official index."))

EXTRACT = OperationDefinition("cbr.forms.extract", 1, "cbr-forms-all-dbf-1",
    ExtractFormRequest, FormFlakes, optional_capabilities=frozenset({"archive_decoder"}),
    partial_allowed=True, limits=_TABLES,
    processing=OperationSemantics((ProcessingStage.EXTRACT,),
        inputs=(InputPort("source", _BYTES, path="payload", alternatives=(_ORIGINAL, _PAYLOAD)),),
        outputs=(OutputPort("flakes", _FLAKES, outcomes=_OUTCOMES),),
        parameters=("key", "text_encoding", "encoding_overrides", "strict", "member_name"),
        summary="Decode every supported DBF and retain exact bytes and inventory for every regular archive member."))

NORMALIZE = OperationDefinition("cbr.forms.normalize", 1, "cbr-forms-source-projection-2",
    NormalizeFormRequest, FormSnapshot, limits=_TABLES,
    processing=OperationSemantics((ProcessingStage.EXTRACT,),
        inputs=(InputPort("flakes", _FLAKES, path="flakes"),),
        outputs=(OutputPort("snapshot", _NORMALIZED),), parameters=("include_deleted",),
        summary="Select a supported physical form table and apply explicit normalization to decoded flakes."))

FLAKE_SNAPSHOT = OperationDefinition("cbr.forms.flake_snapshot", 1, "cbr-forms-flake-snapshot-1",
    FormFlakeSnapshotRequest, DatasetSnapshot, limits=_TABLES,
    processing=OperationSemantics((ProcessingStage.RENDER,),
        inputs=(InputPort("flakes", _FLAKES, path="flakes", outcomes=_OUTCOMES),),
        outputs=(OutputPort("snapshot", _SNAPSHOT),), parameters=("dataset_id", "version_id"),
        summary="Encode one form release as typed flake, schema, flag, identity and original-member tables."))

RESTORE_FLAKES = OperationDefinition("cbr.forms.restore_flakes", 1, "cbr-forms-flake-replay-1",
    DatasetSnapshot, FormFlakes, partial_allowed=True, limits=_TABLES,
    processing=OperationSemantics((ProcessingStage.READ_EXTRACT,),
        inputs=(InputPort("snapshot", _SNAPSHOT),),
        outputs=(OutputPort("flakes", _FLAKES, outcomes=_OUTCOMES),),
        summary="Restore a complete form flake snapshot without parsing original DBF bytes again."))

RESULT_SNAPSHOT = OperationDefinition("cbr.forms.result_snapshot", 1, "cbr-forms-result-snapshot-1",
    FormResultSnapshotRequest, DatasetSnapshot, limits=_TABLES,
    processing=OperationSemantics((ProcessingStage.RENDER,),
        inputs=(InputPort("result", _NORMALIZED, path="value", alternatives=(_DATA, _VIEWS)),),
        outputs=(OutputPort("snapshot", _SNAPSHOT),), parameters=("dataset_id", "version_id"),
        summary="Preserve normalized rows, calculated data or prepared views with exact scalar types and computation lineage."))


def _restore(name, result_type, contract):
    return OperationDefinition("cbr.forms.restore_" + name, 1, "cbr-forms-restore-" + name + "-1",
        DatasetSnapshot, result_type, limits=_TABLES,
        processing=OperationSemantics((ProcessingStage.READ_EXTRACT,),
            inputs=(InputPort("snapshot", _SNAPSHOT),), outputs=(OutputPort("result", contract),),
            summary="Validate and restore the requested form result from a portable dataset snapshot."))


RESTORE_NORMALIZED = _restore("normalized", FormSnapshot, _NORMALIZED)
RESTORE_DATA = _restore("data", FormData, _DATA)
RESTORE_VIEWS = _restore("views", FormViews, _VIEWS)

HISTORY = OperationDefinition("cbr.forms.build_history", 1, "cbr-forms-source-history-2",
    FormHistoryRequest, DatasetSnapshot, limits=_TABLES,
    processing=OperationSemantics((ProcessingStage.EXTRACT,),
        inputs=(InputPort("snapshots", DataContract("cbr.forms.snapshots", 1, DataRole.EXTRACTS), path="snapshots"),),
        outputs=(OutputPort("snapshot", _SNAPSHOT),), parameters=("dataset_id", "version_id"),
        summary="Pin a unique selected history of normalized form releases; duplicate releases require explicit resolution."))

RESTORE_HISTORY = OperationDefinition("cbr.forms.restore_history", 1, "cbr-forms-history-replay-1",
    DatasetSnapshot, tuple, limits=_TABLES,
    processing=OperationSemantics((ProcessingStage.READ_EXTRACT,),
        inputs=(InputPort("snapshot", _SNAPSHOT),),
        outputs=(OutputPort("snapshots", DataContract("cbr.forms.snapshots", 1, DataRole.EXTRACTS)),),
        summary="Restore normalized release history for subsequent financial model evaluation."))

RENDER_FLAKES = OperationDefinition("cbr.forms.render_flakes", 1, "cbr-forms-csv-flakes-1",
    RenderFormFlakesRequest, FormFlakeExport, partial_allowed=True, limits=_TABLES,
    processing=OperationSemantics((ProcessingStage.RENDER,),
        inputs=(InputPort("flakes", _FLAKES, path="flakes", outcomes=_OUTCOMES),),
        outputs=(OutputPort("files", DataContract("cbr.forms.flake_files", 1, DataRole.EXTRACTS), path="files", outcomes=_OUTCOMES),
                 OutputPort("manifest", DataContract("material.collection", 1), path="manifest", outcomes=_OUTCOMES)),
        parameters=("prefix", "include_member_originals"),
        summary="Render all decoded physical DBF records to CSV with complete schema and member evidence for neutral packaging."))

READ_FLAKE_EXPORT = OperationDefinition("cbr.forms.read_flake_export", 1, "cbr-forms-csv-replay-1",
    ReadFormFlakeExportRequest, FormFlakes, partial_allowed=True, limits=_TABLES,
    processing=OperationSemantics((ProcessingStage.READ_EXTRACT,),
        inputs=(InputPort("manifest", DataContract("material.collection", 1), path="manifest", outcomes=_OUTCOMES),),
        outputs=(OutputPort("flakes", _FLAKES, outcomes=_OUTCOMES),), parameters=("files",),
        summary="Validate a complete CSV, descriptor and member-original collection and resume without re-parsing DBF."))
