"""Content identity of numerical rules; no separately maintained rule release."""
from functools import lru_cache
from hashlib import sha256
from importlib.resources import files


@lru_cache(maxsize=8)
def implementation_fingerprint(scope: str = "") -> str:
    root = files(__package__)
    if scope:
        if scope not in {"inputs", "publication", "strict", "optimization", "crosswalk"}:
            raise ValueError("sors.fingerprint_scope_invalid")
        root = root.joinpath(scope)
    digest = sha256()

    def visit(directory, prefix):
        for item in sorted(directory.iterdir(), key=lambda item: item.name):
            name = prefix + item.name
            if item.is_dir() and item.name != "__pycache__":
                visit(item, name + "/")
            elif item.name.endswith(".py"):
                data = item.read_bytes()
                digest.update(name.encode("utf-8"))
                digest.update(len(data).to_bytes(8, "big"))
                digest.update(data)

    visit(root, "")
    return digest.hexdigest()
