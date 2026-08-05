from __future__ import annotations

from dataclasses import dataclass
from math import inf
from typing import Iterable

import numpy as np
import pandas as pd
from scipy.optimize import linprog
from scipy.sparse import csr_matrix, hstack, vstack

from stratbox.macrobanks.cbr_sors_restoration.contracts import SorsSourceBundle
from stratbox.macrobanks.cbr_sors_restoration.schema import COMPONENTS, publication_interval, published_bucket


@dataclass(frozen=True, slots=True)
class SumConstraint:
    name: str
    indices: np.ndarray
    lower: float
    upper: float
    source: str


class VariableIndex:
    def __init__(self, regions: pd.DataFrame, classes: pd.DataFrame):
        self.region_names = tuple(regions['region_name'].astype(str))
        self.region_codes = tuple(regions['region_code'].astype(str))
        self.region_fds = tuple(regions['federal_district_name'].astype(str))
        self.class_codes = tuple(classes['class_code'].astype(str))
        self.class_sections = tuple(classes['section_code'].astype(str))
        self.n_regions = len(self.region_names)
        self.n_classes = len(self.class_codes)
        self.n_components = len(COMPONENTS)
        self.size = self.n_regions * self.n_classes * self.n_components
        self._component_pos = {c: i for i, c in enumerate(COMPONENTS)}
        self._region_pos = {name: i for i, name in enumerate(self.region_names)}
        self._class_pos = {code: i for i, code in enumerate(self.class_codes)}

    def index(self, r: int, c: int, component: str) -> int:
        return (r * self.n_classes + c) * self.n_components + self._component_pos[component]

    def indices_for(self, *, regions: Iterable[int], classes: Iterable[int], components: Iterable[str]) -> np.ndarray:
        return np.fromiter(
            (self.index(r, c, k) for r in regions for c in classes for k in components),
            dtype=np.int64,
        )

    def decode(self, idx: int) -> tuple[int, int, str]:
        cell, k = divmod(int(idx), self.n_components)
        r, c = divmod(cell, self.n_classes)
        return r, c, COMPONENTS[k]

    def locate(self, region_name: str, class_code: str, component: str) -> int:
        return self.index(self._region_pos[region_name], self._class_pos[class_code], component)


def _metric_components(measure: str, currency: str) -> tuple[str, ...]:
    if measure == 'overdue' and currency == 'rub':
        return ('overdue_rub',)
    if measure == 'debt' and currency == 'rub':
        return ('performing_rub', 'overdue_rub')
    if measure == 'overdue' and currency == 'fx':
        return ('overdue_fx',)
    if measure == 'debt' and currency == 'fx':
        return ('performing_fx', 'overdue_fx')
    raise ValueError((measure, currency))


def build_constraints(bundle: SorsSourceBundle, index: VariableIndex, publication_step: float) -> list[SumConstraint]:
    out: list[SumConstraint] = []
    region_by_name = {name: i for i, name in enumerate(index.region_names)}
    class_by_code = {code: i for i, code in enumerate(index.class_codes)}

    # Regional totals from 01_05_A, restricted to mutually exclusive 85-territory basis.
    regional = bundle.regional_grid
    regional = regional[(regional['industry_code'].astype(str) == 'total')]
    for _, row in regional.iterrows():
        name = str(row['region_name'])
        if name not in region_by_name:
            continue
        currency_scope = str(row['currency_scope'])
        if currency_scope == 'total':
            continue
        measure = 'overdue' if str(row['measure']) == 'overdue_debt' else 'debt'
        currency = 'rub' if currency_scope == 'rubles' else 'fx'
        components = _metric_components(measure, currency)
        ids = index.indices_for(regions=(region_by_name[name],), classes=range(index.n_classes), components=components)
        lo, hi = publication_interval(float(row['value']), publication_step)
        out.append(SumConstraint(f'region:{name}:{measure}:{currency}', ids, lo, hi, '01_05_A'))

    # National class margins from 01_02_C.
    for _, row in bundle.national_okved2_grid.iterrows():
        code = str(row['class_code'])
        if code not in class_by_code:
            continue
        components = _metric_components(str(row['measure']), str(row['currency']))
        ids = index.indices_for(regions=range(index.n_regions), classes=(class_by_code[code],), components=components)
        lo, hi = publication_interval(float(row['value']), publication_step)
        out.append(SumConstraint(f'national:{code}:{row["measure"]}:{row["currency"]}', ids, lo, hi, '01_02_C'))

    # FD x OKVED2 section margins from 01_03_C are total across currencies.
    for _, row in bundle.fd_okved2_grid.iterrows():
        fd = str(row['federal_district_name'])
        section = str(row['section_code'])
        rs = [i for i, x in enumerate(index.region_fds) if x == fd]
        cs = [i for i, x in enumerate(index.class_sections) if x == section]
        if not rs or not cs:
            continue
        components = COMPONENTS if str(row['measure']) == 'debt' else ('overdue_rub', 'overdue_fx')
        ids = index.indices_for(regions=rs, classes=cs, components=components)
        lo, hi = publication_interval(float(row['value']), publication_step)
        out.append(SumConstraint(f'fd:{fd}:{section}:{row["measure"]}', ids, lo, hi, '01_03_C'))

    return out


