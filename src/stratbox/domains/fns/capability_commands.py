"""Technical FNS command leaves; execution belongs to the common session."""
from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal
from functools import wraps
import re

from stratbox.core.execution.contracts import OperationFailure
from stratbox.core.operations.source.validation import use_payload
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.representation import Representation
from stratbox.shared.evidence import SourcePayload, UsedInputReceipt


def _scientific(function):
    """Expose bounded scientific rejections without leaking source content."""
    @wraps(function)
    def checked(request, invocation):
        from stratbox.core.formats.archives.members import ArchiveError
        from stratbox.core.runtime.dependencies import MissingExtra
        from stratbox.core.operations.source.validation import source_failure
        from .publications.sme.source import FnsError
        from .publications.legal_entities.source import SourceError
        try:
            return function(request, invocation)
        except MissingExtra:
            raise OperationFailure("provider.capability_missing") from None
        except (FnsError, SourceError, ArchiveError, ValueError) as error:
            code = str(error).split(":", 1)[0]
            if re.fullmatch(r"(?:fns|source|workbook|observations|view|dataset)\.[a-z0-9_.]{1,100}", code):
                raise OperationFailure(code) from None
            raise source_failure(error) from None
    return checked


def _family(request, value=None):
    series = request["series_id"]
    if series not in {"fns.sme", "fns.1yur"}:
        raise OperationFailure("fns.source_family_mismatch")
    if value is not None and getattr(getattr(value, "context", None), "series_id", None) != series:
        raise OperationFailure("fns.source_family_mismatch")
    return "sme" if series == "fns.sme" else "legal_entities"


def _use(value, invocation):
    batch = getattr(value, "batch", None)
    receipts = batch.lineage if batch is not None else getattr(value, "lineage", ())
    for receipt in receipts:
        invocation.use(receipt)
    if batch is not None:
        invocation.budget.charge("cells", len(batch.observations))
    elif hasattr(value, "records"):
        invocation.budget.charge("cells", sum(len(record.fields) for record in value.records))
    elif hasattr(value, "members"):
        invocation.budget.charge("cells", sum(len(sheet.cells) for _, workbook in value.members for sheet in workbook.sheets))
    return value


@_scientific
def extract(request, invocation):
    family = _family(request)
    release = request["release"]
    if release.series_id != request["series_id"]:
        raise OperationFailure("fns.source_family_mismatch")
    payload = request["payload"]
    if family == "sme":
        from .tables.sme.extraction import extract_json
        value = extract_json(payload, release, budget=invocation.budget, checkpoint=invocation.check_cancelled)
    else:
        from .tables.legal_entities.extraction import extract_bundle
        decoder = None
        if payload.data.startswith(b"Rar!"):
            decoder = invocation.provider("archive_decoder")
        value = extract_bundle(payload, release, budget=invocation.budget,
            checkpoint=invocation.check_cancelled, rar_reader=decoder)
    for receipt in value.lineage:
        invocation.use(receipt)
    return value


@_scientific
def readable(request, invocation):
    value = request["flake"]
    family = _family(request, value)
    if family == "sme":
        from .tables.sme.readable import readable as readable_sme
        result = readable_sme(_use(value, invocation))
    else:
        from .tables.legal_entities.readable import readable as readable_1yur
        result = readable_1yur(_use(value, invocation))
    return result


@_scientific
def validate(request, invocation):
    value = request["flake"]
    family = _family(request, value)
    if family == "sme":
        from .tables.sme.projection import validate as validate_sme
        return validate_sme(_use(value, invocation))
    else:
        from .tables.legal_entities.projection import validate as validate_1yur
        return validate_1yur(_use(value, invocation))


@_scientific
def project(request, invocation):
    value = request["flake"]
    family = _family(request, value)
    if family == "sme":
        from .tables.sme.projection import project_counts
        result = project_counts(_use(value, invocation))
    else:
        from .tables.legal_entities.projection import project_reported
        result = project_reported(_use(value, invocation), checkpoint=invocation.check_cancelled)
    return result


