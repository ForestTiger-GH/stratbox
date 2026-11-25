"""Explicit legacy-document conversion without changing publisher originals."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from stratbox.shared.evidence import SourcePayload
from stratbox.shared.identity import ByteIdentity


@dataclass(frozen=True, slots=True)
class ConvertedDocument:
    original_identity: ByteIdentity
    payload: SourcePayload
    provider_id: str
    provider_revision: str

    def __post_init__(self):
        if (not isinstance(self.original_identity, ByteIdentity) or not self.original_identity.size
                or not isinstance(self.payload, SourcePayload) or not self.payload.data.startswith(b"PK")
                or self.payload.media_type != "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                or self.original_identity == self.payload.identity
                or not isinstance(self.provider_id, str) or not self.provider_id
                or not isinstance(self.provider_revision, str) or not self.provider_revision):
            raise ValueError("minfin.document.conversion_invalid")


@runtime_checkable
class DocumentConverter(Protocol):
    """Host-provided conversion engine, independently admitted and versioned.

    Engines return separate DOCX bytes for the exact supplied DOC. They retain
    source_id, honour max_bytes/checkpoint and never replace the input material.
    The library decodes and validates the returned package independently.
    """
    provider_id: str
    revision: str

    def convert(self, payload: SourcePayload, *, target_format: str, max_bytes: int, checkpoint) -> SourcePayload: ...


def convert_legacy_document(payload, converter: DocumentConverter, *, max_bytes=64*1024*1024, checkpoint=None):
    if (not isinstance(payload, SourcePayload) or not payload.data.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1")
            or type(max_bytes) is not int or not 0 < len(payload.data) <= max_bytes <= 128*1024*1024):
        raise ValueError("minfin.document.legacy_source_invalid")
    if not isinstance(converter, DocumentConverter):
        raise ValueError("minfin.document.converter_contract_invalid")
    if checkpoint is not None:
        checkpoint()
    converted = converter.convert(payload, target_format="docx", max_bytes=max_bytes, checkpoint=checkpoint)
    if (not isinstance(converted, SourcePayload) or converted.source_id != payload.source_id
            or not 0 < len(converted.data) <= max_bytes):
        raise ValueError("minfin.document.conversion_output_invalid")
    value = ConvertedDocument(payload.identity, converted, converter.provider_id, converter.revision)
    # Package and XML admission happen before the conversion is accepted. Main
    # body decoding remains its own command and retains ordered evidence.
    from stratbox.core.formats.archives.members import open_zip
    from stratbox.core.formats.xml import parse_xml
    with open_zip(value.payload.data) as package:
        if "word/document.xml" not in package.namelist():
            raise ValueError("minfin.document.converted_docx_required")
        parse_xml(package.read("word/document.xml"))
    if checkpoint is not None:
        checkpoint()
    return value
