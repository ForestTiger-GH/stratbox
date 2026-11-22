"""Manifest operation metadata, loadable without executable handlers."""
from stratbox.core.execution.contracts import OperationDefinition
from stratbox.core.execution.semantics import InputPort, OperationSemantics, OutputPort, ProcessingStage
from stratbox.shared.data.processing import DataContract
from stratbox.shared.data.representation import Representation
from stratbox.shared.material_collections import CollectionManifest
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
