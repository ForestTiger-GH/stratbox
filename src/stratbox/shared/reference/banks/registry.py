"""Bank of Russia official workbook with explicit alias and selection resources."""
from __future__ import annotations
from io import BytesIO, StringIO
from dataclasses import dataclass
from typing import Literal
from stratbox.shared.data.observations import SubjectRef
from stratbox.shared.identity import ByteIdentity
import csv
import json
import re
from typing import TYPE_CHECKING
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.reference.assets import LoadedReference, ReferenceError, load_reference
from .names import normalize_bank_spelling, normalize_bank_name, resolve_bank_name, BankNameResolution
if TYPE_CHECKING:
    import pandas as pd
_PACKAGE = 'stratbox.shared.reference.banks'

def _csv(bundle: LoadedReference, role: str, *, inputs: list[UsedInputReceipt] | None=None):
    import pandas as pd
    return pd.read_csv(BytesIO(bundle.read(role, inputs=inputs)), dtype=str, encoding='utf-8-sig')

def _aliases(bundle: LoadedReference, inputs: list[UsedInputReceipt] | None=None) -> tuple[dict[str, str], dict[str, list[str]]]:
    raw = bundle.read('aliases', inputs=inputs).decode('utf-8-sig')
    reader = csv.DictReader(StringIO(raw))
    if not reader.fieldnames or not {'canon', 'alias'}.issubset(reader.fieldnames):
        raise ReferenceError('Bank aliases require columns canon and alias')
    direct: dict[str, str] = {}
    by_canon: dict[str, list[str]] = {}
    for number, row in enumerate(reader, 2):
        canonical = ' '.join(str(row.get('canon') or '').replace('\xa0', ' ').upper().split())
        alias = normalize_bank_spelling(row.get('alias'), placement='omit', case_mode='upper', drop_bank='left')
        if not canonical or not alias:
            raise ReferenceError(f'Empty bank alias entry at row {number}')
        existing = direct.get(alias)
        if existing is not None and existing != canonical:
            raise ReferenceError(f'Conflicting bank alias {alias!r} at row {number}')
        direct[alias] = canonical
        if alias != canonical and alias not in by_canon.setdefault(canonical, []):
            by_canon[canonical].append(alias)
    for alias, canonical in direct.items():
        if canonical in direct and direct[canonical] != canonical:
            raise ReferenceError(f'Chained/cyclic bank alias mapping is not allowed: {alias!r}')
    return (direct, by_canon)

def _registration_number(value: object) -> str:
    """Remove only a terminal Excel numeric '.0' marker, preserving other digits."""
    if value is None:
        return ''
    text = str(value).strip()
    if text.lower() in {'nan', 'none'}:
        return ''
    return re.sub('^(\\d+)\\.0$', '\\1', text)

def _enabled_selection(bundle: LoadedReference, aliases: dict[str, str], inputs):
    df = _csv(bundle, 'default_selection', inputs=inputs)
    if not {'enabled', 'bank'}.issubset(df.columns):
        raise ReferenceError('Bank selection requires enabled/bank columns')
    flag = df['enabled'].astype(str).str.strip().str.lower()
    accepted = {'true', 'false', '1', '0', 'yes', 'no', 'y', 'n'}
    if not flag.isin(accepted).all():
        raise ReferenceError('Bank selection has an invalid enabled value')
    enabled = flag.isin({'true', '1', 'yes', 'y'})
    return {name for name in (normalize_bank_name(value, aliases=aliases) for value in df.loc[enabled, 'bank']) if name}

def _legacy_sort(bundle: LoadedReference, inputs):
    df = _csv(bundle, 'legacy_selection', inputs=inputs)
    if not {'regn', 'sort'}.issubset(df.columns):
        raise ReferenceError('Legacy selection requires regn/sort columns')
    result: dict[str, int] = {}
    for _, row in df.iterrows():
        key = _registration_number(row['regn'])
        rank = str(row['sort']).strip()
        if not key or not rank or rank.lower() == 'nan':
            continue
        try:
            number = int(rank) if rank.isdigit() else int(float(rank))
        except (TypeError, ValueError) as exc:
            raise ReferenceError(f'Invalid legacy bank sort value for {key!r}') from exc
        if key not in result or number < result[key]:
            result[key] = number
    return result

