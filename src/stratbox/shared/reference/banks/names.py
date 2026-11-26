"""Pure lexical bank names and explicit, validated alias resolution."""
from __future__ import annotations
from dataclasses import dataclass
from stratbox.shared.identity import ByteIdentity
from typing import Mapping, Literal
import re

def normalize_bank_spelling(name, placement: str='omit', case_mode: str='upper', drop_bank: str='left'):
    """Normalize whitespace, legal-form tags and display placement only.

    Alias policy is a separately supplied mapping and never loaded implicitly.
    """
    try:
        import pandas as pd
        HAS_PD = True
    except ImportError:
        HAS_PD = False
        pd = None
    if placement not in {'left', 'right', 'omit'}:
        raise ValueError("placement: 'left' | 'right' | 'omit'")
    if case_mode not in {'upper', 'preserve'}:
        raise ValueError("case_mode: 'upper' | 'preserve'")
    if drop_bank not in {'keep', 'left', 'right', 'both'}:
        raise ValueError("drop_bank: 'keep' | 'left' | 'right' | 'both'")
    ORDERED_TAGS = ['ПАО', 'АО', 'ОАО', 'ООО', 'ЗАО', 'НКО-ЦК', 'НКО', 'АКБ', 'КБ', 'КИНБ', 'АБ', 'МАБ', 'МБО', 'МБ']
    DASHES = '\\u2010\\u2011\\u2012\\u2013\\u2014\\u2015\\u2212\\uFE58\\uFE63\\uFF0D'
    SPACES = '\\u00A0\\u2000-\\u200B\\u202F\\u205F\\u3000'
    OPF = [('\\bнебанковская\\s+кредитная\\s+организация\\b(?:\\s*[-—–]\\s*|\\s*\\(\\s*|\\s+)\\s*центральный\\s+контрагент\\b\\)?', 'НКО-ЦК'), ('\\bнко\\b(?:\\s*[-—–]\\s*|\\s*\\(\\s*|\\s+)\\s*центральный\\s+контрагент\\b\\)?', 'НКО-ЦК'), ('\\bне\\s*публичное\\s+акционерное\\s+общество\\b', 'АО'), ('\\bпубличное\\s+акционерное\\s+общество\\b', 'ПАО'), ('\\bакционерное\\s+общество\\b', 'АО'), ('\\bоткрытое\\s+акционерное\\s+общество\\b', 'ОАО'), ('\\bзакрытое\\s+акционерное\\s+общество\\b', 'ЗАО'), ('\\bобщество\\s+с\\s+ограниченной\\s+ответственностью\\b', 'ООО'), ('\\bнебанковская\\s+кредитная\\s+организация\\b', 'НКО'), ('\\bакционерный\\s+коммерческий\\s+банк\\b', 'АКБ'), ('\\bкоммерческий\\s+банк\\b', 'КБ'), ('\\bкоммерческий\\s+инвестиционный\\s+народный\\s+банк\\b', 'КИНБ'), ('\\bакционерный\\s+банк\\b', 'АБ'), ('\\bмежрегиональный\\s+акционерный\\s+банк\\b', 'МАБ'), ('\\bмежбанковское\\s+объединение\\b', 'МБО'), ('\\bмеждународный\\s+банк\\b', 'МБ')]
    OPF = sorted(OPF, key=lambda pr: (len(pr[1]), len(pr[0])), reverse=True)
    SPECIAL = [(re.compile('\\b(нац(иональн\\w*)?\\s+рас[чш]е?тн\\w*\\s+центр|нрц|нац\\s*рц)\\b', re.I), (['НКО', 'АО'], 'НАЦИОНАЛЬНЫЙ РАСЧЕТНЫЙ ЦЕНТР')), (re.compile('\\b(нац(иональн\\w*)?\\s+рас[чш]е?тн\\w*\\s+депозитар\\w*|нрд)\\b', re.I), (['НКО', 'АО'], 'НАЦИОНАЛЬНЫЙ РАСЧЕТНЫЙ ДЕПОЗИТАРИЙ')), (re.compile('\\b(петербургск\\w*\\s+рас[чш]е?тн\\w*\\s+центр|прц|спб\\s*рц)\\b', re.I), (['НКО', 'АО'], 'ПЕТЕРБУРГСКИЙ РАСЧЕТНЫЙ ЦЕНТР'))]

    def _std(s: str) -> str:
        s = '' if s is None else str(s)
        s = s.replace('Ё', 'Е').replace('ё', 'е')
        s = re.sub(f'[{SPACES}]', ' ', s)
        s = re.sub(f'[{DASHES}]', '-', s)
        s = s.translate(str.maketrans({'«': '', '»': '', '“': '', '”': '', '"': '', "'": '', '_': ' '}))
        s = re.sub('\\.{2,}', '.', s)
        s = re.sub('[^\\w\\.\\-\\s\\(\\)]', ' ', s, flags=re.U)
        return re.sub('\\s+', ' ', s).strip()

    def _apply_opf(s: str) -> str:
        for p, r in OPF:
            s = re.sub(p, r, s, flags=re.I)
        return s
    TAG_ALTS = sorted(ORDERED_TAGS, key=len, reverse=True)
    TAG_RE = re.compile('\\b(?:' + '|'.join(map(re.escape, TAG_ALTS)) + ')\\b')

    def _collect_tags_longest_first(upper: str):
        found = [m.group(0) for m in TAG_RE.finditer(upper)]
        seen, out = (set(), [])
        for t in ORDERED_TAGS:
            if t in found and t not in seen:
                out.append(t)
                seen.add(t)
        return out

    def _strip(base: str, tags, ci=True):
        out = base
        for t in tags:
            out = re.sub(f'\\b{re.escape(t)}\\b', ' ', out, flags=re.I if ci else 0)
        out = out.replace('(', ' ').replace(')', ' ')
        out = re.sub('[^\\w\\.\\-\\s]', ' ', out, flags=re.U)
        out = re.sub('\\s*-\\s*', '-', out)
        out = re.sub('^\\s*-\\s*', '', out)
        return re.sub('\\s+', ' ', out).strip()

    def _one(x):
        if x is None or str(x).strip() == '':
            return None
        s = _std(x)
        s = _apply_opf(s)
        up = s.upper()
        tags, rem = (None, None)
        for pat, (tg, canon) in SPECIAL:
            if pat.search(up):
                tags = [t for t in ORDERED_TAGS if t in tg]
                rem = canon if case_mode == 'upper' else canon.title()
                break
        if tags is None:
            tags = _collect_tags_longest_first(up)
            rem = _strip(up if case_mode == 'upper' else s, tags, ci=case_mode != 'upper')
        if placement == 'omit':
            res = rem
        elif placement == 'right':
            res = f"{rem} ({' '.join(tags)})" if tags and rem else f"({' '.join(tags)})" if tags else rem
        else:
            res = ' '.join([*tags, rem]).strip() if tags and rem else rem or ' '.join(tags).strip()
        if drop_bank in {'left', 'both'}:
            res = re.sub('^\\s*БАНК\\s+(?=\\S)', '', res or '', flags=re.I)
        if drop_bank in {'right', 'both'}:
            res = re.sub('(?<=\\S)\\s+БАНК\\s*$', '', res or '', flags=re.I)
        res = re.sub('(?i)(\\b\\S+-БАНК)\\s+БАНК\\b', '\\1', res or '')
        res = re.sub('\\s*-\\s*', '-', res or '')
        res = re.sub('\\s+', ' ', res).strip()
        return (res.upper() if case_mode == 'upper' else res) or None
    if HAS_PD and isinstance(name, pd.Series):
        return name.map(_one)
    if HAS_PD and isinstance(name, pd.Index):
        return pd.Index([_one(v) for v in name], name=name.name)
    if isinstance(name, (list, tuple)):
        return [_one(v) for v in name]
    return _one(name)

