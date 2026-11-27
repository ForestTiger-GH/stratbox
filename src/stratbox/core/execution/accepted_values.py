"""Bounded accepted-value metadata for journal replay and authority checks.

The journal contains identities and qualified references, never native tables,
temporary tokens, request credentials, or complete input/output payloads.
"""
from __future__ import annotations

from dataclasses import replace

from stratbox.shared.data.source_context import SourceCoordinate, SourceUse
from stratbox.shared.data.values import (
    Assessment, EncodedProduct, FetchEvidence, IdentifiedMaterial,
    ImmutableMaterialRef, ReadEvidence, SnapshotRef, fingerprint,
)


def _unique(values):
    return tuple(dict.fromkeys(values))


def accepted_record(service, run, task, name, value, inputs, *, value_identity, basis, accepted_index=None):
    from .owned_values import input_values
    command = task.spec.command
    accepted_index = service._accepted if accepted_index is None else accepted_index
    inherited, trusted, dependencies = [], [], set()
    for item in input_values(inputs.values()):
        try:
            key = service._values.identity(item)
        except (ValueError, TypeError):
            continue
        previous = accepted_index.get(key)
        if previous:
            inherited.extend(previous['source_uses'])
            trusted.extend(previous.get('trusted_source_uses', ()))
            dependencies.update(previous.get('certificate_dependencies', ()))
        else:
            inherited.extend(getattr(item,'source_uses',()))
    uses = list(getattr(value, 'source_uses', ()))
    physical = value.material if isinstance(value, IdentifiedMaterial) else value
    if isinstance(value, IdentifiedMaterial):
        uses.append(SourceUse(SourceCoordinate(value.claim.source_id,
            issue_id=value.claim.issue_id or None, asset_id=value.claim.asset_id,
            material_identity=value.identity), 'material', value.claim.attribution))
        if command.id == 'command.material.identify':
            evidence = inputs.get('evidence')
            provenance = accepted_index.get(service._values.identity(evidence)) if evidence is not None else None
            acquired = provenance and provenance.get('produced_by') in {
                'command.material.fetch', 'command.material.receive', 'command.material.read'}
            competent = command.method.locator != 'stratbox.core.commands.materials:material_identify'
            if acquired and competent:
                # Identification can preserve caller-supplied uses. Grant new
                # authority only to the exact claim the competent method has
                # checked; an unrelated "verified" use remains caller data.
                coordinate = SourceCoordinate(value.claim.source_id,
                    issue_id=value.claim.issue_id or None, asset_id=value.claim.asset_id,
                    material_identity=value.identity)
                qualifications = value.assessment.qualifications
                verified = value.claim.attribution == 'verified' and 'verified_source' in qualifications
                delivered = (provenance.get('produced_by') == 'command.material.read'
                    and value.claim.attribution == 'recognized' and 'filename_attribution' in qualifications)
                trusted.extend(use for use in uses if use.coordinate == coordinate
                    and use.evidence_ref in {None, 'sha256:' + value.identity.sha256}
                    and (verified and use.qualification == 'verified'
                         and use.input_role in {'publication_acquisition', 'material'}
                         or delivered and use.qualification == 'filename_attribution'
                         and use.input_role == 'delivered_material'))
    if not uses:
        uses.extend(inherited)
    source_id = getattr(value, 'source_id', None)
    if source_id and not uses:
        metadata = getattr(physical, 'metadata', {})
        uses.append(SourceUse(SourceCoordinate(source_id,
            issue_id=getattr(value, 'issue_id', None) or metadata.get('issue_id') or None,
            asset_id=metadata.get('asset_id'), material_identity=getattr(physical, 'identity', None)
                if hasattr(getattr(physical, 'identity', None), 'sha256') else None),
            'acquisition' if command.id in {'command.material.fetch','command.material.receive','command.material.read'} else 'result',
            'observed'))
    uses, trusted = _unique(uses), _unique(trusted)
    if len(uses) > 10000 or len(trusted) > 10000:
        raise ValueError('value.source_metadata_limit')
    certificates = tuple(getattr(value, 'validation_certificates', ()))
    from stratbox.shared.data.values import SourceDataset
    if isinstance(value, SourceDataset):
        from stratbox.shared.data.history import history_certificate_dependencies
        dependencies.update(history_certificate_dependencies(value))
    if command.id == 'command.observations.validate' and certificates:
        from stratbox.shared.data.history import verify_history_certificates
        inherited_certificates = {fingerprint(c) for item in inputs.values()
                                  for c in getattr(item, 'validation_certificates', ())}
        def authority(certificate):
            certificate_id = fingerprint(certificate)
            if certificate_id not in inherited_certificates:
                return True
            if any(certificate_id in record.get('validation_certificates', ())
                   for record in accepted_index.values()):
                return True
            checker = getattr(service.providers.get('source_state'), 'has_validation_certificate', None)
            return bool(checker and checker(certificate_id))
        if not all(authority(certificate) for certificate in certificates) or not verify_history_certificates(value, authority):
            raise ValueError('validation.certificate_authority_or_binding_required')
    return {'id': fingerprint((run.run_id, task.spec.task_id, name, value_identity)),
            'value_identity': value_identity,
            'basis': basis, 'source_uses': uses, 'trusted_source_uses': trusted,
            'trusted_source_use_ids': tuple(fingerprint(use) for use in trusted),
            'produced_by': command.id,
            'certificate_dependencies': tuple(sorted(dependencies)),
            'validation_certificates': tuple(fingerprint(c) for c in certificates)
                if command.id == 'command.observations.validate' else ()}


