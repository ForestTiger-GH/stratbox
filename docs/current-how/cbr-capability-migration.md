# CBR capabilities, source products and retained analytical stages

CBR capabilities use the canonical catalog, preparation service and execution session.
Each technical command calls a direct domain method; operation, scenario and cascade
acceptance remain separate from the execution of that command. Source products keep
independent extracts, datasets and views available when a later representation fails.

## 1. Domain ownership and callable routes

`stratbox.domains.cbr.capabilities.contribution()` supplies typed definitions,
processing groups, profiles and source recipes. Direct executable methods belong to
`stratbox.domains.cbr.methods`; source interpretation, integration, calculations and
products retain their corresponding functional owners under the CBR domain.
Metadata discovery imports no numerical or workbook backend.

The catalog binds `source.extract` and `source.product` goals by exact `source_id`
and `representation`. Extraction goals begin with a supplied publisher original or
source payload, together with explicit source dates and keys. A statistical workbook
starts at `cbr.tables.extract`; a reporting-form archive starts at `cbr.forms.extract`.
A source-local observation projection requiring an existing flake is a subsequent
independent operation.

| Source family | Independent interpretation and analytical route |
| --- | --- |
| Statistical workbooks | `cbr.tables.extract`, `cbr.tables.validate`, `cbr.statistics.align`, `cbr.statistics.build_view`, `cbr.statistics.render_view` |
| Corporate debt and issuance | Source parser, retained-flake integration, explicit APK calculation, pivot preparation and workbook rendering |
| Reporting forms | All-member DBF extraction, physical validation, reviewed source projection, observation alignment, model-input admission and financial calculation |
| Daily and territorial office counts | Independent acquisition, parsing, release validation, observation alignment, dated stock changes, view preparation and rendering |
| Regional project finance | Source parsing, flake validation, integration, qualified observation alignment, stock-date changes, retained views and workbook rendering |
| SORS | Complete source-bundle preparation, numerical restoration, crosswalk, independent view preparation and rendering |

Statistical alignment preserves source-local labels, units, periods and unresolved
qualifications. Explicit row and column-period bindings may supply reviewed semantic
identities. Calculation admission checks measurement scale and period qualifications.
Coincident source labels alone do not establish economic equivalence.

## 2. Source products expose each accepted intermediate result

Each registered source has a `scenario.<source_id>.product` definition. Product
parameters prefix their stage name: for example `extract_key`, `integrate_row_bindings`,
`view_metric_ids` or `render_format`. Catalog metadata specifies the applicable names,
defaults and required parameters for the particular source.

A product returns `extract`, `dataset`, `view` and `representation`. Required completion
roots retain the whole product obligation while permitting independent acceptance of
its earlier outputs. Rendering consumes a prepared view; retaining or replaying that
view supports another rendering invocation without reopening the source original.
Saving representations and publishing a coherent release are separate standard effects.

Reporting-form products with financial models compose extraction, normalization,
explicit collection, model-data preparation, view preparation and rendering. The
source-version vector is calculated from the complete retained projection before
model output selection. SORS similarly prepares its complete admitted input bundle
before restoration; narrowing a product view leaves that numerical input model intact.

Statistical, corporate debt/issuance and project-finance workbook paths separate
`workbook.decode` from source interpretation. The common physical value preserves
source cell tokens, formulas, caches, types, coordinates and merged ranges. Industry
interpretation consumes cached values; project-finance interpretation consumes source
formula text while the underlying physical value retains the independent cache.
The interpreters verify the decoded value's identity against the supplied original.

`cbr.tables.readable` consumes a retained flake directly. The corresponding
`readable_original` operations, and `cbr.workbook.item_readable` for explicitly typed
source requests, use the same physical decoder as extraction. A single original can
therefore serve interpretation and physical readable consumers through one shared
decode, with independent source attribution and output acceptance.

## 3. Reporting forms 134 and 803 have explicit numeric-field interpretation