@_scientific
def align(request, invocation):
    value = request["projection"]
    family = _family(request, value)
    if family == "sme":
        from .integration.sme.alignment import align as align_sme
        return align_sme(_use(value, invocation))
    else:
        from .integration.legal_entities.alignment import align as align_1yur
        return align_1yur(_use(value, invocation))


@_scientific
def compare_flakes(request, invocation):
    from .tables.comparison import compare_flakes as compare
    _family(request, request["before"])
    _family(request, request["after"])
    return compare(_use(request["before"], invocation), _use(request["after"], invocation))


@_scientific
def compare_datasets(request, invocation):
    from stratbox.shared.data.calculations import compare_observations
    _family(request, request["before"])
    _family(request, request["after"])
    return compare_observations(_use(request["before"], invocation).batch,
                                _use(request["after"], invocation).batch)


@_scientific
def calculate_changes(request, invocation):
    from .analytics.calculations import net_changes
    _family(request, request["before"])
    _family(request, request["after"])
    return net_changes(_use(request["before"], invocation), _use(request["after"], invocation),
        metric_ids=request["metric_ids"])


@_scientific
def calculate_shares(request, invocation):
    from .analytics.calculations import shares
    _family(request, request["dataset"])
    return shares(_use(request["dataset"], invocation), **{name: request[name] for name in
        ("numerator_metric", "denominator_metric", "numerator_dimensions", "denominator_dimensions")})


@_scientific
def view(request, invocation):
    from .products.views import prepare_view
    _family(request, request["dataset"])
    return prepare_view(_use(request["dataset"], invocation), **{name: request[name] for name in
        ("metric_ids", "subject_ids", "period_kinds", "dimensions")})


@_scientific
def render(request, invocation):
    from .products.rendering import render as encode
    _family(request, request["view"])
    return encode(_use(request["view"], invocation), format=request["format"], budget=invocation.budget)


def _codec(series, layer):
    if layer == "flake":
        if series == "fns.sme":
            from .tables.sme.snapshots import flake_snapshot as snapshot_sme, flake_from_snapshot as replay_sme
            return snapshot_sme, replay_sme
        else:
            from .tables.legal_entities.snapshots import flake_snapshot as snapshot_1yur, flake_from_snapshot as replay_1yur
            return snapshot_1yur, replay_1yur
    if layer == "projection":
        from .tables.snapshots import projection_snapshot, projection_from_snapshot
        return projection_snapshot, projection_from_snapshot
    if layer == "dataset":
        from .integration.snapshots import dataset_snapshot, dataset_from_snapshot
        return dataset_snapshot, dataset_from_snapshot
    if layer == "calculation":
        from .analytics.calculations import calculation_snapshot, calculation_from_snapshot
        return calculation_snapshot, calculation_from_snapshot
    if layer == "view":
        from .products.views import view_snapshot, view_from_snapshot
        return view_snapshot, view_from_snapshot
    raise ValueError("fns.snapshot_layer_unknown")


@_scientific
def snapshot(request, invocation):
    layer = request["layer"]
    value = request[layer]
    _family(request, value)
    result = _codec(request["series_id"], layer)[0](_use(value, invocation))
    return result


@_scientific
def replay(request, invocation):
    from stratbox.core.execution import values
    values.use_value(request["snapshot"], invocation, "retained_snapshot", include_lineage=True)
    result = _codec(request["series_id"], request["layer"])[1](request["snapshot"])
    _family(request, result)
    return result


def _artifact(value, representation, invocation, role):
    from stratbox.shared.materials import MaterialArtifact
    from stratbox.shared.source_publications import SourceAssetIdentity
    return MaterialArtifact(DataContract(value.context.series_id + "." + role, 1,
        DataRole.READABLE if role == "readable" else DataRole.PRODUCTS), representation,
        tuple(invocation.used_inputs), value.context.series_id,
        SourceAssetIdentity(value.context.series_id, value.context.issue_id, value.context.asset_id))


@_scientific
def readable_artifact(request, invocation):
    representation = readable(request, invocation)
    return _artifact(request["flake"], representation, invocation, "readable")


