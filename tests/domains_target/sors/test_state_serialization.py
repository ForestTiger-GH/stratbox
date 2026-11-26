"""Portable continuation is data-only and preserves scientific distinctions."""
from dataclasses import fields
from pathlib import Path
from runpy import run_path
import json

import pandas as pd
import pytest

from stratbox.domains.cbr.calculations.sors import stages
from stratbox.domains.cbr.calculations.sors.contracts import SorsRunConfig
from stratbox.domains.cbr.calculations.sors.inputs.contracts import SorsSourceBundle
from stratbox.domains.cbr.calculations.sors.publication import SorsPublicationLedger, build_publication_graph
from stratbox.domains.cbr.calculations.sors.strict.interval_closure import SorsIntervalClosureState
from stratbox.domains.cbr.calculations.sors.serialization import encode, decode


def _state():
    fixture = Path(__file__).parents[2] / "cbr_sors_restoration/test_publication_fixed_point.py"
    graph = run_path(str(fixture))["_udmurtia_like_graph"](with_cascade=True)
    bundle = SorsSourceBundle(**{
        field.name: pd.DataFrame() for field in fields(SorsSourceBundle) if field.name.endswith("_grid")})
    inputs = stages.SorsModelInputs(bundle, SorsRunConfig("2026-07-01"), ("d", "m", "r"))
    model = stages.SorsConstraintModel(inputs, graph, build_publication_graph(graph))
    closure = SorsIntervalClosureState(graph, tolerance=1e-7)
    ledger = SorsPublicationLedger()
    ledger.seed_source_facts(closure.quantities_grid)
    return stages.SorsInferenceState(model, closure, ledger)


def test_state_snapshot_resumes_same_next_scientific_action():
    original = _state()
    original = stages.bounds_propagate({"state": original}, None, None)["state"]
    restored = decode(encode(original))
    assert restored.fingerprint == original.fingerprint
    pd.testing.assert_frame_equal(restored.quantities, original.quantities)
    pd.testing.assert_frame_equal(restored.facts, original.facts)
    left = stages.facts_inherit({"state": original}, None, None)["candidates"]
    right = stages.facts_inherit({"state": restored}, None, None)["candidates"]
    assert left.fingerprint == right.fingerprint


def test_snapshot_preserves_open_bounds_exact_scalars_and_nullable_dtypes():
    frame = pd.DataFrame({"value": pd.Series([None, 0], dtype="Float64"),
                          "bound": [float("inf"), -float("inf")],
                          "proofs": [("a", "b"), ()]})
    restored = decode(encode(frame))
    pd.testing.assert_frame_equal(restored, frame)


def test_snapshot_cannot_select_an_import_or_unknown_python_class():
    payload = {"kind": "sors.value", "value": {"record": "os:system", "fields": {}}}
    with pytest.raises(ValueError, match="unadmitted_type"):
        decode(json.dumps(payload).encode())


def test_snapshot_limits_cover_frames_and_arrays():
    data = encode(pd.DataFrame({"x": list(range(20))}))
    with pytest.raises(ValueError, match="cell_limit"):
        decode(data, max_cells=10)
    with pytest.raises(ValueError, match="byte_limit"):
        decode(data, max_bytes=10)


def test_duplicate_json_keys_are_rejected():
    with pytest.raises(ValueError, match="duplicate_key"):
        decode(b'{"kind":"sors.value","kind":"sors.value","value":{}}')