`cbr.forms.extract_fields` consumes complete retained `FormFlakes` and explicit
`FormFieldBinding` objects. A binding defines the member, numeric field, reporting
subject, row dimensions, metric, unit, scale, perimeter, period and edition. Deleted
records remain in the physical flake; inclusion in the observation projection is an
explicit parameter. Blank, dash, withheld, zero and reported values remain distinct.
Source member, record, field and literal numeric token accompany each observation.

`cbr.forms.published_field_bindings` supplies these bounded publisher field layouts:

| Profile | Physical field scope | Basis required from the caller |
| --- | --- | --- |
| `cbr.forms.134.fields.20120801` | `REGN`, row code `C1`, numeric value `C3` in the published data member | Unit, scale and stock date matching the form key |
| `cbr.forms.803.fields.20230701` | `REGN_GKO`, section `RAZDEL`, row `STR`, separate `KORR_P`, `KORR_M` and `VSEGO` measures | Unit, scale and an explicit reporting interval |

These profiles check the publisher's field names, types and widths. Their metadata
retains the exact publisher format-document URLs. The format descriptions establish
field geometry; the caller supplies the publication's measurement and interval basis.
A matching filename alone establishes neither layout compatibility nor financial
meaning. Profile mismatch and unreviewed geometry produce explicit diagnostics.

Products for these two forms compose the published field binding, numeric-field
interpretation and standard observation view/render operations. Their source-level
observations can be aligned and used in independently admitted calculations. This
route does not supply a reviewed financial formula model for either form. Model
admission remains limited to the forms declared by the financial-model registry.

## 4. Collection and history scenarios keep real member occurrences

Raw, stored and mixed-original collection scenarios use a finite ordered fold over
explicitly selected members. Every member is an ordinary independently admitted
command occurrence. The preceding accepted collection carries the remaining aggregate
byte allowance and exact dispositions. A member retry reuses the preceding accepted
state and repeats only that member. Destination writes retain separate effect receipts.

The canonical aggregate output is `collection`; its typed value retains files,
manifest, archive members, completed and unattempted members, failures and reconciliation
state. One-member streaming acquisition and destination commit remain a single qualified
transaction. Archive publication is a separate explicit operation.

Corporate and project-finance histories use bounded maps over independently supplied
source requests, followed by explicit collection and integration. A failed member
keeps its own source interpretation and failure evidence separate from other members.
The standard strict history route requires the selected source interpretations to
complete; independently retained flakes remain usable for a separately qualified
partial-history request.

Industry workbook products compose source-basis selection, pivot preparation and
rendering. APK calculation is an explicit predecessor when an APK stream is needed.
The renderer never supplies a missing derived industry by silently calculating it.
Multiple industries use bounded, separately accepted product-scenario occurrences.

## 5. Validation and project-finance changes consume retained values

Reporting-form validation checks member identities and decoded DBF values against the
retained member bytes. Office validation verifies release versions, row counts,
periods, source qualifications and observation evidence. Industry validation checks
retained source type, series, periods, reference basis and financial control findings.

`cbr.escrow.calculate_change` requires explicit before/after stock dates and metric
selection. It retains all input release evidence, distinguishes an absolute stock
difference from a reported flow, and records the selected date basis. Unknown cumulative
start dates, missing/unqualified values, duplicate revisions and a zero growth baseline
are rejected. Aggregate source rows keep their own subjects and dimensions.

## 6. Supported contracts and remaining implementation limits

The source-stage matrix describes executable routes within their admitted formats,
profiles and explicit parameter contracts. It does not certify every publisher file
or historical edition. Source-level numeric interpretation and financial formula
model coverage remain separate claims.

The following limits remain material:

- Historical project-finance HTML has no reviewed business interpretation route;
  preserve its original independently and request a supported reviewed layout.
- Reporting forms 134 and 803 have published numeric-field routes but no built-in
  financial formula models. Caller-reviewed field interpretation does not certify
  an unreviewed formula or historical schema edition.
- Territorial-office interpretation retains its dedicated lexical OOXML reader for
  formula caches, error cells and merged header evidence. Sharing this physical
  reader with a different workbook interpretation remains outstanding.
- Retained history membership and successful processing of the selected files do not
  certify complete publisher history. Unsupported editions retain explicit diagnostics.
