"""Export caller-selected CBR form publications to one named CSV/evidence ZIP.

Supply every form, issue and format preference explicitly:
    python examples/selective_form_exports.py --workspace ./form-workspace \
        --form FORM_CODE --issue YYYY-MM-DD --format PREFERRED_FORMAT \
        --output exports/forms.zip

Repeat --form and --issue to request their exact Cartesian membership. Repeat
--format in preference order. Each selected DBF contributes both CSV bytes and
full preservation evidence. This finite physical export claims no financial
interpretation of an unreviewed form. The host owns scheduling and recovery.
"""
from __future__ import annotations

from argparse import ArgumentParser
from contextlib import ExitStack
from datetime import date
import json
from pathlib import Path, PurePosixPath
import re
from urllib.parse import urlsplit

from stratbox.capabilities.model.targets import FeedTarget
from stratbox.core.execution.effect_state import FileEffectState
from stratbox.core.observability.journal import FileJournal
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.sdk import StrategyBox
from stratbox.shared.data.archives import ArchiveMemberSelection
from stratbox.shared.data.dbf import DBFPreservationPolicy
from stratbox.shared.data.selection import IssueQuery


FEED = 'cbr.reporting_forms.publications'


def _form_asset(value):
    token = str(value).removeprefix('form-')
    if re.fullmatch(r'[0-9]{3}', token):
        token = '0409' + token
    if not re.fullmatch(r'0409[0-9]{3}', token):
        raise ValueError('A form must be a three-digit code or an exact form-0409xxx asset ID.')
    return 'form-' + token


def _checked(result, capability):
    if result.outcome != 'succeeded':
        raise RuntimeError(f'{capability}: {result.outcome}: {result.diagnostics}')
    return result


