"""Neutral publication evidence selection and source-assessment fallbacks."""
from __future__ import annotations
from stratbox.core.execution.service import ExecutionFailure
from stratbox.shared.data.values import AssetSelection, PublicationListing, UpdateAssessment, fingerprint
from ._settings import _get


def publication_scan(inputs, settings, context):
    raise ExecutionFailure("publication.source_specification_required")


def issue_select(inputs, settings, context):
    from stratbox.shared.data.selection import select_publication_assets, SelectionError
    query = inputs.get("query")
    if query is None:
        query = context.parameters.get("query", {})
    expected = _get(settings, "source_id")
    try:
        selection, report = select_publication_assets(inputs["listing"], query,
            source_ids=(expected,) if expected else ())
    except SelectionError as error:
        raise ExecutionFailure(error.code) from error
    return {"selection": selection, "report": report}


def source_assess(inputs, settings, context):
    validation = retained_validation_assessment(inputs,context)
    if validation is not None:
        return validation
    candidate, previous = inputs["evidence"], inputs.get("baseline")
    incomplete = any(not getattr(value.assessment, "complete", False) for value in (candidate, previous)
                     if value is not None and hasattr(value, "assessment"))
    if incomplete or isinstance(candidate, PublicationListing):
        return {"assessment": UpdateAssessment("unknown", _get(settings, "basis", "provided_evidence"),
            ("Evidence is incomplete or establishes only a publication listing, not actual asset content.",), evidence=(candidate, previous))}
    current = fingerprint(candidate)
    baseline = fingerprint(previous) if previous is not None else None
    return {"assessment": UpdateAssessment("first_seen" if previous is None else "unchanged" if current == baseline else "changed",
        _get(settings, "basis", "provided_evidence"), predecessor=baseline, candidate=current)}


def retained_validation_assessment(inputs, context):
    """A 304 validates a stored representation, not fresh remote byte equality."""
    from stratbox.shared.data.values import FetchEvidence
    observed = inputs.get('acquisition_evidence')
    if not isinstance(observed,FetchEvidence) or observed.validation_kind != 'retained_validation':
        return None
    verify = getattr(context,'verify_acquisition_evidence',None)
    if not verify or not verify(observed) or observed.status_code != 304:
        raise ExecutionFailure('source.validation_evidence_unverified')
    current = getattr(inputs.get('evidence'),'identity',None)
    previous = getattr(inputs.get('baseline'),'identity',None)
    if current != observed.material_identity:
        raise ExecutionFailure('source.validation_material_conflict')
    def coordinate(value):
        claim = getattr(value,'claim',None)
        metadata = getattr(value,'metadata',{})
        return (getattr(claim,'source_id',getattr(value,'source_id',None)),
                getattr(claim,'issue_id',metadata.get('issue_id')) or '',
                getattr(claim,'asset_id',metadata.get('asset_id')) or 'main')
    same_coordinate = coordinate(inputs.get('evidence')) == coordinate(inputs.get('baseline'))
    return {'assessment':UpdateAssessment('first_seen' if previous is None else 'unchanged' if previous == current and same_coordinate else 'changed',
        'retained_representation_validation',('http.304_does_not_establish_remote_byte_equality',),
        predecessor=getattr(previous,'sha256',None),candidate=current.sha256,
        evidence={'acquisition_identity':fingerprint(observed),'retained_effect_id':observed.retained_effect_id,
                  'representation_identity':observed.representation_identity,
                  'weak_validator':observed.headers.get('etag','').startswith('W/')})}


def publication_transcribe(inputs, settings, context):
    return {"publication": inputs["physical"]}
