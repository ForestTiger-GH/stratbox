# Extraction assessments and analytical pairs

Canonical extraction returns the observations together with measured coverage
and findings. A readable workbook and an analytical product use separate data
roles even when both use the `Representation` carrier. Analytical ratios require
an explicit pair contract that pins their economic meaning and input basis.

## Coherent extraction outputs

`extract.observations` exposes three named outputs:

| Output | Meaning |
| --- | --- |
| `observations` | Source observations with exact units, periods, statuses, lineage and actual `ValueEvidence`. |
| `coverage` | The observed member identities and axes, whether membership is closed, the explicitly requested scope and physical source selection. |
| `findings` | Counted unavailable-value statuses and missing expected coverage, with bounded examples. |

The three outputs are accepted coherently. Selecting only `observations` still
runs the assessment and retains its coverage and findings on the accepted batch.
Registered row and Minfin budget methods implement this same operation.

A completed inspection closes the membership of its selection. Expected
subjects, metrics and periods from `expected_subjects`, `expected_metrics` and
`expected_periods` describe axis marginals. Their separate `axis_status` can be
complete while analytical `status` remains unknown. Seeing A/X/T1 and B/Y/T2
does not establish the other six coordinates of an A–B × X–Y × T1–T2 cube.
Missing expected axis members still establish partial coverage.

Analytical completeness requires an explicit `expected_coordinates` list. Each
coordinate pins `subject_namespace`, `subject_id`, `metric_id`, `period_kind`,
`period`, `dimensions` and `perimeter`. A date period uses its ISO date; an
interval uses `YYYY-MM-DD/YYYY-MM-DD`. Matching all required coordinate
identities can establish complete coverage of that declared scope. Explicitly
requiring only the two sparse coordinates is valid; a Cartesian product is
never inferred from independent axis lists. The list is bounded by
`max_expected_coordinates` (default 100,000), and its objects consume the
invocation budget before assessment.

`coverage.complete` concerns required observation membership. Unavailable
values retain their own missing, withheld or other statuses and findings;
complete membership does not manufacture a reported numeric value.

Port qualifications and coverage are admission requirements. Actual facts come
from the accepted value. Declaring `coverage.complete` on a consumer cannot
promote a partial batch to complete. Extraction keeps reported zero, missing,
blank, dash, withheld and not-applicable values distinct.

`ValueEvidence` retains selected method, profile and reference fingerprints from
the admitted binding. An inline profile retains a digest of its consumed data.
Source uses distinguish an acquired source identity from caller-declared source
semantics on supplied bytes. Equal observation values do not erase that origin
distinction.

Findings retain the exact assessment `scope_id` to which their counts apply.
A selected view has its own coverage identity and keeps broader source findings
with their original scope, so source validation counts remain interpretable.

## Readable content and products

`convert.readable` returns `readable.representation` with role `READABLE`.
Its workbook JSONL preserves decoder-visible sheets, coordinates, original
tokens, cached formula evidence and formats. Its physical membership is closed;
wider analytical coverage remains unspecified. Formulas are retained as data.

`render.table` returns `product.representation` with role `PRODUCTS`. The same
immutable carrier preserves actual source or calculation evidence alongside its
encoded bytes. Typed portable value encoding retains that evidence. Writing
only the carrier's raw CSV bytes is a representation export; the portable value
codec is the route for restoring the full semantic artifact.

## Admitted ratios

`calculate.ratio` requires a `pair` parameter. Its descriptor contains:

| Field | Responsibility |
| --- | --- |
| `id`, `revision`, `rationale` | Identify and explain the analytical relation. |
| `numerator`, `denominator` | Pin each dataset, metric, definition version, unit, quantity kind and scale. An optional `release_id` pins a specific input release. |
| `result` | Declare the resulting metric, unit, quantity kind and scale. |
| `period_policy` | Match equal periods, or explicitly match their ending dates. |
| `origin_policy` | Require common physical source material, the same logical sources, or an explicitly declared cross-source pair. |
| `release_policy` | Require equal releases, or separately pin both releases. |
| `multiplier`, `precision` | Declare scaling and Decimal division precision; defaults are one and 28 digits. |

A debt-share rule can declare matching regional stocks in RUB with unit scale
one, common material, equal periods and equal releases. A stock-to-annual-flow
ratio can explicitly declare different quantity kinds, a common ending date and
the intended output unit. The pair contract supplies that meaning; matching
column names or units alone does not establish it.

Input keys retain subjects, dimensions and perimeters. Duplicate or unmatched
keys, unavailable numeric inputs, zero denominators, changed metric definitions
and incompatible revisions fail with qualified calculation diagnostics.

The result retains `CalculationEvidence`: the pair identity and revision,
descriptor fingerprint, exact snapshots and release identifiers of both inputs,
and the admitted period, origin and revision policies. Its derived release
identity depends on the complete rule and both input snapshots. Views,
representations and portable snapshots preserve that basis.

The lower-level `numbers.evaluate` command remains a technical same-unit
division primitive. It does not grant `calculation.admitted` and does not replace
the analytical pair contract. The supplied ratio scenario and package cascade
require `pair` explicitly and pass it through to `calculate.ratio`.

See [the shared capability session](capability-session.md) for preparation and
execution, and [effect recovery and stage events](effect-recovery-and-stage-events.md)
for independent save and notification obligations.
