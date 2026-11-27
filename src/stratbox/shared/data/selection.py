"""Explicit bounded selections over declared sources and observed evidence.

Selectors carry caller intent. They never choose a publisher-specific workload
or turn an incomplete observation into evidence of absent publications.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, fields, replace
from datetime import date, datetime

from .values import Assessment, AssetSelection, PublicationListing, SourceDataset, fingerprint, immutable
from .coverage import SelectedScopeCoverage


MAX_SELECTION_ITEMS = 10000
SOURCE_FACETS = frozenset({"publisher_id", "issue_model", "delivery_mode", "artifact_category",
                          "formats", "family_ids", "stage_support", "target_kind"})


class SelectionError(ValueError):
    def __init__(self, code, *, report=None):
        self.code, self.report = code, report
        super().__init__(code)


def _tokens(values, name, *, allow_empty=False, maximum=MAX_SELECTION_ITEMS):
    if isinstance(values, (str, bytes)):
        raise SelectionError("selection.invalid_" + name)
    result = tuple(values)
    if (len(result) > maximum or len(result) != len(set(result))
            or any(type(v) is not str or (not v and not allow_empty) or len(v) > 2048 for v in result)):
        raise SelectionError("selection.invalid_" + name)
    return result


def _limit(value, name="max_items", *, zero=False, maximum=MAX_SELECTION_ITEMS):
    if type(value) is not int or not (0 if zero else 1) <= value <= maximum:
        raise SelectionError("selection.invalid_" + name)
    return value


def _day(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        raise SelectionError("selection.calendar_date_required")
    if type(value) is date:
        return value
    if isinstance(value, str):
        try:
            result = date.fromisoformat(value)
            if result.isoformat() == value:
                return result
        except ValueError:
            pass
    raise SelectionError("selection.invalid_date")


def _mapping(value, cls):
    if not isinstance(value, Mapping):
        raise SelectionError("selection.typed_query_required")
    if set(value) - {f.name for f in fields(cls)}:
        raise SelectionError("selection.unknown_query_field")
    return dict(value)


@dataclass(frozen=True, slots=True)
class SourceQuery:
    mode: str = "exact"
    includes: tuple[str, ...] = ()
    excludes: tuple[str, ...] = ()
    facets: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    order: tuple[str, ...] = ()
    max_items: int = MAX_SELECTION_ITEMS

    def __post_init__(self):
        if self.mode not in {"exact", "predicate", "all"}:
            raise SelectionError("selection.source_mode_invalid")
        for name in ("includes", "excludes", "order"):
            object.__setattr__(self, name, _tokens(getattr(self, name), name))
        if not isinstance(self.facets, Mapping) or set(self.facets) - SOURCE_FACETS:
            raise SelectionError("selection.unknown_source_facet")
        facets = {key: _tokens((value,) if isinstance(value, str) else value, key)
                  for key, value in self.facets.items()}
        if any(not value for value in facets.values()):
            raise SelectionError("selection.empty_facet")
        if self.mode == "predicate" and not facets or self.mode == "exact" and facets:
            raise SelectionError("selection.source_predicate_required")
        object.__setattr__(self, "facets", immutable(facets))
        _limit(self.max_items)

    @property
    def identity(self):
        return fingerprint(self)


def source_query(value):
    return value if isinstance(value, SourceQuery) else SourceQuery(**_mapping(value, SourceQuery))


@dataclass(frozen=True, slots=True)
class SourceSelection:
    query: SourceQuery
    declaration_basis: str
    source_ids: tuple[str, ...]
    excluded: tuple[str, ...] = ()
    membership_closed: bool = True

    def __post_init__(self):
        if not isinstance(self.query, SourceQuery) or not self.declaration_basis or self.membership_closed is not True:
            raise SelectionError("selection.invalid_source_selection")
        object.__setattr__(self, "source_ids", _tokens(self.source_ids, "source_ids"))
        object.__setattr__(self, "excluded", _tokens(self.excluded, "excluded"))
        if set(self.source_ids) & set(self.excluded) or len(self.source_ids) > self.query.max_items:
            raise SelectionError("selection.source_scope_conflict")

    @property
    def identity(self):
        return fingerprint(self)


@dataclass(frozen=True, slots=True)
class IssueQuery:
    mode: str = "observed"
    issues: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()
    asset_ids: tuple[str, ...] = ()
    locators: tuple[str, ...] = ()
    date_from: date | None = None
    date_to: date | None = None
    date_axis: str = "issue_id"
    formats: tuple[str, ...] = ()
    latest: int = 1
    expected_issues: tuple[str, ...] = ()
    ambiguity: str = "reject"
    max_items: int = MAX_SELECTION_ITEMS
    coverage_intent: str = "selected"

    def __post_init__(self):
        if self.mode not in {"observed", "exact", "range", "latest", "calendar", "rolling"}:
            raise SelectionError("selection.issue_mode_invalid")
        for name in ("issues", "source_ids", "asset_ids", "locators", "formats", "expected_issues"):
            values = tuple(v.isoformat() if type(v) is date else v for v in getattr(self, name))
            object.__setattr__(self, name, _tokens(values, name, allow_empty=name in {"issues", "expected_issues"}))
        for name in ("date_from", "date_to"):
            object.__setattr__(self, name, _day(getattr(self, name)))
        if self.mode == "observed":
            if self.issues:
                object.__setattr__(self, "mode", "exact")
            elif self.expected_issues:
                object.__setattr__(self, "mode", "calendar")
            elif self.date_from is not None or self.date_to is not None:
                object.__setattr__(self, "mode", "range")
        if self.issues and self.mode != "exact" or self.expected_issues and self.mode not in {"calendar", "range"}:
            raise SelectionError("selection.incompatible_issue_fields")
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise SelectionError("selection.date_range_invalid")
        if self.date_axis not in {"issue_id", "publication_date", "reporting_date", "measurement_date", "issue_order"}:
            raise SelectionError("selection.date_axis_invalid")
        if self.date_axis == "issue_order" and (self.date_from is not None or self.date_to is not None):
            raise SelectionError("selection.order_is_not_date_axis")
        if self.mode == "range" and self.date_from is None and self.date_to is None:
            raise SelectionError("selection.date_range_required")
        if self.mode == "calendar" and not self.expected_issues:
            raise SelectionError("selection.expected_issues_required")
        if self.ambiguity not in {"reject", "report"}:
            raise SelectionError("selection.ambiguity_policy_invalid")
        if self.coverage_intent not in {"selected", "complete_inventory"}:
            raise SelectionError("selection.coverage_intent_invalid")
        _limit(self.latest, "latest")
        _limit(self.max_items)

    @property
    def identity(self):
        return fingerprint(self)


def issue_query(value):
    """Normalize documented scalar aliases at the public query boundary only."""
    if isinstance(value, IssueQuery):
        return value
    if value is None:
        return IssueQuery()
    if not isinstance(value, Mapping):
        raise SelectionError("selection.typed_query_required")
    data = dict(value)
    for old, new in (("source_id", "source_ids"), ("asset_id", "asset_ids"),
                     ("issue_id", "issues"), ("issue", "issues"), ("as_of", "issues"), ("periods", "issues"),
                     ("format", "formats"), ("locator", "locators"), ("url", "locators")):
        if old in data:
            if new in data:
                raise SelectionError("selection.conflicting_query_alias")
            item = data.pop(old)
            data[new] = (item,) if isinstance(item, (str, date)) else tuple(item)
    if "issues" in data:
        data.setdefault("mode", "exact")
    elif "date_from" in data or "date_to" in data:
        data.setdefault("mode", "range")
    return IssueQuery(**_mapping(data, IssueQuery))


@dataclass(frozen=True, slots=True)
class SelectionReport:
    query_identity: str
    basis_identity: str
    requested: tuple[str, ...] = ()
    observed: tuple[str, ...] = ()
    selected: tuple[str, ...] = ()
    missing: tuple[str, ...] = ()
    ambiguous: tuple[str, ...] = ()
    excluded: tuple[str, ...] = ()
    membership_closed: bool = False
    reasons: tuple[str, ...] = ()
    assessment: Assessment = Assessment()
    parent_assessment: Assessment = Assessment()

    def __post_init__(self):
        if not self.query_identity or not self.basis_identity or type(self.membership_closed) is not bool:
            raise SelectionError("selection.invalid_report")
        for name in ("requested", "observed", "selected", "missing", "ambiguous", "excluded", "reasons"):
            object.__setattr__(self, name, _tokens(getattr(self, name), name, allow_empty=name in {"requested", "missing"}))
        if not set(self.selected) <= set(self.observed) or set(self.selected) & (set(self.excluded) | set(self.ambiguous)):
            raise SelectionError("selection.report_scope_conflict")


def publication_key(asset):
    return fingerprint((asset.source_id, asset.issue_id, asset.asset_id))


def select_publication_assets(listing, query, *, source_ids=()):
    """Select actual candidates and report missing/ambiguous membership.

    Representation preferences only choose among formats. Two differing assets
    at the same logical coordinate and format still require revision evidence.
    """
    if not isinstance(listing, PublicationListing):
        raise SelectionError("publication.listing_required")
    query = issue_query(query)
    if len(listing.entries) > query.max_items:
        raise SelectionError("selection.candidate_limit")
    allowed_sources = set(source_ids)
    if allowed_sources and query.source_ids and not set(query.source_ids) <= allowed_sources:
        raise SelectionError("selection.source_scope_conflict")
    sources = set(query.source_ids) or allowed_sources
    candidates, excluded = [], []
    observed = tuple(dict.fromkeys(publication_key(a) for a in listing.entries))
    expected = query.issues if query.mode == "exact" else query.expected_issues
    for asset in listing.entries:
        accepted = (not sources or asset.source_id in sources) and (not query.asset_ids or asset.asset_id in query.asset_ids)
        accepted &= not query.locators or asset.locator in query.locators
        if expected:
            accepted &= asset.issue_id in expected
        if query.mode == "exact" and not query.issues:
            accepted = False
        if query.mode == "rolling":
            accepted &= asset.issue_id in {"", "rolling"} or asset.metadata.get("issue_model") == "rolling"
        if query.formats:
            accepted &= asset.format in query.formats
        if accepted and (query.date_from is not None or query.date_to is not None):
            token = asset.issue_id if query.date_axis == "issue_id" else asset.metadata.get(query.date_axis)
            day = _day(token)
            if day is None:
                raise SelectionError("selection.date_axis_unavailable")
            accepted &= (query.date_from is None or day >= query.date_from) and (query.date_to is None or day <= query.date_to)
        if accepted:
            candidates.append(asset)
        else:
            excluded.append(publication_key(asset))
    if query.mode == "latest":
        # Latest is per source, so one source cannot erase another source's issue.
        recent = {}
        for asset in candidates:
            token = asset.issue_id if query.date_axis == "issue_id" else asset.metadata.get(query.date_axis)
            day = _issue_order(token) if query.date_axis == "issue_order" else _day(token)
            if day is None:
                raise SelectionError("selection.date_axis_unavailable")
            recent.setdefault(asset.source_id, set()).add(day)
        try:
            admitted = {source: set(sorted(days, reverse=True)[:query.latest]) for source, days in recent.items()}
        except TypeError:
            raise SelectionError("selection.incomparable_issue_order") from None
        retained = []
        for asset in candidates:
            token = asset.issue_id if query.date_axis == "issue_id" else asset.metadata.get(query.date_axis)
            actual = _issue_order(token) if query.date_axis == "issue_order" else _day(token)
            if actual in admitted[asset.source_id]:
                retained.append(asset)
            else:
                excluded.append(publication_key(asset))
        candidates = retained
    groups = {}
    for asset in candidates:
        group = groups.setdefault(publication_key(asset), {})
        group.setdefault(fingerprint(asset), asset)
    selected, ambiguous = [], []
    for key, alternatives in groups.items():
        entries = tuple(alternatives.values())
        if query.formats:
            preferred = min(query.formats.index(item.format) for item in entries)
            entries = tuple(item for item in entries if query.formats.index(item.format) == preferred)
        if len(entries) != 1:
            ambiguous.append(key)
        else:
            selected.append(entries[0])
    # Exact issue order is caller-owned; other modes use deterministic coordinates.
    ranks = {value: index for index, value in enumerate(expected)}
    selected.sort(key=lambda item: (ranks.get(item.issue_id, len(ranks)), item.source_id, item.issue_id, item.asset_id))
    present = {item.issue_id for item in selected}
    requested, satisfied, missing = tuple(expected), tuple(sorted(present)), ()
    if expected:
        scope_sources = tuple(sorted(sources)) or (None,)
        scope_assets = query.asset_ids or (None,)
        if len(scope_sources) * len(scope_assets) * len(expected) > query.max_items:
            raise SelectionError("selection.expected_membership_limit")
        scoped = len(scope_sources) > 1 or bool(query.asset_ids)
        memberships = tuple((source, issue, asset) for source in scope_sources
                            for issue in expected for asset in scope_assets)
        def membership_key(member):
            return fingerprint(("requested_publication", *member)) if scoped else member[1]
        requested = tuple(membership_key(member) for member in memberships)
        observed_memberships = {(source, item.issue_id, asset) for item in selected
                                for source in (item.source_id, None) for asset in (item.asset_id, None)}
        satisfied = tuple(membership_key(member) for member in memberships if member in observed_memberships)
        satisfied_set = set(satisfied)
        missing = tuple(value for value in requested if value not in satisfied_set)
    closed = bool(listing.assessment.complete)
    complete = (closed or query.coverage_intent == "selected" and (bool(selected) or query.mode == "exact" and not query.issues)) and not missing and not ambiguous
    assessment = Assessment("complete" if complete else "partial", listing.assessment.findings,
        expected=requested, observed=satisfied,
        qualifications=listing.assessment.qualifications | frozenset({"selected_publication_scope"})
        | (frozenset({"latest_observed_only"}) if query.mode == "latest" else frozenset()))
    selected_keys = tuple(publication_key(item) for item in selected)
    excluded_keys = tuple(key for key in dict.fromkeys(excluded) if key not in groups)
    report = SelectionReport(query.identity, fingerprint(listing), requested, observed, selected_keys, missing,
        tuple(ambiguous), excluded_keys, closed,
        (() if closed else ("publication.discovery_incomplete",)), assessment, listing.assessment)
    if ambiguous and query.ambiguity == "reject":
        raise SelectionError("publication.ambiguous_asset", report=report)
    return AssetSelection(tuple(selected), assessment), report


def _issue_order(value):
    if isinstance(value, (tuple, list)):
        value = tuple(value)
        if not value or len(value) > 8 or any(type(part) not in {int, str, date} for part in value):
            raise SelectionError("selection.invalid_issue_order")
    elif type(value) not in {int, str, date}:
        raise SelectionError("selection.invalid_issue_order")
    return value


@dataclass(frozen=True, slots=True)
class SubjectChoice:
    namespace: str
    subject_id: str
    label: str | None = None
    reference_identity: str | None = None

    def __post_init__(self):
        _tokens((self.namespace,), "subject_namespace")
        _tokens((self.subject_id,), "subject_id")
        for value in (self.label, self.reference_identity):
            if value is not None and (not isinstance(value, str) or not value or len(value) > 2048):
                raise SelectionError("selection.invalid_subject_label")


@dataclass(frozen=True, slots=True)
class ObservationQuery:
    filters: Mapping[str, tuple[object, ...]] = field(default_factory=dict)
    periods: tuple[object, ...] | None = None
    date_from: date | None = None
    date_to: date | None = None
    period_field: str = "period"
    interval_mode: str = "contained"
    subjects: tuple[SubjectChoice, ...] | None = None
    metrics: tuple[str, ...] | None = None
    order_by: tuple[str, ...] = ()
    limit: int | None = None
    expected_members: tuple[str, ...] = ()
    max_items: int = 1000000

    def __post_init__(self):
        if not isinstance(self.filters, Mapping) or len(self.filters) > 64:
            raise SelectionError("selection.invalid_observation_filters")
        normalized = {}
        for key, values in self.filters.items():
            _tokens((key,), "filter_field")
            values = tuple(values) if isinstance(values, (tuple, list, set, frozenset)) else (values,)
            if len(values) > MAX_SELECTION_ITEMS:
                raise SelectionError("selection.filter_limit")
            normalized[key] = immutable(values)
        object.__setattr__(self, "filters", immutable(normalized))
        if self.periods is not None:
            object.__setattr__(self, "periods", tuple(immutable(v) for v in self.periods))
            if len(self.periods) > MAX_SELECTION_ITEMS:
                raise SelectionError("selection.period_limit")
        for name in ("date_from", "date_to"):
            object.__setattr__(self, name, _day(getattr(self, name)))
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise SelectionError("selection.date_range_invalid")
        if not isinstance(self.period_field, str) or not self.period_field or self.interval_mode not in {"contained", "overlap"}:
            raise SelectionError("selection.period_policy_invalid")
        if self.subjects is not None:
            choices = tuple(item if isinstance(item, SubjectChoice) else SubjectChoice(**item) for item in self.subjects)
            if len(choices) > MAX_SELECTION_ITEMS or len({(v.namespace, v.subject_id) for v in choices}) != len(choices):
                raise SelectionError("selection.duplicate_subject")
            object.__setattr__(self, "subjects", choices)
        for name in ("metrics", "order_by", "expected_members"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _tokens(value, name))
        if self.limit is not None:
            _limit(self.limit, "limit", zero=True, maximum=1000000)
        _limit(self.max_items, maximum=1000000)

    @property
    def identity(self):
        return fingerprint(self)


def observation_query(value):
    return value if isinstance(value, ObservationQuery) else ObservationQuery(**_mapping(value, ObservationQuery))


def observation_key(row, grain=None):
    if grain is None:
        grain = ("period", "metric", "subject_namespace", "subject", "unit", "scale", "perimeter",
                 "measure_kind", "frequency", "period_kind", "basis", "value_basis", "dimensions",
                 "legal_kind", "currency", "portfolio", "activity", "bank", "sex", "age")
    return fingerprint(tuple((name, row.get(name)) for name in grain))


def select_observations(dataset, query):
    """Project exact rows while retaining parent coverage and scientific limits."""
    if not isinstance(dataset, SourceDataset):
        raise SelectionError("selection.dataset_required")
    query = observation_query(query)
    subject_order = {(item.namespace, item.subject_id): index for index, item in enumerate(query.subjects or ())}
    rows = []
    for row in dataset.rows:
        if not all(row.get(key) in values for key, values in query.filters.items()):
            continue
        if query.subjects is not None and (str(row.get("subject_namespace")), str(row.get("subject"))) not in subject_order:
            continue
        if query.metrics is not None and row.get("metric") not in query.metrics:
            continue
        period = row.get(query.period_field)
        if query.periods is not None and period not in query.periods:
            continue
        if query.date_from is not None or query.date_to is not None:
            if isinstance(period, (tuple, list)) and len(period) == 2:
                start, end = map(_day, period)
            else:
                start = end = _day(period)
            if start is None or end is None or start > end:
                raise SelectionError("selection.period_unavailable")
            lower, upper = (end, start) if query.interval_mode == "overlap" else (start, end)
            if query.date_from and lower < query.date_from or query.date_to and upper > query.date_to:
                continue
        rows.append(row)
        if len(rows) > query.max_items:
            raise SelectionError("selection.output_limit")
    if query.order_by:
        try:
            rows.sort(key=lambda row: tuple((row.get(key) is None, row.get(key)) for key in query.order_by))
        except TypeError:
            raise SelectionError("selection.incomparable_order") from None
    if query.subjects is not None:
        rows.sort(key=lambda row: subject_order[(str(row.get("subject_namespace")), str(row.get("subject")))])
    if query.limit is not None:
        rows = rows[:query.limit]
    from .history import history_grain, history_value_identity
    grain = history_grain(dataset)
    selected = tuple(dict.fromkeys(observation_key(row, grain or None) for row in rows))
    missing = tuple(key for key in query.expected_members if key not in selected)
    parent_identity = history_value_identity(dataset)
    coverage = SelectedScopeCoverage(parent_identity, query.identity, query.expected_members or selected, selected,
        missing, dataset.assessment, membership_closed=True)
    # The selection proves its own membership, not stronger scientific validity
    # than its accepted parent. Complete parent + deliberate subset stays complete.
    status = "complete" if dataset.assessment.complete and not missing else "partial"
    assessment = Assessment(status, dataset.assessment.findings, query.expected_members or selected, selected,
        dataset.assessment.qualifications | frozenset({"selected_scope"}), coverage)
    from .history import project_history, history_view_labels
    membership = project_history(dataset, rows, query_identity=query.identity,
        expected_coordinates=query.expected_members)
    scopes = {fingerprint(value): value for value in (*membership.selection_scopes, coverage)}
    membership = replace(membership, selection_coverage=coverage,
        selection_scopes=tuple(scopes[key] for key in sorted(scopes)))
    source_id, issue_id = history_view_labels(membership)
    return replace(dataset, rows=tuple(rows), source_id=source_id, issue_id=issue_id, native=None, assessment=assessment,
        lineage=(*dataset.lineage, parent_identity), history_membership=membership)


@dataclass(frozen=True, slots=True)
class MemberOutcome:
    member_key: str
    ordinal: int
    outcome: str
    available_stages: tuple[str, ...] = ()
    references: tuple[object, ...] = ()
    diagnostics: tuple[str, ...] = ()
    effect_state: str | None = None

    def __post_init__(self):
        if (not self.member_key or type(self.ordinal) is not int or self.ordinal < 0
                or self.outcome not in {"succeeded", "partial", "failed", "cancelled", "unknown", "not_attempted", "excluded"}
                or self.effect_state not in {None, "confirmed", "unknown", "rejected", "pending"}):
            raise SelectionError("selection.invalid_member_outcome")
        for name in ("available_stages", "diagnostics"):
            object.__setattr__(self, name, _tokens(getattr(self, name), name))
        object.__setattr__(self, "references", immutable(tuple(self.references)))
