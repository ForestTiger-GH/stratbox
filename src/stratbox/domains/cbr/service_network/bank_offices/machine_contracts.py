"""Read-only machine schemas, independent of executable adapters."""

from stratbox.core.execution.machine.contracts import ReadOnlyWireContract

REF = {"type": "string", "pattern": r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$"}

DAY = {"type": "string", "pattern": r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$", "format": "date"}

DIGEST = {"type": "string", "pattern": r"^[0-9a-f]{64}$"}

INTEGER = {"type": "integer", "minimum": 0}

STRING = {"type": "string"}

LAYER = {"enum": ["same", "changed", "unavailable", "incompatible"]}

LAYERS = ("original", "structure", "facts", "method", "representation")

COVERAGE = {
    "common_observations": INTEGER, "baseline_observations": INTEGER,
    "candidate_observations": INTEGER, "common_subjects": INTEGER, "scope": STRING,
}

PARSE_CONTRACT = ReadOnlyWireContract(
    "cbr.offices.parse",
    1,
    {"source_ref": REF, "expected_sha256": DIGEST, "capture_date": DAY},
    ("source_ref", "capture_date"),
    {"as_of": DAY, "row_count": INTEGER,
     "dataset_sha256": DIGEST, "representation_sha256": DIGEST},
)

COMPARE_CONTRACT = ReadOnlyWireContract(
    "cbr.offices.compare",
    2,
    {"candidate_ref": REF, "baseline_ref": REF},
    ("candidate_ref",),
    {"state": STRING, "reason": STRING, "changed_count": INTEGER,
     "layers": {"type": "object", "additionalProperties": False,
                "properties": dict.fromkeys(LAYERS, LAYER), "required": list(LAYERS)},
     "coverage": {"anyOf": [{"type": "object", "additionalProperties": False,
                             "properties": COVERAGE, "required": list(COVERAGE)},
                            {"type": "null"}]}},
)
