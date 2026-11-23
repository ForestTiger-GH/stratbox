"""Stable metadata and table identities for prepared SORS values."""
from dataclasses import asdict, fields
from decimal import Decimal
from stratbox.shared.data.lineage import input_value
from stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.contracts import SorsSourceBundle
from .results import SorsRestorationResult, SorsCrosswalkResult

def grid_tables(value):
    return tuple((item.name, getattr(value, item.name)) for item in fields(value) if item.name.endswith("_grid"))


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
        return {
            "as_of_date": value.as_of_date, "publication_step": parameters(value.publication_step),
            "coverage": asdict(value.coverage), "method_version": value.method_version,
            "lineage": [input_value(item) for item in value.lineage],
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
