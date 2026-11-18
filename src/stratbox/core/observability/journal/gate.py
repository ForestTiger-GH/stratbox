"""Pre-effect journal barrier with explicit read-back evidence."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from stratbox.shared.identity import ByteIdentity
from stratbox.core.observability.records.contracts import JournalRecord
from stratbox.core.observability.journal.contracts import JournalWriteReceipt, JournalBarrierError
from stratbox.core.observability.journal.codecs import encode_records
from stratbox.core.observability.journal.ports import RecordWriter

def require_confirmed(receipt: JournalWriteReceipt) -> JournalWriteReceipt:
    if not isinstance(receipt, JournalWriteReceipt):
        raise ValueError("journal.write_receipt_invalid")
    if receipt.state != "confirmed":
        raise JournalBarrierError(receipt)
    return receipt


class RequiredJournalGate:
    """An explicit *pre-action* barrier; never a general EventSink policy."""
    def __init__(self, writer: RecordWriter):
        self.writer = writer

    def require_confirmed(self, record: JournalRecord) -> JournalWriteReceipt:
        batch = (record,)
        identity = ByteIdentity.of(encode_records(batch, format=self.writer.format))
        receipt = require_confirmed(self.writer.write_batch(batch))
        if not receipt.confirms_batch(identity, (record.record_id,)):
            raise JournalBarrierError(replace(
                receipt, state="failed", diagnostic_code="journal.write_receipt_mismatch", already_present=False,
            ))
        return receipt

    def execute_after_record(self, record: JournalRecord, action: Callable[[], object]) -> tuple[object, JournalWriteReceipt]:
        receipt = self.require_confirmed(record)
        return action(), receipt