@_scientific
def render_artifact(request, invocation):
    representation = render(request, invocation)
    return _artifact(request["view"], representation, invocation, "rendered_view")


@_scientific
def acquire(request, invocation):
    from .publications.contracts import ReleaseContext
    release = request["release"]
    if not isinstance(release, ReleaseContext) or release.series_id != request["series_id"]:
        raise OperationFailure("fns.source_family_mismatch")
    transport = invocation.provider("http")
    if _family(request) == "sme":
        if request["url"] is not None:
            raise OperationFailure("fns.sme.fixed_endpoint_required")
        from .publications.sme.access import acquire_source as acquire_sme
        acquired = acquire_sme(release.observation_date, invocation, transport)
    else:
        from stratbox.shared.data.releases import ReleaseLink
        from .publications.legal_entities.access import acquire_source as acquire_1yur
        if not request["url"]:
            raise OperationFailure("request.release_link_required")
        acquired = acquire_1yur(ReleaseLink(release.observation_date, request["url"]), invocation, transport)
    context = replace(release, captured_at=acquired.receipt.observed_at_utc)
    from stratbox.core.execution.contracts import EffectReceipt
    from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
    effect_id = ByteIdentity.of(canonical_manifest_bytes({"source_id": release.series_id,
        "issue_id": release.issue_id, "request": acquired.receipt.request_sha256,
        "observed_at": acquired.receipt.observed_at_utc, "payload": acquired.payload.identity.sha256})).sha256
    invocation.effect(EffectReceipt("network.receive", "confirmed", identity=acquired.payload.identity,
        effect_id=effect_id, guarantee="acquisition_receipt"))
    return {"payload": acquired.payload, "release": context, "acquisition": acquired.receipt}


@_scientific
def discover(request, invocation):
    payload = request["index"]
    use_payload(payload, invocation, role="source_index", limit=2_000_000)
    if _family(request) == "sme":
        from .tables.sme.parser import discover_dates
        return tuple(discover_dates(payload.data))
    from .publications.legal_entities.source import BASE, allowed_url, extract_releases
    from .publications.legal_entities.source_history import MIN_DATE, releases_from_page
    from stratbox.shared.data.releases import ReleaseLink
    year = request["year"]
    if type(year) is not int or not MIN_DATE.year <= year <= 2099:
        raise OperationFailure("request.invalid_year")
    base = request["base_url"]
    if not base or base == BASE:
        raise OperationFailure("request.release_index_required")
    allowed_url(base, "page")
    missing = set()
    found = releases_from_page(payload.data, base, missing=missing, require_releases=False)
    if not found and not missing:
        found = extract_releases(payload.data, base)
    links = tuple(ReleaseLink(day, url) for day, url in sorted(found.items()) if day.year == year)
    gaps = tuple(sorted(day for day in missing - found.keys() if day.year == year))
    if not links and not gaps:
        raise OperationFailure("source.year_unavailable")
    return {"releases": links, "missing": gaps, "membership_closed": True,
        "history_complete": False}


@_scientific
def regional_product(request, invocation):
    value = request["flake"]
    if _family(request, value) == "sme":
        from .tables.sme.extraction import json_text
        from .tables.sme.parser import decode_snapshot
        from .products.sme.regional_csv import write_csv, read_csv
        rows = decode_snapshot(json_text(value).encode("utf-8"), value.context.observation_date)
        data = write_csv(rows)
        read_csv(data)
    else:
        from .tables.legal_entities.projection import select_part_i, CellBook
        from .tables.legal_entities.history import project_book
        from .integration.legal_entities.mapping import convert
        _, workbook = select_part_i(value)
        physical, _ = project_book(CellBook(workbook), value.context.observation_date,
            checkpoint=invocation.check_cancelled)
        data, _ = convert(value.context.observation_date, physical)
    _use(value, invocation)
    return Representation(request["series_id"] + ".regional-csv", 1, "text/csv", data)


