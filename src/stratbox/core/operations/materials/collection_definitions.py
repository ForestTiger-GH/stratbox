"""Manifest operation metadata, loadable without executable handlers."""

from stratbox.core.registry.operations import definition as _registry_definition
from stratbox.shared.data.processing import DataContract
from stratbox.shared.data.representation import Representation
from stratbox.shared.material_collections import CollectionManifest
from .definitions import LIMITS

COLLECTION = DataContract("material.collection")
ENCODED = DataContract("material.collection.json")
SERIALIZE = _registry_definition('material.serialize_collection', 1)
READ = _registry_definition('material.read_collection', 1)
