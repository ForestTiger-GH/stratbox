"""Prepare existing observation content and render selected representations."""
from __future__ import annotations
from io import StringIO
import csv
import json
from stratbox.shared.data.values import EncodedProduct, SourceDataset, View
from stratbox.shared.data.selection import ObservationQuery, select_observations
from ._settings import _get, _option


def view_prepare(inputs, settings, context):
    dataset, filters = inputs["dataset"], _option(context, settings, "filters", {})
    selected = select_observations(dataset, ObservationQuery(filters=filters)) if filters else dataset
    return {"view": View(selected,
                         {} if settings is None else settings, (*dataset.lineage, dataset.identity), dataset.source_uses)}


def product_render(inputs, settings, context):
    view = inputs["view"]
    rows = view.value.rows if isinstance(view.value, SourceDataset) else view.value
    fmt = _option(context, settings, "format", "csv")
    if fmt == "csv":
        columns = tuple(_get(settings, "columns", ())) or tuple(dict.fromkeys(k for row in rows for k in row))
        stream = StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)
        data, media = stream.getvalue().encode("utf-8"), "text/csv"
    elif fmt in {"json", "jsonl"}:
        encode = lambda value: json.dumps(value, default=str, ensure_ascii=False, separators=(",", ":"))
        data = ("\n".join(encode(dict(row)) for row in rows) if fmt == "jsonl" else encode([dict(row) for row in rows])).encode()
        media = "application/x-ndjson" if fmt == "jsonl" else "application/json"
    else:
        renderer = context.provider("renderer")
        data, media = renderer.render(view, format=fmt, checkpoint=context.checkpoint)
    return {"product": EncodedProduct(data, media, view.lineage, source_uses=view.source_uses,
        assessment=view.assessment)}
