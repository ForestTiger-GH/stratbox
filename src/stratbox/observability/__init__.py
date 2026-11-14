"""Optional semantic observability, portable history and verified file journals.

Never required for ordinary execution; imports perform no I/O or background work.
"""
from .contracts import (DomainFact, JournalBarrierError, JournalRecord, JournalWriteReceipt,
                        ObjectRef, make_fact_id)
from .adapters import (fact_from_acquisition, fact_from_comparison, fact_from_publication,
                       fact_from_stored_bytes, record_from_execution_event, record_from_fact,
                       record_from_result)
from .policies import CapturePolicy, PersistencePolicy, PresentationPolicy
from .sinks import CompositeEventSink, RecordMemorySink, FileEventSink
from .selection import (CausalInspection, RecordFilter, group_records, inspect_causes,
                        select_records)
from .history import (OperationHistory, OperationStatistics, build_operation_history,
                      summarize_operations)
from .projections import (OperationState, SourceCheckState, DatasetState, ArtifactState,
                          EffectState, project_operation_state, operation_state_from_result,
                          project_source_state, project_dataset_state, project_artifact_state,
                          project_effect_state, projection_rows, source_state_from_publication,
                          dataset_state_from_comparison, artifact_state_from_storage,
                          effect_state_from_result)
from .codecs import (JournalDecodeError, encode_record, decode_record, encode_records,
                     decode_records, iter_decode_jsonl, export_projection_csv)
from .file_journal import (FileJournalReader, FileJournalWriter, BufferedFileJournal,
                           JournalReadIssue, JournalReadReport, RecordReader, RecordWriter,
                           RequiredJournalGate, reconcile_write, require_confirmed)
from .capture import (CaptureReport, RecordCapture, capture_operation_result,
                      fact_for_artifact, fact_for_source_check)
