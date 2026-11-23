"""Source-readable JSON export independent of semantic projection."""
from stratbox.shared.data.representation import Representation

from .extraction import json_text


def readable(flake):
    return Representation("fns.sme.source-json", 1, "application/json",
                          json_text(flake).encode("utf-8"), "utf-8")
