"""Form 1-YUR legal-entity population and dated source semantics."""

"""Public exports are resolved on first use; operation metadata stays lightweight."""

from importlib import import_module as _import_module

_SYMBOL_MODULES = {'ACQUIRE': '.definitions',
 'CAPTURE': '.definitions',
 'COMPARE': '.definitions',
 'CompareReleaseRequest': 'stratbox.shared.data.releases',
 'DISCOVER': '.definitions',
 'Discover1YurRequest': '.definitions',
 'PARSE': '.definitions',
 'Parse1YurRequest': '.definitions',
 'READ': '.definitions',
 'ReadReleaseRequest': 'stratbox.shared.data.releases',
 'ReleaseIndex': '.definitions',
 'ReleaseLink': 'stratbox.shared.data.releases',
 'acquire': '.operations',
 'capture': '.operations',
 'compare': '.operations',
 'discover': '.operations',
 'parse': '.operations',
 'read_representation': '.operations'}

_SYMBOL_MODULES.update({
    "EXTRACT": ".definitions",
    "extract": ".pipeline",
    "READABLE": ".definitions",
    "readable": ".pipeline",
    "VALIDATE": ".definitions",
    "validate": ".pipeline",
    "COMPARE_FLAKES": ".definitions",
    "compare_flakes": ".pipeline",
    "PROJECT": ".definitions",
    "project": ".pipeline",
    "ALIGN": ".definitions",
    "align": ".pipeline",
    "COMPARE_DATASETS": ".definitions",
    "compare_datasets": ".pipeline",
    "CALCULATE_CHANGES": ".definitions",
    "calculate_changes": ".pipeline",
    "CALCULATE_SHARES": ".definitions",
    "calculate_shares": ".pipeline",
    "VIEW": ".definitions",
    "view": ".pipeline",
    "RENDER": ".definitions",
    "render": ".pipeline",
    "FLAKE_SNAPSHOT": ".definitions",
    "flake_snapshot": ".pipeline",
    "READ_FLAKE_SNAPSHOT": ".definitions",
    "read_flake_snapshot": ".pipeline",
    "PROJECTION_SNAPSHOT": ".definitions",
    "projection_snapshot": ".pipeline",
    "READ_PROJECTION_SNAPSHOT": ".definitions",
    "read_projection_snapshot": ".pipeline",
    "DATASET_SNAPSHOT": ".definitions",
    "dataset_snapshot": ".pipeline",
    "READ_DATASET_SNAPSHOT": ".definitions",
    "read_dataset_snapshot": ".pipeline",
    "CALCULATION_SNAPSHOT": ".definitions",
    "calculation_snapshot": ".pipeline",
    "READ_CALCULATION_SNAPSHOT": ".definitions",
    "read_calculation_snapshot": ".pipeline",
    "VIEW_SNAPSHOT": ".definitions",
    "view_snapshot": ".pipeline",
    "READ_VIEW_SNAPSHOT": ".definitions",
    "read_view_snapshot": ".pipeline",
    "PROCESS": ".definitions",
    "process": ".pipeline",
    "CAPTURE_FULL": ".definitions",
    "capture_full": ".pipeline",
    "ExtractRequest": "stratbox.domains.fns.operations.contracts",
    "FlakeRequest": "stratbox.domains.fns.operations.contracts",
    "ProjectionRequest": "stratbox.domains.fns.operations.contracts",
    "DatasetRequest": "stratbox.domains.fns.operations.contracts",
    "CalculationRequest": "stratbox.domains.fns.operations.contracts",
    "ViewValueRequest": "stratbox.domains.fns.operations.contracts",
    "SnapshotRequest": "stratbox.domains.fns.operations.contracts",
    "CompareFlakesRequest": "stratbox.domains.fns.operations.contracts",
    "CompareDatasetsRequest": "stratbox.domains.fns.operations.contracts",
    "ChangesRequest": "stratbox.domains.fns.operations.contracts",
    "SharesRequest": "stratbox.domains.fns.operations.contracts",
    "ViewRequest": "stratbox.domains.fns.operations.contracts",
    "RenderRequest": "stratbox.domains.fns.operations.contracts",
    "ProcessRequest": "stratbox.domains.fns.operations.contracts",
    "CaptureFullRequest": "stratbox.domains.fns.operations.contracts",
    "ProcessedRelease": "stratbox.domains.fns.operations.contracts",
    "ReleaseContext": "stratbox.domains.fns.publications.contracts",
})
_SYMBOL_MODULES.update({"render_artifact": ".pipeline", "readable_artifact": ".pipeline",
                        "RENDER_ARTIFACT": ".definitions", "READABLE_ARTIFACT": ".definitions"})
__all__ = tuple(_SYMBOL_MODULES)


def __getattr__(name: str):
    module_name = _SYMBOL_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = _import_module(module_name, __name__)
    value = module if module_name == "." + name else getattr(module, name)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | set(__all__))