@_scientific
def read_regional(request, invocation):
    """Admit an exact regional CSV as a partial, source-qualified dataset.

    Its absent source fields and national/district rows stay absent; reading the
    CSV never fabricates an original JSON asset or workbook evidence.
    """
    from stratbox.shared.data.observations import MetricRef, Observation, ObservationBatch, PeriodRef, SubjectRef
    from stratbox.shared.data.snapshots import SnapshotCoverage
    from stratbox.shared.data.source_context import SourceCoordinate, SourceUse
    from .integration.contracts import FnsDataset
    from .tables.contracts import FieldDisposition
    release, payload = request["release"], request["payload"]
    if release.series_id != request["series_id"]:
        raise OperationFailure("fns.source_family_mismatch")
    use_payload(payload, invocation, role="regional_csv", limit=30_000_000)
    observations = []
    if _family(request) == "sme":
        from .publications.sme.access import _check_date as check_sme_date
        check_sme_date(release.observation_date)
        from .products.sme.regional_csv import read_csv
        from .tables.sme.parser import COLUMNS
        from .integration.sme.alignment import PROFILE, METRICS
        rows = read_csv(payload.data)
        for code, row in sorted(rows.items()):
            for source, token in zip(COLUMNS[2:], row[2:]):
                invocation.check_cancelled()
                invocation.budget.charge("cells", 1)
                metric = METRICS["cnt_" + source] if "cnt_" + source in METRICS else source
                source_field = next(key for key, target in METRICS.items() if target == metric)
                observations.append(Observation(SubjectRef("fns.ssrf", code),
                    MetricRef(metric, "count", "stock", PROFILE, Decimal(1)), PeriodRef("as_of", release.observation_date),
                    (("published_label", row[1]), ("geographic_level", "0"), ("source_field", source_field)), "published_subject", int(token),
                    "reported", "csv-region:" + code + ":" + source, token))
    else:
        from .publications.legal_entities.access import _check_date as check_1yur_date
        check_1yur_date(release.observation_date)
        from .products.legal_entities.regional_csv import read_canonical
        from .integration.legal_entities.alignment import PROFILE
        from .integration.legal_entities.mapping import MAP_VERSION
        fields, rows = read_canonical(payload.data)
        for (code, label), row in rows.items():
            perimeter = "published_territory" if code else ("published_national" if label.casefold() == "российская федерация" else "published_district")
            for field, token in zip(fields[2:], row[2:]):
                invocation.check_cancelled()
                invocation.budget.charge("cells", 1)
                measure, kind = field[3:].split("__", 1)
                quantity = "stock" if measure in {"not_ceased", "bankruptcy_proceedings"} else "count"
                dimensions = (("region_code", code), ("published_label", label), ("legal_kind", kind))
                if quantity == "count":
                    dimensions += (("time_basis", "published_reporting_date_unspecified_accumulation"),)
                observations.append(Observation(SubjectRef("fns.1yur.geography", code + ":" + label if code else label),
                    MetricRef(measure, "count", quantity, MAP_VERSION, Decimal(1)), PeriodRef("as_of", release.observation_date),
                    dimensions, perimeter,
                    int(token), "reported", "csv-region:" + code + ":" + field, token))
    lineage = (UsedInputReceipt.for_payload(payload, "regional_csv"),)
    source = SourceUse(SourceCoordinate(request["series_id"], issue_id=release.issue_id, asset_id=release.asset_id,
        material_identity=payload.identity, semantic_profile_edition=request["series_id"] + ".regional-csv.v1"),
        "regional_csv", "declared")
    batch = ObservationBatch(request["series_id"] + ".regional_csv", 1, "source-" + payload.identity.sha256,
        tuple(observations), lineage, (source,))
    qualifications = ("source.regional_csv_subset", "source.physical_original_unavailable")
    if request["series_id"] == "fns.1yur":
        qualifications += ("source.ceased_bankruptcy_period_basis_unresolved",)
    dataset = FnsDataset(release, payload.identity, batch, PROFILE,
        SnapshotCoverage("partial", "Exactly the supplied regional CSV projection; omitted source fields are unavailable."),
        qualifications, (FieldDisposition("original", None, "not_in_supplied_csv"),), parents=(payload.identity,))
    return dataset
