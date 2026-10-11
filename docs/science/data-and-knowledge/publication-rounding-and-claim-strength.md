# Publication buckets, latent quantities and strength of analytical claims

**Scope:** scientific and engineering interpretation of reconstruction from rounded banking statistics, preserving the difference between the publication and evidence about an underlying latent quantity. **Status:** bounded source-grounded Science article; complete preservation of the historical research corpus remains open.

## Two different measured objects

Let `x` denote a nonnegative latent quantity, `p` its rounded published representative, and `h>0` the publishing step. In the current SORS algorithm, `p` corresponds to the interval

\[
I(p)=[\max(0,p-h/2),\,p+h/2).
\]

The upper bound is **open**. With `h=1`, publication `p=6` admits `5.5 \le x < 6.5`. Even an **exactly identified published number** 6 does not thereby identify the **exact latent** `x=6`. This follows from the [implemented `RoundingPolicy.interval` and `PublicationInterval.is_point` contracts](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/cbr_sors_restoration/publication/rounding.py).

### Why arithmetic on published integers can fail

Suppose latent quantities satisfy `x_T=x_A+x_B`. This is an exact latent linear constraint. Independently rounded representatives `p_T,p_A,p_B` need not satisfy `p_T=p_A+p_B`. For `h=1`, take `x_A=5.6`, `x_B=5.6`, `x_T=11.2`. Their published representatives can be `p_A=6`, `p_B=6`, `p_T=11`. Thus `6+6 \ne 11` does **not** violate the exact latent identity.

Treating published representatives as exact measurements can therefore invent a zero, a negative residual or a purported source error. The current SORS quantity graph expresses component sums as `METRIC_COMPONENT_SUM`, models dominance constraints separately, and intersects interval bounds before reconciling multiple observations of one published quantity. An empty intersection or a zero-width point excluded by an open boundary triggers a conflict. See the [direct quantity-graph implementation](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/cbr_sors_restoration/strict/quantities.py).

## Evidence strength is separate from representative selection

The current evidence implementation distinguishes **five assumption tiers, 0–4**: `STRICT_OFFICIAL`, `SOURCE_PRESERVING`, `ROUNDING_OPTIMAL`, `ROUNDING_PREFERRED`, and `ROUNDING_SELECTED`. A numerically higher tier represents **weaker evidential support**, not necessarily a larger numerical error. A separate `EVIDENCE_STRENGTH` mapping ranks methods for choosing a representative within one publication bucket. Confusing assumption tier with strength of a preferred selection can inadvertently claim stronger evidence solely because an aesthetically convenient representative was selected. See the [implemented evidence contract](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/cbr_sors_restoration/evidence.py).

**Historical drift:** the older `docs_old/cbr_sors_restoration/methodology.md` explained **four tiers (0–3)**, whereas the frozen current `evidence.py` specifies **five**. For a CURRENT behavior claim, the exact implementation takes precedence. The historical reason and date of the `PREFERRED`/`SELECTED` separation have not been established; do not fabricate a migration narrative.

## Alternatives and applicability boundaries

- **Assume published integers are exact amounts.** Cheap computationally, but only justified when the publisher actually provides exact observations or a separately justified domain contract establishes that interpretation.
- **Keep only intervals.** Preserves strict uncertainty but may not yield the single convenient numerical representative expected by a consuming analyst. An admissible latent interval is not a published zero.
- **Choose representatives through optimization.** Useful when a particular number is required, but the assumptions, evidence tier and grounds for choosing it must remain visible. A collection of individually admissible representatives can still violate global constraints; joint feasibility must be tested.

**UNKNOWN:** whether every external statistical publisher uses this rounding step and convention; whether all relevant source editions are current; optimizer reliability/performance in the actual target environment. `RoundingPolicy` establishes this subsystem's implementation contract, **not** a universal rule for all authorities.

**Reopen on:** change in an official rounding rule, `RoundingPolicy`, `EVIDENCE_TIER`, source registry or measurement model; independent source verification or a counterexample. This article explains epistemic strength but **does not adopt a Product policy for selecting or publishing estimates**.
