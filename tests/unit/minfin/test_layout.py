"""Minfin's source layout has one owner, canonical resources and four semantic packages.

The test loads *every* registered operation after the old implementation paths
are removed, so a stale definition or handler reference is caught offline.
"""
from pathlib import Path

from stratbox.domains import minfin
from stratbox.operations import operation_catalog
from stratbox.domains.minfin.publications import access, catalog, materials, contracts as publications
from stratbox.domains.minfin.tables import contracts as tables, cleaning, extraction, representation
from stratbox.domains.minfin.analytics import contracts as analytics, indicators, notices
from stratbox.domains.minfin.operations import contracts as composite


def test_root_has_only_canonical_registry_records_and_one_owner():
    root = Path(minfin.__file__).parent
    from stratbox.domains.registry.declarations import source_cards
    assert not tuple(root.glob("REGISTRY_*.yaml"))
    assert len(source_cards("minfin")) == 13
    assert {p.name for p in root.glob("*.py")} == {"__init__.py", "_registration.py", "profiles.py"}
    assert {p.name for p in root.iterdir() if p.is_dir() and not p.name.startswith("__")} == {
        "publications", "tables", "analytics", "operations", "integration", "products", "documents",
    }
    assert all((root / name / "__init__.py").is_file()
               for name in ("publications", "tables", "analytics", "operations"))
    assert list(root.rglob("_registration.py")) == [root / "_registration.py"]


def test_public_api_is_the_same_type_as_its_semantic_contract():
    assert minfin.DiscoverRequest is publications.DiscoverRequest
    assert minfin.UpdateRequest is publications.UpdateRequest
    assert minfin.BuildFlakeRequest is tables.BuildFlakeRequest
    assert minfin.ExtractRequest is tables.ExtractRequest
    assert minfin.SummaryRequest is analytics.SummaryRequest
    assert minfin.NoticeRequest is analytics.NoticeRequest
    assert minfin.CaptureRequest is composite.CaptureRequest
    assert minfin.family is catalog.family
    assert minfin.checkpoint_for.__module__.endswith(".publications.updates")
    assert callable(access.allowed_file)
    assert callable(materials.acquire_material)
    assert callable(materials.read_document)
    assert callable(cleaning.build_flake)
    assert callable(extraction.extract_tables)
    assert callable(representation.render_flake_csv)
    assert callable(indicators.summarize)
    assert callable(notices.prepare_notification)


def test_all_minfin_operations_resolve_to_one_owner_and_semantic_handlers():
    register = operation_catalog()
    ref = tuple(r for r in register.references if r.operation_id.startswith("minfin."))
    assert len(ref) == 34
    assert len({r.operation_id for r in ref}) == 34
    for operation in ref:
        assert register.owner_of(operation.operation_id) == "minfin"
        assert not hasattr(operation, "definition_ref")
        assert operation.handler_ref.startswith("stratbox.domains.minfin.operations.")
        definition, handler, wire = register.resolve(operation.operation_id)
        assert definition.operation_id == operation.operation_id
        assert not hasattr(definition, "contract_version")
        assert callable(handler)
        assert wire is None
