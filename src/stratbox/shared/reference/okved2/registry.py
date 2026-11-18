"""Verified bundled OKVED2 classification from Rosstat CSV source materials."""

from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING

from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.reference.assets import ReferenceError, load_reference

if TYPE_CHECKING:
    import pandas as pd

_PACKAGE = "stratbox.shared.reference.okved2"


def _read_csv(role: str, *, inputs: list[UsedInputReceipt] | None = None,
              edition_id: str | None = None, soft: bool = False):
    import pandas as pd
    bundle = load_reference(_PACKAGE, edition_id=edition_id)
    raw = bundle.read(role, inputs=inputs)
    opts = dict(encoding="cp1251", sep=";", dtype=str, engine="python")
    if role == "data":
        return pd.read_csv(BytesIO(raw), header=None, names=["Razdel", "Code", "Name"], **opts)
    if not soft:
        return pd.read_csv(BytesIO(raw), **opts)
    try:
        return pd.read_csv(BytesIO(raw), **opts)
    except pd.errors.ParserError:
        return pd.read_csv(BytesIO(raw), on_bad_lines="skip", **opts)


def read_meta(*, inputs: list[UsedInputReceipt] | None = None, edition_id: str | None = None):
    return _read_csv("meta", inputs=inputs, edition_id=edition_id, soft=True)


def read_structure(*, inputs: list[UsedInputReceipt] | None = None, edition_id: str | None = None):
    return _read_csv("structure", inputs=inputs, edition_id=edition_id, soft=True)


def read(*, inputs: list[UsedInputReceipt] | None = None, edition_id: str | None = None):
    import pandas as pd
    df = _read_csv("data", inputs=inputs, edition_id=edition_id)
    cols = {str(name).lower(): name for name in df.columns}
    if not {"razdel", "code", "name"}.issubset(cols):
        raise ReferenceError("OKVED2 data requires Razdel/Code/Name fields")
    out = pd.DataFrame({
        "section": df[cols["razdel"]].astype(str).str.strip(),
        "code": df[cols["code"]].astype(str).str.strip(),
        "name": df[cols["name"]].astype(str).str.strip(),
    })
    out["code"] = out["code"].replace({"nan": ""})
    return out[out["code"].ne("")].reset_index(drop=True)


def lookup(code: str, *, edition_id: str | None = None):
    if code is None:
        return None
    df = read(edition_id=edition_id)
    hit = df[df["code"] == str(code).strip()]
    return None if hit.empty else hit.iloc[0].to_dict()