def read_official_registry(*, inputs: list[UsedInputReceipt] | None=None):
    """Official publisher table, independent of bank alias/selection policies."""
    import pandas as pd
    bundle = load_reference(_PACKAGE)
    raw = bundle.read('official_xlsx', inputs=inputs)
    frame = pd.read_excel(BytesIO(raw))
    cols = {str(c).lower(): c for c in frame.columns}
    if not {'cregnum', 'bnk_name'}.issubset(cols):
        raise ReferenceError('Official bank workbook requires cregnum/bnk_name columns')
    out = frame.copy()
    out['regn'] = out[cols['cregnum']].map(_registration_number)
    out['bank_name'] = out[cols['bnk_name']].astype(str).str.strip()
    if 'lic_status' in cols:
        out['lic_status'] = out[cols['lic_status']]
    return out

def build_bank_profile(official, *, aliases: dict[str, str], by_canon: dict[str, list[str]], selected: set[str], legacy: dict[str, int]):
    """Derived profile without hidden resource access."""
    import pandas as pd
    out = official.copy()
    out['bank_name_norm'] = out['bank_name'].map(lambda value: normalize_bank_name(value, aliases=aliases))
    out['is_canonical'] = out['bank_name_norm'].isin(selected)
    out['replacements_list'] = out['bank_name_norm'].map(lambda value: by_canon.get(value, []))
    out['replacements_json'] = out['replacements_list'].map(lambda values: json.dumps(values, ensure_ascii=False))
    sort = out['regn'].map(legacy)
    out['is_legacy'] = sort.astype(object).where(pd.notna(sort), False)
    return out

def read(*, inputs: list[UsedInputReceipt] | None=None):
    """Compose official registry plus explicit policy resources."""
    bundle = load_reference(_PACKAGE)
    official = read_official_registry(inputs=inputs)
    aliases, by_canon = _aliases(bundle, inputs)
    selected = _enabled_selection(bundle, aliases, inputs)
    legacy = _legacy_sort(bundle, inputs)
    return build_bank_profile(official, aliases=aliases, by_canon=by_canon, selected=selected, legacy=legacy)

@dataclass(frozen=True, slots=True)
class BankEntityResolution:
    raw_registration: str
    status: Literal['matched', 'unmatched', 'ambiguous']
    subject: SubjectRef | None
    bank_name: str | None
    reference_id: str
    reference_content_id: str
    reference_snapshot_identity: ByteIdentity

def resolve_bank_entity(regn: str, *, inputs: list[UsedInputReceipt] | None=None) -> BankEntityResolution:
    """Resolve only a CBR registration number; bank display names are not identities."""
    if not isinstance(regn, str) or not regn.strip():
        raise ValueError('Bank registration identifier must be a nonempty string')
    bundle = load_reference(_PACKAGE)
    official = read_official_registry(inputs=inputs)
    key = _registration_number(regn)
    rows = official[official['regn'] == key]
    if rows.empty:
        return BankEntityResolution(regn, 'unmatched', None, None, bundle.reference.reference_id, bundle.snapshot_identity.sha256, bundle.snapshot_identity)
    if len(rows) != 1:
        return BankEntityResolution(regn, 'ambiguous', None, None, bundle.reference.reference_id, bundle.snapshot_identity.sha256, bundle.snapshot_identity)
    return BankEntityResolution(regn, 'matched', SubjectRef('cbr.bank.registration', key), str(rows.iloc[0]['bank_name']), bundle.reference.reference_id, bundle.snapshot_identity.sha256, bundle.snapshot_identity)

def lookup(regn: str) -> dict | None:
    if regn is None:
        return None
    frame = read()
    hit = frame[frame['regn'] == _registration_number(regn)]
    return None if hit.empty else hit.iloc[0].to_dict()

def normalize_registered_bank(name, *, inputs: list[UsedInputReceipt] | None=None):
    """Display-oriented composition; caller may collect the exact policy receipt."""
    bundle = load_reference(_PACKAGE)
    aliases, _ = _aliases(bundle, inputs)
    return normalize_bank_name(name, aliases=aliases)

def resolve_registered_bank(name: str, *, inputs: list[UsedInputReceipt] | None=None) -> BankNameResolution:
    """Policy-qualified bank name decision with reference snapshot and evidence."""
    bundle = load_reference(_PACKAGE)
    aliases, _ = _aliases(bundle, inputs)
    result = resolve_bank_name(name, aliases=aliases, policy_content_id=bundle.snapshot_identity.sha256)
    from dataclasses import replace
    return replace(result, reference_id=bundle.reference.reference_id, policy_snapshot_identity=bundle.snapshot_identity)
