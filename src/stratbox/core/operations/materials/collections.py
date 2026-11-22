"""Encode and read complete material manifests through the common runner."""
from stratbox.core.execution import OperationDefinition, OperationFailure, run
from stratbox.core.execution.semantics import InputPort, OperationSemantics, OutputPort, ProcessingStage
from stratbox.shared.data.processing import DataContract
from stratbox.shared.data.representation import Representation
from stratbox.shared.material_collections import CollectionManifest, decode_collection, encode_collection
from .definitions import LIMITS

COLLECTION = DataContract("material.collection")
ENCODED = DataContract("material.collection.json")
SERIALIZE = OperationDefinition("material.serialize_collection", 1, "material-collection-v1",
    CollectionManifest, Representation, limits=LIMITS,
    processing=OperationSemantics((ProcessingStage.RENDER,),
        inputs=(InputPort("collection", COLLECTION),), outputs=(OutputPort("manifest", ENCODED),),
        summary="Encode logical members, selection outcomes and coverage independently of store bindings."))
READ = OperationDefinition("material.read_collection", 1, "material-collection-v1",
    Representation, CollectionManifest, limits=LIMITS,
    processing=OperationSemantics((ProcessingStage.READ_EXTRACT,),
        inputs=(InputPort("manifest", ENCODED),), outputs=(OutputPort("collection", COLLECTION),),
        summary="Restore a validated manifest without interpreting a batch as complete publisher history."))


def serialize_collection(request, *, context=None):
    def work(req, invocation):
        invocation.stage("encode")
        try:
            data = encode_collection(req)
        except ValueError as error:
            raise OperationFailure(str(error)) from None
        invocation.budget.charge("output_bytes", len(data))
        result = Representation("material.collection.json", 1, "application/json", data, "utf-8")
        invocation.record(result.identity, parameters={"collection": req.identity.sha256})
        return result
    return run(SERIALIZE, request, work, context=context)


def read_collection(request, *, context=None):
    def work(req, invocation):
        invocation.stage("decode")
        if (req.profile_id, req.version, req.media_type, req.encoding) != (
                "material.collection.json", 1, "application/json", "utf-8"):
            raise OperationFailure("collection.representation_invalid")
        invocation.budget.charge("input_bytes", len(req.data))
        try:
            value = decode_collection(req.data)
        except ValueError as error:
            raise OperationFailure(str(error)) from None
        from stratbox.shared.evidence import UsedInputReceipt
        invocation.use(UsedInputReceipt("collection_manifest", req.identity, req.media_type, "inline"))
        invocation.record(value.identity)
        return value
    return run(READ, request, work, context=context)
