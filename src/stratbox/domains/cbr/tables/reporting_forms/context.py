"""One metadata projection for form seals, replay and independent consumers."""
from stratbox.shared.data.source_context import source_use_value


def normalized_metadata(key, physical_fields, source_uses):
    return {"form": key.code, "as_of": key.as_of, "fields": dict(physical_fields),
            "source_uses": [source_use_value(use) for use in source_uses]}


def data_metadata(form, indicator_order, source_uses):
    return {"form": form, "indicator_order": dict(indicator_order),
            "source_uses": [source_use_value(use) for use in source_uses]}


def views_metadata(form, profile, source_uses):
    return {"form": form, "profile": profile,
            "source_uses": [source_use_value(use) for use in source_uses]}