def compact_reference(value):
    """Keep immutable physical authority while omitting arbitrary metadata."""
    if isinstance(value, ImmutableMaterialRef):
        admitted = {'source_id','issue_id','asset_id','filename','member','media_type','charset','format'}
        metadata = {key: item for key, item in value.metadata.items()
                    if key in admitted and (item is None or isinstance(item, (str, int, bool)))}
        from urllib.parse import urlsplit
        lineage = []
        for item in value.lineage:
            if isinstance(item, FetchEvidence):
                headers = {str(k).lower():v for k,v in item.headers.items()
                    if str(k).lower() in {'content-type','etag','last-modified','vary'}
                    and isinstance(v,str) and len(v) <= 8192 and not any(ord(c) < 32 for c in v)}
                parts = urlsplit(item.effective_locator or '')
                safe = 'https://' + parts.hostname + '/' if parts.scheme == 'https' and parts.hostname else None
                lineage.append(replace(item, headers=headers, effective_locator=safe))
            elif isinstance(item, ReadEvidence):
                lineage.append(item)
        return replace(value, metadata=metadata, lineage=tuple(lineage[-2:]))
    return value if isinstance(value, SnapshotRef) else None


def accepted_fact(record, value, *, inputs, outputs):
    physical = value.material if isinstance(value, IdentifiedMaterial) else value
    reference = compact_reference(physical)
    if isinstance(value,IdentifiedMaterial) and isinstance(reference,ImmutableMaterialRef):
        reference = replace(reference,source_uses=_unique((*reference.source_uses,*value.source_uses)),
            metadata={**dict(reference.metadata),'source_id':reference.source_id or value.claim.source_id,
                      'issue_id':value.claim.issue_id,'asset_id':value.claim.asset_id})
    evidence = outputs.get('evidence')
    request = outputs.get('request') or inputs.get('request')
    metadata = getattr(physical, 'metadata', {})
    source_id = getattr(value, 'source_id', None) or getattr(request, 'source_id', None)
    issue_id = getattr(value, 'issue_id', None) or metadata.get('issue_id')
    asset_id = metadata.get('asset_id')
    if record['source_uses']:
        first = record['source_uses'][0].coordinate
        source_id, issue_id, asset_id = source_id or first.source_id, issue_id or first.issue_id, asset_id or first.asset_id
    assessment = value if isinstance(value, Assessment) else getattr(value, 'assessment', None)
    if not isinstance(assessment, Assessment):
        assessment = outputs.get('assessment') if isinstance(outputs.get('assessment'), Assessment) else None
    if record['produced_by'] in {
            'command.artifact.commit', 'command.artifact.materialize'}:
        # A content-addressed receipt retains its original logical provenance.
        # A new accepted consumer can carry a different qualification over the
        # same bytes; record that consumer's coverage without rewriting receipt.
        inherited_assessment = getattr(inputs.get('material'), 'assessment', None)
        if isinstance(inherited_assessment, Assessment):
            assessment = inherited_assessment
    effect_ids = tuple(dict.fromkeys(filter(None, (
        getattr(physical, 'effect_id', None), getattr(value, 'effect_id', None)))))
    result = {'accepted_value_id':record['id'], 'value_identity':record['value_identity'],
        'value_kind':type(value).__module__ + ':' + type(value).__qualname__,
        'processing_basis':record['basis'], 'source_uses':record['source_uses'],
        'trusted_source_uses':record['trusted_source_uses'],
        'certificate_ids':record['validation_certificates'], 'assessment':assessment,
        'certificate_dependencies':record.get('certificate_dependencies', ()),
        'retained_reference':reference, 'persistent':reference is not None,
        'effect_ids':effect_ids, 'source_id':source_id, 'issue_id':issue_id, 'asset_id':asset_id,
        'selection_identity':fingerprint(inputs['query']) if 'query' in inputs else None}
    if isinstance(value, EncodedProduct):
        result['represents_value_identity'] = value.descriptor.get('value_identity')
    if isinstance(value,(FetchEvidence,ReadEvidence)) and record['produced_by'] in {
            'command.material.fetch','command.material.receive','command.material.read'}:
        result['acquisition_evidence_id'] = record['value_identity']
    receipt_value = getattr(value, 'value', None)
    destination = getattr(receipt_value, 'destination', None)
    if destination is not None:
        result['destination_identity'] = fingerprint((getattr(receipt_value, 'provider_scope', None), destination))
    if source_id and isinstance(evidence, (FetchEvidence, ReadEvidence)):
        result['observation'] = {'source_id':source_id,'issue_id':issue_id,'asset_id':asset_id,
            'observation_id':getattr(evidence,'observation_id',None) or fingerprint(evidence),
            'observed_at':evidence.observed_at,
            'comparison_scope':fingerprint((source_id,issue_id,asset_id)),
            'evidence_identity':fingerprint(evidence),'material_identity':evidence.material_identity,
            'representation_identity':getattr(evidence,'representation_identity',None),
            'retained_reference':reference,'acquisition_evidence':evidence}
        result['observation_ref'] = result['observation']['observation_id']
    return result
