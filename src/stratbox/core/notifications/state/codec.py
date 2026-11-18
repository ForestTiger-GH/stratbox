"""Versioned transport for transaction commands owned by a state provider."""
from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import datetime
import json

from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
from stratbox.core.observability import JournalCursor, JournalHead, JournalRecord, StreamKey, decode_record, encode_record
from stratbox.core.observability.records.contracts import require_utc

from stratbox.core.notifications.contracts import (
    EventPointer, FilterCondition, HandoffLookup, HandoffReceipt, NotificationIntent,
    NotificationRoute, Subscription, SubscriptionSpec,
)
from stratbox.core.notifications.state.contracts import (
    Attempt, CheckpointKey, CheckpointUpdate, Dispatch, DispatchUpdate, RecordIdentity,
    Replay, StateMutation,
)

_MAX_BYTES = 32 * 1024**2
_TYPES = {
    item.__name__: item for item in (
        Attempt, ByteIdentity, CheckpointKey, CheckpointUpdate, Dispatch, DispatchUpdate, EventPointer,
        FilterCondition, HandoffLookup, HandoffReceipt, JournalCursor, JournalHead, NotificationIntent,
        NotificationRoute, RecordIdentity, Replay, StateMutation, StreamKey, Subscription, SubscriptionSpec,
    )
}


def _pack(value):
    if isinstance(value, JournalRecord):
        return {"type": "record", "value": encode_record(value).decode("utf-8")}
    if isinstance(value, datetime):
        return {"type": "utc", "value": require_utc(value).isoformat()}
    if isinstance(value, bytes):
        return {"type": "bytes", "value": value.hex()}
    if isinstance(value, frozenset):
        return {"type": "strings", "value": sorted(value)}
    if isinstance(value, tuple):
        return [_pack(item) for item in value]
    if is_dataclass(value) and _TYPES.get(type(value).__name__) is type(value):
        return {"type": type(value).__name__, "value": {
            item.name: _pack(getattr(value, item.name)) for item in fields(value) if item.init
        }}
    if type(value) in {str, int, bool, type(None)}:
        return value
    raise ValueError("notification.state_codec_invalid")


def _pairs(pairs):
    value = dict(pairs)
    if len(value) != len(pairs):
        raise ValueError("notification.state_codec_duplicate_field")
    return value


def _unpack(value, *, depth: int = 0):
    if depth > 32:
        raise ValueError("notification.state_codec_depth_limit")
    if type(value) in {str, int, bool, type(None)}:
        return value
    if type(value) is list:
        return tuple(_unpack(item, depth=depth + 1) for item in value)
    if type(value) is not dict or value.keys() != {"type", "value"}:
        raise ValueError("notification.state_codec_invalid")
    tag, raw = value["type"], value["value"]
    if tag == "record":
        return decode_record(raw.encode("utf-8"))
    if tag == "utc":
        return require_utc(datetime.fromisoformat(raw))
    if tag == "bytes":
        return bytes.fromhex(raw)
    if tag == "strings":
        if type(raw) is not list or not all(type(item) is str for item in raw):
            raise ValueError("notification.state_codec_invalid")
        return frozenset(raw)
    cls = _TYPES.get(tag)
    if cls is None or type(raw) is not dict or raw.keys() != {item.name for item in fields(cls) if item.init}:
        raise ValueError("notification.state_codec_invalid")
    return cls(**{key: _unpack(item, depth=depth + 1) for key, item in raw.items()})


def encode_state_mutation(mutation: StateMutation) -> bytes:
    encoded = canonical_manifest_bytes({
        "state_schema_version": 1, "command_id": mutation.command_id, "mutation": _pack(mutation),
    })
    if len(encoded) > _MAX_BYTES:
        raise ValueError("notification.state_codec_byte_limit")
    return encoded


def decode_state_mutation(data: bytes) -> StateMutation:
    """Decode a canonical command from the authenticated state provider."""
    if type(data) is not bytes or len(data) > _MAX_BYTES:
        raise ValueError("notification.state_codec_byte_limit")
    try:
        value = json.loads(data, object_pairs_hook=_pairs)
        if (type(value) is not dict or value.keys() != {"state_schema_version", "command_id", "mutation"}
                or type(value["state_schema_version"]) is not int or value["state_schema_version"] != 1):
            raise ValueError
        result = _unpack(value["mutation"])
        if (type(result) is not StateMutation or result.command_id != value["command_id"]
                or encode_state_mutation(result) != data):
            raise ValueError
        return result
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
        raise ValueError("notification.state_codec_invalid") from None