def export_forms_once(box, forms, issues, *, formats, policy, store, output,
                      members=None, replace_existing=False, max_exports=500,
                      max_archive_bytes=8 * 1024**3):
    """Observe one feed, freeze exact selection, then export and deliver it.

    Caller-supplied policy can include exact source/issue/asset/member encoding
    overrides. Optional member names apply to each selected archive; omitted
    names select its DBF members. Every requested form/issue must be observed.
    """
    if not isinstance(policy, DBFPreservationPolicy):
        raise TypeError('Supply an explicit DBFPreservationPolicy.')
    asset_ids = tuple(_form_asset(value) for value in forms)
    issues = tuple(date.fromisoformat(value).isoformat() for value in issues)
    formats = tuple(formats)
    if not asset_ids or not issues or not formats:
        raise ValueError('Forms, exact issues and ordered format preferences are required.')
    if any(fmt not in {'zip', 'rar', 'dbf'} for fmt in formats):
        raise ValueError('This physical form export accepts ZIP, RAR or DBF representations.')
    if type(max_exports) is not int or not 1 <= max_exports <= 5000:
        raise ValueError('max_exports must be between one and 5000.')
    query = IssueQuery(mode='exact', issues=issues, asset_ids=asset_ids,
                       formats=formats, coverage_intent='selected')
    selection_rule = ArchiveMemberSelection(names=tuple(members) if members is not None else None,
                                           suffixes=('.dbf',), allow_empty=False)
    with box.invoke('operation.source.check', target=FeedTarget(FEED), inputs={'query': query}) as observed:
        _checked(observed, 'operation.source.check')
        selection, report = observed.output('selection'), observed.output('report')
        if not selection.assessment.complete or report.missing or report.ambiguous:
            raise RuntimeError('The observed feed does not establish the complete requested form/issue selection.')
    by_member = {(asset.asset_id, asset.issue_id): asset for asset in selection.entries}
    ordered = tuple(by_member[(form, issue)] for form in asset_ids for issue in issues)
    archive_members, exports = [], []
    for asset in ordered:
        with ExitStack() as owned:
            received = owned.enter_context(box.invoke('operation.material.receive', target=FeedTarget(FEED),
                inputs={'locator': asset, 'destination': 'originals'}))
            _checked(received, 'operation.material.receive')
            if not received.output('assessment').complete:
                raise RuntimeError(f'{asset.asset_id}/{asset.issue_id}: source admission is incomplete.')
            material, inspection = received.output('material'), received.output('inspection')
            if inspection.format in {'zip', 'rar'}:
                unpacked = owned.enter_context(box.invoke('command.archive.unpack',
                    inputs={'material': material, 'selection': selection_rule}, parameters={'placement': 'staged'}))
                _checked(unpacked, 'command.archive.unpack')
                dbfs = unpacked.output('members')
            elif inspection.format == 'dbf':
                filename = PurePosixPath(urlsplit(asset.locator).path).name
                if members is not None and tuple(members) != (filename,):
                    raise ValueError('A direct DBF asset must match the exact requested member name.')
                dbfs = (material,)
            else:
                raise RuntimeError(f'{asset.asset_id}/{asset.issue_id}: no admitted DBF or archive envelope.')
            if len(exports) + len(dbfs) > max_exports:
                raise RuntimeError('The selected DBF count exceeds this finite export limit.')
            for dbf in dbfs:
                name = dbf.metadata.get('member') or dbf.metadata.get('filename')
                if not isinstance(name, str) or not name:
                    raise RuntimeError('The admitted DBF has no exact physical member name.')
                with box.invoke('operation.dbf.export_csv', inputs={
                        'material': dbf, 'policy': policy, 'destination': 'representations'},
                        parameters={'placement': 'staged'}) as exported:
                    _checked(exported, 'operation.dbf.export_csv')
                    csv_ref, evidence_ref = exported.output('csv_reference'), exported.output('evidence_reference')
                    receipts = exported.output('receipts')
                    if (len(receipts) != 2 or any(receipt.status != 'confirmed' for receipt in receipts)
                            or {receipt.effect_id for receipt in receipts} != {csv_ref.effect_id, evidence_ref.effect_id}
                            or not exported.output('physical_assessment').complete):
                        raise RuntimeError('CSV and full preservation evidence must both have confirmed retention.')
                    prefix = f'{asset.asset_id}/{asset.issue_id}/{name}'
                    archive_members.extend(({'name': prefix + '.csv', 'material': csv_ref},
                        {'name': prefix + '.preservation.json', 'material': evidence_ref}))
                    exports.append({'asset_id': asset.asset_id, 'issue_id': asset.issue_id, 'member': name,
                        'csv_sha256': csv_ref.identity.sha256, 'evidence_sha256': evidence_ref.identity.sha256,
                        'receipt_ids': [receipt.effect_id for receipt in receipts],
                        'summary': dict(exported.output('summary'))})
    inputs = {'members': tuple(archive_members), 'destination': 'archives', 'named_destination': output}
    parameters = {'placement': 'staged', 'compression': 'deflated', 'max_bytes': max_archive_bytes,
                  'max_members': 2 * max_exports, 'policy': 'create_only'}
    if replace_existing:
        try:
            previous = store.inspect_file(output)
        except FileNotFoundError:
            previous = None
        if previous is not None:
            inputs['expected_destination'] = previous.identity
            parameters['policy'] = 'replace_if_matches'
    with box.invoke('operation.archive.publish', inputs=inputs, parameters=parameters) as published:
        _checked(published, 'operation.archive.publish')
        reference, delivery = published.output('reference'), published.output('delivery_receipt')
        if delivery.status != 'confirmed' or not published.output('assessment').complete:
            raise RuntimeError('The requested archive delivery is incomplete.')
        return {'query_identity': query.identity, 'selection_basis_identity': report.basis_identity,
            'selected_forms': list(asset_ids), 'selected_issues': list(issues), 'exports': exports,
            'archive_members': [entry['name'] for entry in published.output('manifest')],
            'archive_sha256': reference.identity.sha256, 'archive_location': reference.location,
            'output': output, 'delivery_status': delivery.status, 'delivery_effect_id': delivery.effect_id}


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--form', action='append', required=True)
    parser.add_argument('--issue', action='append', required=True, help='Exact ISO publication issue date; repeat as needed.')
    parser.add_argument('--format', action='append', choices=('zip', 'rar', 'dbf'), required=True,
                        help='Allowed representation; repeat in preference order.')
    parser.add_argument('--member', action='append', help='Exact DBF member required in each selected archive.')
    parser.add_argument('--encoding', default='cp866', help='Caller-selected strict DBF encoding (default: cp866).')
    parser.add_argument('--output', required=True, help='Named ZIP path relative to the workspace material store.')
    parser.add_argument('--replace', action='store_true', help='Replace only the exact destination observed by this pass.')
    parser.add_argument('--max-exports', type=int, default=500)
    parser.add_argument('--max-archive-bytes', type=int, default=8 * 1024**3)
    args = parser.parse_args()
    root = args.workspace.resolve()
    store = LocalFileStore(root / 'materials')
    policy = DBFPreservationPolicy(encoding=args.encoding, encoding_basis='caller', include_deleted=True)
    with FileJournal(root / 'journal') as journal:
        with StrategyBox(journal=journal, providers={
                'filestore': store, 'effect_state': FileEffectState(root / 'effects')}) as box:
            result = export_forms_once(box, args.form, args.issue, formats=args.format, policy=policy,
                store=store, output=args.output, members=args.member, replace_existing=args.replace,
                max_exports=args.max_exports, max_archive_bytes=args.max_archive_bytes)
            print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
