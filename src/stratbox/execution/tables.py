"""Snapshot admission and lineage shared by domain operations."""

from __future__ import annotations

from dataclasses import replace

from stratbox.data.evidence import ByteIdentity, UsedInputReceipt
from stratbox.data.identity import canonical_manifest_bytes
from stratbox.data.tables import TABLE_ENCODING, TABLE_MEDIA_TYPE, table_identity

from .contracts import OperationFailure


def _identity(tables, invocation, metadata, allow_infinite, checkpoint=None):
    try:
        identity = table_identity(tables, checkpoint=checkpoint or invocation.check_cancelled,
                                  allow_infinite=allow_infinite)
        if metadata is not None:
            return ByteIdentity.of(canonical_manifest_bytes({
                "encoding": TABLE_ENCODING, "tables": [identity.sha256, identity.size],
                "metadata": metadata,
            }))
        return identity
    except (TypeError, ValueError, UnicodeError, RecursionError):
        raise OperationFailure("input.table_value_unsupported") from None


def record_tables(invocation, tables, *, parameters=None, metadata=None, allow_infinite=False, checkpoint=None):
    invocation.budget.charge("cells", sum(frame.shape[0] * frame.shape[1] for _, frame in tables),
                             completed=checkpoint is not None)
    return invocation.record(
        _identity(tables, invocation, metadata, allow_infinite, checkpoint),
        parameters={"encoding": TABLE_ENCODING, **(parameters or {})},
    )


def use_tables(invocation, tables, *, receipt=None, role="user_table", metadata=None, allow_infinite=False):
    """Copy first, then verify and use that same private scalar-only snapshot."""
    import pandas

    if any(not isinstance(frame, pandas.DataFrame) for _, frame in tables):
        raise OperationFailure("request.invalid_table")
    invocation.budget.charge("cells", sum(frame.shape[0] * frame.shape[1] for _, frame in tables))
    private = tuple((name, frame.copy(deep=True)) for name, frame in tables)
    for _, frame in private:
        frame.index = frame.index.copy(deep=True)
        frame.columns = frame.columns.copy(deep=True)
    identity = _identity(private, invocation, metadata, allow_infinite)
    if receipt is not None and identity != receipt.output:
        raise OperationFailure("input.identity_mismatch")
    invocation.use(UsedInputReceipt(
        role, identity, TABLE_MEDIA_TYPE, "inline",
        source_id=receipt.version.dataset_id if receipt else None,
        version=receipt.version.identity if receipt else None,
    ))
    if receipt is not None:
        invocation.parents.append((role, receipt))
    return tuple(frame for _, frame in private)


def use_stream(invocation, stream, *, source=None):
    if source is not None and getattr(stream, "evidence", None) is not None:
        if stream.evidence != source.evidence:
            raise OperationFailure("input.identity_mismatch")
    owner = source if source is not None else stream
    receipt = getattr(owner, "evidence", None)
    frame = getattr(stream, "df_stream", stream)
    if source is not None and receipt is None:
        raise OperationFailure("input.snapshot_required")
    if hasattr(owner, "df_stream") and receipt is None:
        raise OperationFailure("input.snapshot_required")
    table, = use_tables(
        invocation, (("stream", frame),), receipt=receipt,
        role="stream" if receipt else "user_table", metadata=_stream_coverage(owner),
    )
    return table


def _stream_coverage(value):
    if hasattr(value, "dates") and hasattr(value, "validation_issues"):
        return {
            "dates": value.dates,
            "failed": bool(value.failures),
            "invalid": any(item.severity == "error" for item in value.validation_issues),
            "stop_reason": value.stop_reason,
        }
    return None


def seal_stream(invocation, result, *, parameters=None, checkpoint=None):
    evidence = record_tables(invocation, (("stream", result.df_stream),), parameters=parameters,
                             metadata=_stream_coverage(result), checkpoint=checkpoint)
    return replace(result, evidence=evidence)
