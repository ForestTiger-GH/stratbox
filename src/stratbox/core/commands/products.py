"""Prepare existing observation content and render selected representations."""
from __future__ import annotations
from io import StringIO
import csv
import json
from stratbox.shared.data.values import EncodedProduct, SourceDataset, View, select_dataset
from ._settings import _get, _option


def view_prepare(inputs, settings, context):
    dataset, filters = inputs["dataset"], _option(context, settings, "filters", {})
    rows = tuple(row for row in dataset.rows if all(row.get(k) in v if isinstance(v, (tuple, list, set, frozenset)) else row.get(k) == v for k, v in filters.items()))
    return {"view": View(select_dataset(dataset, rows),
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
    return {"product": EncodedProduct(data, media, view.lineage, source_uses=view.source_uses)}
