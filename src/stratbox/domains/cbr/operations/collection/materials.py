"""A single bounded collection can read inline, retained and HTTP originals."""
from dataclasses import replace

from stratbox.core.execution import Completion, OperationFailure, run
from stratbox.core.limits import BudgetError
from stratbox.core.operations.source.originals import read_material
from stratbox.core.operations.source.validation import use_payload
from stratbox.core.runtime.capabilities import BindingError
from stratbox.domains.cbr.publications.access import ARCHIVE_TYPES, HTML_TYPES, XLSX_TYPES, receive_cbr
from stratbox.domains.cbr.publications.contracts import IdentifyRequest
from stratbox.domains.cbr.publications.admission import identify_value
from stratbox.domains.cbr.publications.profiles import acquisition_profile
from stratbox.domains.cbr.publications.catalog import source
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.snapshots import SnapshotCoverage, identifier
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.material_collections import CollectionDisposition, CollectionManifest, CollectionMember

from stratbox.domains.cbr.operations.collection.material_definitions import COLLECT_MATERIALS, CollectMaterial, CollectMaterialsRequest, MaterialCollection


def _receive(item, invocation, transport, store, limit):
    supplied = sum(value is not None for value in (item.payload, item.material, item.url))
    if supplied > 1:
        raise OperationFailure("cbr.collection.multiple_inputs")
    if item.payload is not None:
        use_payload(item.payload, invocation, role="original", limit=limit)
        return item.payload
    if item.material is not None:
        reader = invocation.provider("filestore", store, selection=item.selection)
        return read_material(item.material, reader, invocation, limit=limit, role="original")
    series = source(item.series_id)
    profile = acquisition_profile(series.acquisition_profile)
    url = item.url
    if url is None:
        if profile.kind not in {"fixed", "page"}:
            raise OperationFailure("cbr.collection.asset_url_required")
        url = profile.default_url
    media = (HTML_TYPES if item.format == "html" else
             ARCHIVE_TYPES if item.format in {"rar", "zip"} else
             frozenset({"application/x-dbf", "application/dbf", "application/octet-stream"})
             if item.format == "dbf" else XLSX_TYPES)
    reader = invocation.provider("http", transport, selection=item.selection)
    value = receive_cbr(url, roots=(), media_types=media, limit=limit, source_id=item.series_id,
                        transport=reader, invocation=invocation).payload
    # HTTP admission already charges the body; record lineage without charging
    # the same received bytes again through the inline-payload admission path.
    invocation.use(UsedInputReceipt.for_payload(value, "original"))
    return value


def collect_materials(request, *, transport=None, store=None, context=None):
    def work(req, invocation):
        if (not isinstance(req.items, tuple) or not req.items or len(req.items) > 10_000
                or any(not isinstance(item, CollectMaterial) for item in req.items)
                or type(req.max_batch_bytes) is not int or not 0 < req.max_batch_bytes <= 256 * 1024**2
                or type(req.continue_on_error) is not bool):
            raise OperationFailure("cbr.collection.selection_invalid")
        for item in req.items:
            try:
                identifier(item.key)
                series = source(item.series_id)
                if item.format not in series.formats:
                    raise ValueError("cbr.publication.format_unsupported")
            except ValueError as error:
                raise OperationFailure(str(error)) from None
        if len({item.key for item in req.items}) != len(req.items):
            raise OperationFailure("cbr.collection.selection_invalid")
        invocation.stage("collect_materials")
        originals, members, dispositions, inputs = [], [], [], []
        remaining, stop = req.max_batch_bytes, None
        for item in req.items:
            if stop is not None or invocation.cancelled() or remaining == 0:
                stop = stop or ("operation.cancelled" if invocation.cancelled() else "budget.batch_bytes")
                dispositions.append(CollectionDisposition(item.key, "not_attempted", stop))
                continue
            try:
                invocation.budget.checkpoint()
                payload = _receive(item, invocation, transport, store, remaining)
                if payload.identity.size > remaining:
                    raise OperationFailure("budget.batch_bytes")
                remaining -= payload.identity.size
                inputs.append(UsedInputReceipt("original", payload.identity, payload.media_type,
                    "reference_only" if item.material is not None else "inline", item.series_id))
                value = identify_value(IdentifyRequest(item.series_id, item.issue_id, payload, item.format, item.asset_id), invocation)
                name = (f"{item.series_id}/{item.issue_id}/{item.asset_id}.{item.format}"
                        if item.name is None else item.name)
                member = CollectionMember(item.key, name,
                    DataContract("cbr.publication.original", 1, DataRole.ORIGINALS), payload.identity,
                    payload.media_type, value.asset, value.artifact.identity)
                # Reject collisions while still preserving earlier completed work.
                CollectionManifest("cbr.originals", "validation", tuple(members) + (member,),
                    tuple(dispositions) + (CollectionDisposition(item.key, "completed"),), SnapshotCoverage("unknown"))
                invocation.account_output(payload.identity, key=f"original.{len(dispositions) + 1}")
            except (OperationFailure, BudgetError, BindingError) as error:
                code = error.diagnostic.code if isinstance(error, OperationFailure) else error.code
                dispositions.append(CollectionDisposition(item.key, "failed", code))
                if isinstance(error, BudgetError) or code == "operation.cancelled" or not req.continue_on_error:
                    stop = code
            except ValueError as error:
                code = str(error) if str(error).startswith(("cbr.", "collection.", "source.")) else "cbr.collection.invalid_material"
                dispositions.append(CollectionDisposition(item.key, "failed", code))
                if not req.continue_on_error:
                    stop = code
            else:
                originals.append((item.key, value))
                members.append(member)
                dispositions.append(CollectionDisposition(item.key, "completed"))
        manifest = CollectionManifest("cbr.originals", "content", tuple(members), tuple(dispositions),
            SnapshotCoverage("unknown", "Explicitly selected materials; complete publisher history is not asserted."),
            tuple(inputs))
        manifest = replace(manifest, version_id=manifest.identity.sha256)
        result = MaterialCollection(tuple(originals), manifest)
        invocation.record(manifest.identity)
        if manifest.complete:
            return result
        diagnostic = stop or next(item.diagnostic for item in dispositions if item.status != "completed")
        return Completion(result, "partial" if originals else "failed", diagnostic)
    return run(COLLECT_MATERIALS, request, work, context=context, providers={"http": transport, "filestore": store})
