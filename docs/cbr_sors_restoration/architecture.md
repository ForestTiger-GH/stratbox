# Архитектура SORS restoration

```text
CBR stock sources
  ├─ CORPORATE_TOTAL
  ├─ SME
  └─ SME_IE
        ↓
SorsSourceBundle
        ↓
strict.quantities.SorsQuantityGraph
  ├─ 3 independent latent component cubes
  ├─ region×class metrics for every scope
  ├─ published aggregates
  ├─ exact additive relations
  └─ DOMINANCE relations
       overdue <= debt
       SME_IE <= SME <= CORPORATE_TOTAL
        ↓
publication.partitions.SorsPublicationGraph
        ↓
publication.closure.run_publication_fixed_point
  ├─ strict.interval_closure.SorsIntervalClosureState
  ├─ publication.ledger.SorsPublicationLedger
  ├─ same-scope Published Mass Tokens
  ├─ source-preserving inheritance
  └─ bucket feedback into latent bounds
        ↓  fixed point required
strict.compiler.StrictCompilation
  ├─ one sparse latent LP for all three scopes
  ├─ hard scope nesting on atomic components
  ├─ stable dynamic metric rows
  └─ target catalog ONLY for CORPORATE_TOTAL
        ↓
strict.solver global feasibility gate
        ↓
optimization.engine
  ├─ strict corporate target min/max
  ├─ strong rounding profile: min L∞ → min L1
  ├─ strong optimal-face min/max
  ├─ relaxed-L1 bucket competition
  ├─ zero-protected controlled selection
  └─ deterministic fixed point after every promotion
        ↓
result_grid
  └─ only CORPORATE_TOTAL is a user-facing restored product
```

## Multi-scope latent model

The internal model contains three independent hidden cubes:

```text
CORPORATE_TOTAL
      ↑
     SME
      ↑
   SME_IE
```

For every atomic `region × OKVED2 class × component` the hard inequalities are:

```text
0 <= SME_IE <= SME <= CORPORATE_TOTAL
```

Scope is part of quantity identity. Publication tokens are also scope-local: an official `6` in SME and an official `6` in CORPORATE_TOTAL are different publication objects and can never be merged by inheritance. Information crosses scope boundaries only through explicit dominance relations.

SME and SME_IE are auxiliary latent scopes. Solver targets, `regional_okved2_grid`, pivots and restored user output remain CORPORATE_TOTAL-only.

## Publication layer

`publication/` owns the meaning of the published integer and its provenance. It does not solve LP. `SorsPublicationLedger` is the authoritative source of final `value`; result grids do not re-infer facts from final bounds.

`publication/partitions.py` builds complete/disjoint same-scope partitions. Those partitions have two separate roles:

1. publication token localization using official integer representatives;
2. exact latent sum relations using hidden monetary quantities.

This distinction permits valid publication effects such as `6 + 5 != 10` while preserving exact hidden-money identities.

Inheritance requires explicit child=`v` plus zero siblings inside a complete/disjoint partition. `parent=v + zero siblings` without a matching child never creates `v` for an unknown child.

An inherited publication value constrains latent money by its publication bucket, e.g. `6 -> [5.5, 6.5)`, not by the point `x=6`.

## Deterministic DOMINANCE

DOMINANCE is a generic hidden-money inequality relation. It is used for:

- `overdue_rub <= debt_rub`;
- `overdue_fx <= debt_fx`;
- `overdue_total <= debt_total`;
- scope nesting `SME_IE <= SME <= CORPORATE_TOTAL`;
- corresponding validated published aggregates where supports are identical.

For `child <= parent`, deterministic closure propagates:

```text
upper(child) <= upper(parent)
lower(parent) >= lower(child)
```

The same atomic scope inequalities are compiled as hard LP rows, so deterministic and Solver semantics agree.

## Strict layer

`strict/` is the continuous latent model. Every official observation keeps its own original publication interval; path length never widens a source interval.

Target uncertainty may nevertheless accumulate naturally after several exact sums, residuals and dominance relations. That uncertainty appears as a wider final target interval and is handled later by the rounding tiers rather than by increasing source tolerance.

The compiler creates one sparse LP for all scopes but emits optimization targets only for CORPORATE_TOTAL. SME/SME_IE therefore add constraints and latent degrees of freedom without tripling expensive user-target min/max work.

## Strong rounding layer

`optimization/distortion.py` builds source residual variables and computes a lexicographic strong profile:

```text
tau_star = min max_j |A_j x - P_j|
l1_star  = min sum_j |A_j x - P_j| subject to tau <= tau_star + numerical_tolerance
```

This is the strong `ROUNDING_OPTIMUM_IDENTIFIED` face. `tau_star` is calculated from the current date and data; it is not an economic tolerance configured in millions.

## Relaxed bucket competition

Weak practical reconstruction is deliberately separated from the strong optimum.

A second baseline is calculated:

```text
relaxed_l1_star = min sum_j |A_j x - P_j|
```

while every original official publication interval remains HARD, but without forcing the solution to remain on the minimum-L∞ face.

If a corporate target has several feasible publication buckets, each bucket is temporarily imposed and the whole-model L1 source-rounding cost is minimized again. A bucket can become `ROUNDING_PREFERRED` when it is decisively cheaper than alternatives and remains inside the configured global degradation budget relative to `relaxed_l1_star`.

`max_linf_degradation_mln` is optional. `None` means the weak tier may use the full legal ±0.5 room of each source observation; it does not widen any source interval. If configured, it adds a cap above `tau_star`.

Weak selection protects tiny cells: while bucket `0` remains a feasible alternative, controlled selection rejects the target by default. Zero may still be proven by deterministic, strict or strong optimal-face mechanisms.

## Evidence hierarchy

Published facts carry both evidence method and assumption tier. Weaker premises propagate as weaker facts:

```text
STRICT_OFFICIAL
SOURCE_PRESERVING
ROUNDING_OPTIMAL
ROUNDING_PREFERRED
ROUNDING_SELECTED
```

A weaker rounding premise can therefore unlock new closure facts, but those descendants cannot be relabelled as strict evidence.