def initial_bounds(size: int, constraints: list[SumConstraint]) -> tuple[np.ndarray, np.ndarray]:
    lower = np.zeros(size, dtype=float)
    upper = np.full(size, inf, dtype=float)
    for con in constraints:
        upper[con.indices] = np.minimum(upper[con.indices], con.upper)
    if np.isinf(upper).any():
        missing = int(np.isinf(upper).sum())
        raise ValueError(f'{missing} variables are not bounded by published margins')
    return lower, upper


def deterministic_closure(
    lower: np.ndarray,
    upper: np.ndarray,
    constraints: list[SumConstraint],
    *,
    max_passes: int = 100,
    tolerance: float = 1e-9,
) -> tuple[np.ndarray, np.ndarray, int, int]:
    lo = lower.copy()
    hi = upper.copy()
    updates = 0
    for pass_no in range(1, max_passes + 1):
        changed = 0
        for con in constraints:
            ids = con.indices
            lvals = lo[ids]
            uvals = hi[ids]
            sum_l = float(lvals.sum())
            sum_u = float(uvals.sum())
            if sum_l > con.upper + tolerance or sum_u < con.lower - tolerance:
                raise ValueError(f'Infeasible during deterministic closure: {con.name}')
            # For positive sums: x_i >= L - sum U_others and x_i <= U - sum L_others.
            new_lo = np.maximum(lvals, con.lower - (sum_u - uvals))
            new_hi = np.minimum(uvals, con.upper - (sum_l - lvals))
            new_lo = np.maximum(new_lo, 0.0)
            if np.any(new_lo > new_hi + tolerance):
                raise ValueError(f'Infeasible variable bounds after {con.name}')
            changed += int(np.count_nonzero(new_lo > lvals + tolerance))
            changed += int(np.count_nonzero(new_hi < uvals - tolerance))
            lo[ids] = np.maximum(lo[ids], new_lo)
            hi[ids] = np.minimum(hi[ids], new_hi)
        updates += changed
        if changed == 0:
            return lo, hi, pass_no, updates
    return lo, hi, max_passes, updates


def build_ub_matrix(size: int, constraints: list[SumConstraint]) -> tuple[csr_matrix, np.ndarray]:
    rows = []
    rhs = []
    for con in constraints:
        data = np.ones(len(con.indices), dtype=float)
        row = csr_matrix((data, (np.zeros(len(con.indices), dtype=int), con.indices)), shape=(1, size))
        rows.append(row)
        rhs.append(con.upper)
        rows.append(-row)
        rhs.append(-con.lower)
    return vstack(rows, format='csr'), np.asarray(rhs, dtype=float)


def check_feasible(A_ub: csr_matrix, b_ub: np.ndarray, lower: np.ndarray, upper: np.ndarray) -> dict[str, object]:
    result = linprog(
        c=np.zeros(len(lower), dtype=float),
        A_ub=A_ub,
        b_ub=b_ub,
        bounds=list(zip(lower, upper, strict=True)),
        method='highs',
    )
    return {'success': bool(result.success), 'status': int(result.status), 'message': str(result.message)}



def minimum_extra_error(A_ub: csr_matrix, b_ub: np.ndarray, size: int) -> dict[str, object]:
    """Minimum common expansion (million rubles) beyond publication intervals."""
    slack_col = -np.ones((A_ub.shape[0], 1), dtype=float)
    augmented = hstack([A_ub, csr_matrix(slack_col)], format='csr')
    c = np.zeros(size + 1, dtype=float)
    c[-1] = 1.0
    result = linprog(
        c=c,
        A_ub=augmented,
        b_ub=b_ub,
        bounds=[(0.0, None)] * size + [(0.0, None)],
        method='highs',
    )
    return {
        'success': bool(result.success),
        'status': int(result.status),
        'message': str(result.message),
        'minimum_extra_error_mln_rub': float(result.fun) if result.success else None,
    }


def certify_indices(
    indices: Iterable[int],
    A_ub: csr_matrix,
    b_ub: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
) -> dict[int, tuple[float, float]]:
    bounds = list(zip(lower, upper, strict=True))
    out: dict[int, tuple[float, float]] = {}
    n = len(lower)
    for idx in indices:
        idx = int(idx)
        c = np.zeros(n, dtype=float)
        c[idx] = 1.0
        lo_res = linprog(c=c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method='highs')
        if not lo_res.success:
            raise RuntimeError(f'LP min failed for variable {idx}: {lo_res.message}')
        c[idx] = -1.0
        hi_res = linprog(c=c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method='highs')
        if not hi_res.success:
            raise RuntimeError(f'LP max failed for variable {idx}: {hi_res.message}')
        out[idx] = (float(lo_res.fun), float(-hi_res.fun))
    return out


def bounds_frame(index: VariableIndex, lower: np.ndarray, upper: np.ndarray, publication_step: float) -> pd.DataFrame:
    records = []
    for idx in range(index.size):
        r, c, component = index.decode(idx)
        lo = float(lower[idx]); hi = float(upper[idx])
        bucket = published_bucket(lo, hi, publication_step)
        records.append({
            'variable_id': idx,
            'region_code': index.region_codes[r],
            'region_name': index.region_names[r],
            'federal_district_name': index.region_fds[r],
            'class_code': index.class_codes[c],
            'section_code': index.class_sections[c],
            'component': component,
            'lower_bound': lo,
            'upper_bound': hi,
            'interval_width': hi - lo,
            'published_precision_value': bucket,
        })
    return pd.DataFrame(records)
