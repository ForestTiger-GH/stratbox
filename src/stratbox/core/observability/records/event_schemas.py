"""Data schemas for the core events currently eligible for structured output."""
from stratbox.core.observability.records.schema import FieldRule, RecordDataSchema, ValueRule

TOKEN = ValueRule("token", max_length=128)
HASH = ValueRule("hash", max_length=64)
COUNT = ValueRule("integer", minimum=0)
OPTIONAL_TOKEN = ValueRule("token", nullable=True, max_length=128)
OUTCOMES = ("succeeded", "partial", "failed", "cancelled", "unknown")
IDENTITY = ValueRule("object", fields=(FieldRule("sha256", HASH), FieldRule("size", COUNT)))
ARTIFACT_REF = ValueRule("object", fields=(
    FieldRule("scope_id", TOKEN),
    FieldRule("artifact_id", TOKEN),
    FieldRule("version_id", TOKEN),
    FieldRule("sha256", HASH),
    FieldRule("size_bytes", COUNT),
))


OPERATION_FINISHED = RecordDataSchema("execution", "operation.finished", 1, (
    FieldRule("version", ValueRule("integer", minimum=3, maximum=3)),
    FieldRule("kind", ValueRule("token", choices=("operation.finished",))),
    FieldRule("invocation_id", TOKEN, classification="restricted"),
    FieldRule("operation_id", TOKEN, classification="public"),
    FieldRule("method_id", TOKEN),
    FieldRule("sequence", ValueRule("integer", minimum=1)),
    FieldRule("occurred_at_utc", ValueRule("text", max_length=40)),
    FieldRule("correlation", ValueRule("object", fields=tuple(
        FieldRule(name, OPTIONAL_TOKEN, classification="restricted")
        for name in ("run_id", "step_id", "attempt_id", "cause_event_id")
    )), classification="restricted"),
    FieldRule("stage", OPTIONAL_TOKEN, required=False),
    FieldRule("outcome", ValueRule("token", choices=OUTCOMES), classification="public"),
    FieldRule("diagnostic_code", OPTIONAL_TOKEN, required=False),
    FieldRule("duration_ms", ValueRule("integer", nullable=True, minimum=0), required=False),
    FieldRule("completed", ValueRule("integer", nullable=True, minimum=0), required=False),
    FieldRule("total", ValueRule("integer", nullable=True, minimum=0), required=False),
    FieldRule("reason_class", OPTIONAL_TOKEN, required=False),
    FieldRule("stage_elapsed_ms", ValueRule("integer", nullable=True, minimum=0), required=False),
    FieldRule("incident_id", OPTIONAL_TOKEN, required=False, classification="restricted"),
), implicit_version_one=True)

MATERIAL_STORED = RecordDataSchema("domain_fact", "material.stored", 1, (
    FieldRule("status", ValueRule("token", choices=("stored", "already_present")), classification="public"),
    FieldRule("effect_state", ValueRule("token", choices=("confirmed",))),
    FieldRule("effect_kind", TOKEN, required=False),
    FieldRule("guarantee", TOKEN),
    FieldRule("identity", IDENTITY),
    FieldRule("effect_id", TOKEN, required=False),
), implicit_version_one=True)

SOURCE_BYTES_CHANGED = RecordDataSchema("domain_fact", "source.bytes_changed", 1, (
    FieldRule("source_id", TOKEN, classification="public"),
    FieldRule("transition_id", TOKEN, classification="public"),
    FieldRule("old_sha256", HASH, classification="public"),
    FieldRule("new_sha256", HASH, classification="public"),
    FieldRule("size_bytes", COUNT, classification="public"),
    FieldRule("time_basis", ValueRule("token", choices=("observed_change",)), classification="public"),
))

PUBLICATION_COMMITTED = RecordDataSchema("domain_fact", "publication.committed", 1, (
    FieldRule("series_id", TOKEN, classification="public"),
    FieldRule("reference_date", ValueRule("date", max_length=10), classification="public"),
    FieldRule("transition_id", TOKEN, classification="public"),
    FieldRule("change", ValueRule("token", choices=("new", "updated")), classification="public"),
    FieldRule("mode", ValueRule("token", choices=("live", "backfill")), classification="public"),
    FieldRule("artifact_ref", ARTIFACT_REF, classification="public"),
    FieldRule("regions", COUNT, required=False, classification="public"),
    FieldRule("changed_regions", COUNT, required=False, classification="public"),
    FieldRule("legal_kinds", COUNT, required=False, classification="public"),
))


SOURCE_ORIGINAL_COMMITTED = RecordDataSchema("domain_fact", "source.original_version_committed", 1, (
    FieldRule("source_id", TOKEN, classification="public"),
    FieldRule("series_id", TOKEN, classification="public"),
    FieldRule("issue_id", TOKEN, classification="public"),
    FieldRule("asset_id", TOKEN, classification="public"),
    FieldRule("transition_id", TOKEN, classification="public"),
    FieldRule("change", ValueRule("token", choices=("first_seen", "new_release", "new_asset", "revised")), classification="public"),
    FieldRule("previous_sha256", ValueRule("hash", nullable=True), classification="public"),
    FieldRule("previous_transition_id", ValueRule("hash", nullable=True), classification="public"),
    FieldRule("current_sha256", HASH, classification="public"),
    FieldRule("size_bytes", COUNT, classification="public"),
    FieldRule("mode", ValueRule("token", choices=("live", "backfill")), classification="public"),
    FieldRule("owner_id", TOKEN, classification="public"),
    FieldRule("destination_id", TOKEN, classification="public"),
    FieldRule("artifact_ref", ARTIFACT_REF, classification="public"),
    FieldRule("publication_proof_ref", TOKEN, classification="public"),
))

BUILTIN_DATA_SCHEMAS = (OPERATION_FINISHED, MATERIAL_STORED, SOURCE_BYTES_CHANGED, PUBLICATION_COMMITTED, SOURCE_ORIGINAL_COMMITTED)
