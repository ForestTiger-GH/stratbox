"""Durable effect outcomes, recorded before any potentially uncertain mutation."""
from pathlib import Path
from hashlib import sha256
from threading import RLock
import json
import os
import tempfile

from stratbox.shared.data.values import canonical_tree, restore_tree


class FileEffectState:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

    def _path(self, identity):
        digest = sha256(identity.encode()).hexdigest()
        parent = self.directory / digest[:2]
        parent.mkdir(exist_ok=True)
        return parent / (digest + ".json")

    def get(self, effect_id):
        from .service import EffectReceipt
        path = self._path(effect_id)
        with self._lock:
            if not path.exists(): return None
            obj = json.loads(path.read_bytes())
            if obj["effect_id"] != effect_id: raise ValueError("effect.identity_conflict")
            return EffectReceipt(effect_id, obj["kind"], obj["status"], restore_tree(obj["value"]), obj["resource"], obj["finding"], restore_tree(obj.get("intent")))

    def put(self, receipt):
        obj = dict(effect_id=receipt.effect_id, kind=receipt.kind, status=receipt.status,
            value=canonical_tree(receipt.value), resource=receipt.resource, finding=receipt.finding, intent=canonical_tree(receipt.intent))
        path = self._path(receipt.effect_id)
        with self._lock:
            descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".effect-")
            try:
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode())
                    stream.flush(); os.fsync(stream.fileno())
                os.replace(temporary, path)
            finally:
                Path(temporary).unlink(missing_ok=True)
