"""Stable metadata and table identities for prepared SORS values."""
from dataclasses import asdict, fields
from decimal import Decimal
from stratbox.shared.data.lineage import input_value
from stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.contracts import SorsSourceBundle
from .results import SorsRestorationResult, SorsCrosswalkResult

def grid_tables(value):
    return tuple((item.name, getattr(value, item.name)) for item in fields(value) if item.name.endswith("_grid"))


def source_uses(value):
    """Preserve the full admitted publication vector across derived products."""
    if isinstance(value, SorsSourceBundle):
        return value.source_uses
    if isinstance(value, SorsRestorationResult):
        return value.source_bundle.source_uses if value.source_bundle is not None else ()
    if isinstance(value, SorsCrosswalkResult):
        return source_uses(value.strict_result) if value.strict_result is not None else ()
    raise ValueError("sors.source_context_value_invalid")


def parameters(value):
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {name: parameters(item) for name, item in value.items()}
    if isinstance(value, (tuple, list)):
        return tuple(parameters(item) for item in value)
    return value


def grid_metadata(value):
    if isinstance(value, SorsSourceBundle):
        from stratbox.shared.data.source_context import source_use_value
        return {
            "as_of_date": value.as_of_date, "publication_step": parameters(value.publication_step),
            "coverage": asdict(value.coverage), "method_version": value.method_version,
            "lineage": [input_value(item) for item in value.lineage],
            "source_uses": [source_use_value(use) for use in value.source_uses],
        }
    if isinstance(value, SorsRestorationResult):
        return {"summary": parameters(asdict(value.summary)),
                "run_config": parameters(asdict(value.run_config)) if value.run_config else None,
                "source_context": asdict(value.source_bundle.evidence.output) if value.source_bundle is not None and value.source_bundle.evidence else None}
    if isinstance(value, SorsCrosswalkResult):
        return {"status": value.status, "crosswalk_run_id": value.crosswalk_run_id,
                "crosswalk_config": parameters(asdict(value.crosswalk_config)) if value.crosswalk_config else None,
                "strict_context": asdict(value.strict_result.evidence.output) if value.strict_result is not None and value.strict_result.evidence else None}
    return None
