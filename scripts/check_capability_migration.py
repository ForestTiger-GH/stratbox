"""Audit canonical route coverage separately from publisher-edition evidence."""
from __future__ import annotations

import argparse
from collections import Counter
from importlib import import_module
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
DOMAINS = ('cbr', 'fns', 'minfin', 'frank_rg', 'rosstat')


def audit():
    from stratbox.sdk.bootstrap import default_snapshot
    from stratbox.capabilities.operations.stages import dispositions as neutral_dispositions
    snapshot = default_snapshot()
    baseline = json.loads((ROOT / '_mw/epochs-001-strategy-box-development/refactoring/p00/baseline.json').read_text())
    dispositions = dict(neutral_dispositions())
    stages, domain_evidence = {}, {}
    for domain in DOMAINS:
        module = import_module('stratbox.domains.' + domain + '.capabilities')
        values = module.dispositions()
        if isinstance(values, dict):
            for identifier, entry in values.items():
                dispositions[identifier] = (entry['capability_id'],)
        else:
            for entry in values:
                original = entry.get('original_id', entry.get('operation_id', entry.get('source_id', entry['capability_id'])))
                dispositions[original] = (entry['capability_id'],)
        rows = module.stage_matrix()
        domain_evidence[domain] = rows
        for row in rows:
            if 'stage' in row:
                stages[row['source_id'], row['stage']] = row
            else:
                for stage, entry in row['stages'].items():
                    detail = {'capability_id': entry} if isinstance(entry, str) else dict(entry)
                    stages[row['source_id'], stage] = {**row, **detail, 'stage': stage}
    ids = {item.id for item in snapshot.definitions}
    errors, operation_rows, source_rows, profile_rows, template_rows = [], [], [], [], []
    for record in baseline['operations']:
        original = record['document']['definition']['operation_id']
        targets = dispositions.get(original, ())
        missing = tuple(item for item in targets if item not in ids)
        if not targets or missing:
            errors.append('operation:' + original)
        operation_rows.append({'original_id': original, 'capabilities': targets,
            'status': 'canonical' if targets and not missing else 'unresolved'})
    for record in baseline['source_stage_matrix']:
        source = record['source_id']
        group = next((item for item in snapshot.groups if source in item.source_ids), None)
        if group is None:
            errors.append('source:' + source)
        cells = []
        for old in record['stages']:
            stage = old['stage']
            item = stages.get((source, stage))
            targets = () if item is None else tuple(item.get('capabilities', ()))
            if item is not None and 'capability_id' in item:
                targets = (item['capability_id'],)
            valid = bool(targets) and all(identifier in ids for identifier in targets)
            if not valid:
                errors.append('stage:' + source + ':' + stage)
            cells.append({'stage': stage, 'capabilities': targets,
                'route_status': 'canonical' if valid else 'unresolved',
                'semantic_scope': item.get('scope', item.get('semantic_scope')) if item else None,
                'qualification': item.get('state', item.get('edition_verification')) if item else None})
        source_rows.append({'source_id': source, 'source_group_id': record['group_id'],
            'processing_group_id': group.group_id if group else None, 'stages': cells})
    profiles = {item.profile_id for item in snapshot.profiles}
    for record in baseline['profiles']:
        identifier = record['document']['profile_id']
        present = identifier in profiles
        if not present:
            errors.append('profile:' + identifier)
        profile_rows.append({'profile_id': identifier, 'status': 'canonical' if present else 'unresolved'})
    for record in baseline['templates']:
        document = record['document']
        slots = []
        for name, slot in document['slots'].items():
            targets = dispositions.get(slot['operation_id'], ())
            slots.append({'name': name, 'capabilities': targets})
            if not targets or any(item not in ids for item in targets):
                errors.append('template:' + document['template_id'] + ':' + name)
        template_rows.append({'template_id': document['template_id'], 'slots': slots,
            'disposition': 'typed capabilities and contributed source-goal recipes'})
    # Structural executability and publication-specific scientific evidence are
    # independent. A callable reviewed-profile method does not prove an unseen
    # publisher edition or replace a financial model for forms 134/803.
    evidence_obligations = (
        {'domain': 'cbr', 'scope': 'historical publisher layouts and financial models for forms 134/803',
         'status': 'publisher_and_model_review_pending',
         'implemented': 'physical evidence and explicitly reviewed numeric-field interpretation'},
        {'domain': 'frank_rg', 'scope': 'publisher semantic layouts for all fourteen licensed report series',
         'status': 'publisher_originals_required',
         'implemented': 'strict reusable reviewed layout profiles, source-qualified interpretation and all processing stages'},
        {'domain': 'minfin', 'scope': 'reviewed economic fields for the three NWF document source editions',
         'status': 'publisher_originals_required',
         'implemented': 'DOC conversion contract, ordered document evidence and reviewed field interpretation'},
        {'domain': 'rosstat', 'scope': 'publisher editions beyond explicitly pinned reviewed workbook/profile scope',
         'status': 'bounded_edition_scope',
         'implemented': 'KEP2 plus the specifically reviewed retained population and regional source layouts'},
    )
    return {'schema': 'stratbox.capability-migration.v1',
        'baseline_commit': baseline['base_commit'],
        'catalog_fingerprint': snapshot.fingerprint,
        'counts': {'capabilities': dict(Counter(item.kind for item in snapshot.definitions)),
            'original_operations': len(operation_rows), 'sources': len(source_rows),
            'stage_cells': sum(len(row['stages']) for row in source_rows),
            'original_profiles': len(profile_rows), 'original_templates': len(template_rows)},
        'structural_errors': sorted(set(errors)),
        'operations': operation_rows, 'sources': source_rows, 'profiles': profile_rows,
        'templates': template_rows, 'publisher_evidence_obligations': evidence_obligations,
        'status': 'routes_admitted_publisher_scope_qualified' if not errors else 'route_gaps',
        'full_plan_closure': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--require-publisher-evidence', action='store_true')
    options = parser.parse_args()
    result = audit()
    if options.output:
        options.output.parent.mkdir(parents=True, exist_ok=True)
        options.output.write_text(json.dumps(result, ensure_ascii=True, indent=2) + '\n')
    print(json.dumps({key: result[key] for key in ('status', 'counts', 'structural_errors', 'full_plan_closure')}, indent=2))
    return 1 if result['structural_errors'] or options.require_publisher_evidence and not result['full_plan_closure'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