@dataclass(frozen=True, slots=True)
class BankNameResolution:
    raw_name: str
    normalized_name: str | None
    display_name: str | None
    match_kind: Literal['exact', 'alias', 'unmatched']
    policy_content_id: str | None = None
    reference_id: str | None = None
    policy_snapshot_identity: ByteIdentity | None = None

def normalize_bank_name(name, placement: str='omit', case_mode: str='upper', drop_bank: str='left', *, aliases: Mapping[str, str] | None=None):
    """Explicit composition; no filesystem or registry lookup occurs here."""
    value = normalize_bank_spelling(name, placement, case_mode, drop_bank)
    if not aliases or case_mode != 'upper':
        return value

    def replace_one(v):
        return aliases.get(v.upper(), v) if isinstance(v, str) else v
    try:
        import pandas as pd
    except ImportError:
        pd = None
    if pd is not None and isinstance(value, pd.Series):
        return value.map(replace_one)
    if pd is not None and isinstance(value, pd.Index):
        return pd.Index([replace_one(v) for v in value], name=value.name)
    if isinstance(value, list):
        return [replace_one(v) for v in value]
    return replace_one(value)

def resolve_bank_name(value: str, *, aliases: Mapping[str, str], policy_content_id: str | None=None, placement: str='omit', case_mode: str='upper', drop_bank: str='left') -> BankNameResolution:
    if not isinstance(value, str):
        raise TypeError('Bank name must be a string')
    key = normalize_bank_spelling(value, placement, case_mode, drop_bank)
    displayed = normalize_bank_name(value, placement, case_mode, drop_bank, aliases=aliases)
    admitted = aliases is not None and (key in aliases or key in aliases.values())
    kind = 'unmatched' if not admitted else 'alias' if displayed != key else 'exact'
    return BankNameResolution(value, key, displayed, kind, policy_content_id)
