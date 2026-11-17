"""Portable, optional observability. Import never creates storage or runtime state."""
from stratbox.core.observability.records.contracts import (DomainFact, JournalRecord,
                        ObjectRef, OriginClaim, OriginAttestation, PayloadLimits, make_fact_id)
from stratbox.core.observability.journal.contracts import JournalBarrierError, JournalWriteReceipt
from stratbox.core.observability.assessment.coverage import (SequenceRange, CaptureCoverage, CoverageEvidence, CoverageAssessment,
                       merge_ranges, subtract_ranges, intersect_ranges, count_ranges,
                       find_gaps, assess_coverage, GenerationCaptureAssessment)
from stratbox.core.observability.capture.adapters import (fact_from_acquisition, fact_from_comparison, fact_from_publication,
                       fact_from_stored_bytes, effect_state_from_storage_status,
                       record_from_execution_event, record_from_fact, record_from_result)
from stratbox.core.observability.capture.policies import CapturePolicy, ObserverLimits
from stratbox.core.observability.journal.policies import PersistencePolicy
from stratbox.core.observability.analysis.policies import PresentationPolicy
from stratbox.core.observability.records.field_policy import (AllowedField, RecordFieldSchema, FieldSchemaRegistry, SCHEMAS, validate_builtin_fields)
from stratbox.core.observability.records.schema import FieldRule, RecordDataSchema, ValueRule
from stratbox.core.observability.capture.health import ObserverHealthSnapshot
from stratbox.core.observability.capture.sinks import (CaptureDisposition, CompositeEventSink, RecordMemorySink, FileEventSink, ObserverGenerationSnapshot)
from stratbox.core.observability.analysis.selection import CausalInspection, RecordFilter, group_records, inspect_causes, select_records
from stratbox.core.observability.assessment.lifecycle import ExecutionLifecycleAssessment, inspect_execution_lifecycle, assess_generation_coverage
from stratbox.core.observability.analysis.history import OperationHistory, OperationStatistics, build_operation_history, summarize_operations
from stratbox.core.observability.analysis.projections import (OperationState, SourceCheckState, PublicationObservation, RevisionResolution, DatasetState, ArtifactState, EffectState,
                          project_operation_state, operation_state_from_result,
                          project_source_state, project_dataset_state, project_artifact_state,
                          project_effect_state, projection_rows, source_state_from_publication,
                          dataset_state_from_comparison, artifact_state_from_storage,
                          effect_state_from_result)
from stratbox.core.observability.journal.codecs import (JournalDecodeError, encode_record, decode_record, encode_records,
                     decode_records, iter_decode_jsonl)
from stratbox.core.observability.analysis.exports import export_projection_csv
from stratbox.core.observability.journal.file_writer import FileJournalWriter, reconcile_write
from stratbox.core.observability.journal.file_reader import FileJournalReader
from stratbox.core.observability.journal.contracts import JournalNamespace, JournalReadIssue, JournalReadReport
from stratbox.core.observability.journal.ports import RecordReader, RecordWriter
from stratbox.core.observability.journal.buffered import BufferedFileJournal
from stratbox.core.observability.journal.gate import RequiredJournalGate, require_confirmed
from stratbox.core.observability.journal.manifests import (JournalManifest, SegmentDescriptor, build_manifest,
                        encode_manifest, decode_manifest)
from stratbox.core.observability.capture.operations import (CaptureReport, RecordCapture, capture_operation_result,
                      fact_for_artifact, fact_for_source_check)
from stratbox.core.observability.journal.sources import (EpochJournalSource, FileJournalSource, IndexedSegment, JournalCursor, JournalEntry,
                     JournalHead, JournalPage, JournalReadLimits, JournalReadProblem,
                     JournalSource, SnapshotJournalSource, SourceProfile, StreamKey)
