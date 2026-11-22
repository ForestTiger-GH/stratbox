"""Encode and read complete material manifests through the common runner."""
from stratbox.core.execution import OperationFailure, run
from stratbox.shared.data.representation import Representation
from stratbox.shared.material_collections import CollectionManifest, decode_collection, encode_collection
from .collection_definitions import READ, SERIALIZE


def serialize_collection(request, *, context=None):
    def work(req, invocation):
        invocation.stage("encode")
        try:
            data = encode_collection(req)
        except ValueError as error:
            raise OperationFailure(str(error)) from None
        result = Representation("material.collection.json", 1, "application/json", data, "utf-8")
        invocation.account_output(result.identity)
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
