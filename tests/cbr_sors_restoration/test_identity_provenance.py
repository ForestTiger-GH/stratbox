"""SORS identities must distinguish data, classifier material and execution settings.

These tests do not invoke the solver and require only pandas and bundled assets.
"""

from __future__ import annotations

from dataclasses import fields, replace

import pandas as pd
import pytest

from stratbox.domains.cbr_sors_restoration.contracts import (
    SorsSourceBundle, SorsRunConfig, SorsDeterministicConfig,
)
from stratbox.domains.cbr_sors_restoration.operations import _identities
from stratbox.shared.evidence import SourcePayload, UsedInputReceipt
from stratbox.shared.identity import ByteIdentity
from stratbox.shared.reference.assets import (
    ReferenceError, load_reference, qualified_reference_use,
)

_SERIES = (
    "01_05_A", "01_02_A", "01_02_C", "01_03_C", "01_11",
    "01_11_F", "01_11_I", "01_12_A", "01_13_F", "01_13_I",
)


def _bundle(inputs):
    frames = {
        item.name: pd.DataFrame()
        for item in fields(SorsSourceBundle)
        if item.name.endswith("_grid")
    }
    frames.update({
        "source_manifest_grid": pd.DataFrame([
            {"source_series": name, "sha256": "a" * 64} for name in _SERIES
        ]),
        "atomic_regions_grid": pd.DataFrame({"region_code": ["r1"]}),
        "okved2_classes_grid": pd.DataFrame({"class_code": ["01"]}),
    })
    return SorsSourceBundle(**frames, lineage=tuple(inputs))


def _classifier():
    reference = load_reference("stratbox.shared.reference.okved2")
    inputs = []
    reference.read("data", inputs=inputs)
    return inputs[0]


def test_classifier_use_is_qualified_by_family_role_bytes_and_snapshot():
    receipt = _classifier()
    used = qualified_reference_use(
        [receipt], package="stratbox.shared.reference.okved2", role="data"
    )
    assert used.role == "data"
    assert used.reference_id == "reference.okved2"
    assert used.edition_id
    assert used.snapshot_identity == receipt.version
    assert used.identity == receipt.identity
    with pytest.raises(ReferenceError, match="exactly one"):
        qualified_reference_use(
            [receipt, receipt], package="stratbox.shared.reference.okved2", role="data"
        )
    with pytest.raises(ReferenceError, match="exactly one"):
        qualified_reference_use(
            [UsedInputReceipt.for_payload(SourcePayload(b"other", "text/csv", "external:data"), "data")],
            package="stratbox.shared.reference.okved2", role="data"
        )
    with pytest.raises(ReferenceError, match="Unqualified"):
        qualified_reference_use(
            [replace(receipt, identity=ByteIdentity("0" * 64, receipt.identity.size))],
            package="stratbox.shared.reference.okved2", role="data"
        )
    with pytest.raises(ReferenceError, match="Unqualified"):
        qualified_reference_use(
            [replace(receipt, version=ByteIdentity("0" * 64, receipt.version.size))],
            package="stratbox.shared.reference.okved2", role="data"
        )


def test_sors_model_identity_reacts_to_classifier_and_meaningful_parameters():
    base = _bundle((_classifier(),))
    config = SorsRunConfig(as_of_date="2026-06-01")
    dataset_id, strict_id, execution_id = _identities(base, config)
    assert len(dataset_id) == len(strict_id) == len(execution_id) == 24
    assert _identities(base, config) == (dataset_id, strict_id, execution_id)
    changed = replace(config, point_tolerance=config.point_tolerance / 2)
    new_ids = _identities(base, changed)
    assert new_ids[0] == dataset_id
    assert new_ids[1] != strict_id
    assert new_ids[2] != execution_id
    inherited = replace(config, deterministic=replace(
        config.deterministic, inheritance_enabled=False
    ))
    assert _identities(base, inherited)[1] != strict_id
    optimized = replace(config, optimization=replace(config.optimization, max_targets=10))
    assert _identities(base, optimized)[1] == strict_id
    assert _identities(base, optimized)[2] != execution_id
    unqualified = replace(base, lineage=())
    with pytest.raises(ReferenceError, match="exactly one"):
        _identities(unqualified, config)


def test_sors_dataset_identity_ignores_classifier_policy_but_model_does_not():
    receipt = _classifier()
    bundle = _bundle((receipt,))
    config = SorsRunConfig(as_of_date="2026-06-01")
    baseline = _identities(bundle, config)
    spoof = replace(receipt, source_id="external:data")
    with pytest.raises(ReferenceError):
        _identities(replace(bundle, lineage=(spoof,)), config)
    duplicate = replace(bundle, lineage=(receipt, receipt))
    with pytest.raises(ReferenceError):
        _identities(duplicate, config)


def test_unsealed_prebuilt_sors_bundle_is_rejected_before_solver():
    from stratbox.core.execution import OperationFailure
    from stratbox.domains.cbr_sors_restoration.api import _use_grids
    with pytest.raises(OperationFailure, match="input.snapshot_required"):
        _use_grids(None, _bundle((_classifier(),)), "sors_source_bundle")


def test_strict_identity_fingerprints_classifier_byte_and_edition_changes(monkeypatch):
    import stratbox.domains.cbr_sors_restoration.operations as operations
    from stratbox.shared.reference.assets import qualified_reference_use
    receipt = _classifier()
    used = qualified_reference_use(
        (receipt,), package="stratbox.shared.reference.okved2", role="data"
    )
    source = _bundle((receipt,))
    config = SorsRunConfig(as_of_date="2026-06-01")
    baseline = operations._identities(source, config)
    monkeypatch.setattr(operations, "qualified_reference_use", lambda *args, **kwargs:
                        replace(used, identity=ByteIdentity.of(b"alternate classifier material")))
    changed_bytes = operations._identities(source, config)
    assert changed_bytes[0] == baseline[0]
    assert changed_bytes[1] != baseline[1]
    assert changed_bytes[2] != baseline[2]
    monkeypatch.setattr(operations, "qualified_reference_use", lambda *args, **kwargs:
                        replace(used, snapshot_identity=ByteIdentity.of(b"alternate curated edition")))
    changed_policy = operations._identities(source, config)
    assert changed_policy[0] == baseline[0]
    assert changed_policy[1] != baseline[1]
    assert changed_policy[1] != changed_bytes[1]
