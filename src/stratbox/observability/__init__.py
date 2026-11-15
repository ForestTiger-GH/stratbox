"""Portable, optional observability. Import never creates storage or runtime state."""
from .contracts import (DomainFact, JournalBarrierError, JournalRecord, JournalWriteReceipt,
                        ObjectRef, OriginClaim, OriginAttestation, PayloadLimits, make_fact_id)
from .coverage import (SequenceRange, CaptureCoverage, CoverageEvidence, CoverageAssessment,
                       merge_ranges, subtract_ranges, intersect_ranges, count_ranges,
                       find_gaps, assess_coverage, GenerationCaptureAssessment)
from .adapters import (fact_from_acquisition, fact_from_comparison, fact_from_publication,
                       fact_from_stored_bytes, effect_state_from_storage_status,
                       record_from_execution_event, record_from_fact, record_from_result)
from .policies import CapturePolicy, PersistencePolicy, PresentationPolicy, ObserverLimits
from .field_policy import (AllowedField, RecordFieldSchema, FieldSchemaRegistry, SCHEMAS, validate_builtin_fields)
from .health import ObserverHealthSnapshot
from .sinks import (CaptureDisposition, CompositeEventSink, RecordMemorySink, FileEventSink, ObserverGenerationSnapshot)
from .selection import CausalInspection, RecordFilter, group_records, inspect_causes, select_records
from .lifecycle import ExecutionLifecycleAssessment, inspect_execution_lifecycle, assess_generation_coverage
from .history import OperationHistory, OperationStatistics, build_operation_history, summarize_operations
from .projections import (OperationState, SourceCheckState, PublicationObservation, RevisionResolution, DatasetState, ArtifactState, EffectState,
                          project_operation_state, operation_state_from_result,
                          project_source_state, project_dataset_state, project_artifact_state,
                          project_effect_state, projection_rows, source_state_from_publication,
                          dataset_state_from_comparison, artifact_state_from_storage,
                          effect_state_from_result)
from .codecs import (JournalDecodeError, encode_record, decode_record, encode_records,
                     decode_records, iter_decode_jsonl, export_projection_csv)
from .file_journal import (JournalNamespace, FileJournalReader, FileJournalWriter,
                           BufferedFileJournal, JournalReadIssue, JournalReadReport,
                           RecordReader, RecordWriter, RequiredJournalGate, reconcile_write, require_confirmed)
from .manifests import (JournalManifest, SegmentDescriptor, build_manifest,
                        encode_manifest, decode_manifest)
from .capture import (CaptureReport, RecordCapture, capture_operation_result,
                      fact_for_artifact, fact_for_source_check)
