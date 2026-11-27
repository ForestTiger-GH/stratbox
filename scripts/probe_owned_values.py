"""Measure one public workbook extraction and concurrent short commands.

The fixture is the repository's synthetic 0105a debt workbook (15,720 physical
cells, 14,976 source rows). This is extraction, not the retained/replayed
multistage rendering test. Traversal counts instrument the three scientific
carrier types, not every scalar hash. Resident/working counters describe managed
ownership, not total process RSS. Latencies are samples from this run, not an SLO.

Use --repo to run the identical probe against another read-only source snapshot.
Both snapshots need the current interpreter's compatible test dependencies.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from threading import current_thread
from time import perf_counter, sleep

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1],
                    help='Source snapshot; defaults to this repository.')
parser.add_argument('--output', type=Path,
                    help='Optional JSON file; the report is always printed.')
parser.add_argument('--fixture', type=Path,
                    help='Reuse this exact XLSX fixture, creating it when absent.')
parser.add_argument('--samples', type=int, default=8,
                    help='Maximum concurrent short-command samples (0–64; default 8).')
args = parser.parse_args()
if not 0 <= args.samples <= 64:
    parser.error('--samples must be between 0 and 64')
args.repo = args.repo.resolve()
sys.path[:0] = [str(args.repo / 'src'), str(args.repo / 'tests/unit/macrobanks'),
               str(args.repo / 'tests/core_target')]

from test_cbr_industries_0105a_debt_corp import _workbook_bytes
from stratbox.capabilities.model import MethodRef, PortContract, ReuseContract
from stratbox.capabilities.model.targets import SeriesTarget
from stratbox.capabilities.plan.models import BoundCommand, CommandTask, PreparedPlan, ValueRef
from stratbox.sdk import StrategyBox
from stratbox.shared.data.values import Material, SourceDataset, WorkbookEvidence, TableEvidenceSet
from stratbox.core.execution.service import ExecutionService
import stratbox.shared.data.values as values
import stratbox.core.execution.owned_values as ownership

heavy = (SourceDataset, WorkbookEvidence, TableEvidenceSet)
counts = Counter()
timings = Counter()
try:
    import stratbox.shared.data.value_identity as identities
except ImportError:
    identities = None

def observe(label, original):
    def measured(value, *arguments, **options):
        tracked = isinstance(value, heavy)
        start = perf_counter() if tracked else None
        try:
            return original(value, *arguments, **options)
        finally:
            if tracked:
                key = (label, type(value).__name__, current_thread().name)
                counts[key] += 1
                timings[key] += perf_counter() - start
    return measured

if identities is not None:
    identities.exact_fingerprint = observe('identity', identities.exact_fingerprint)
else:
    values.canonical_tree = observe('identity', values.canonical_tree)
ownership._isolate = observe('copy', ownership._isolate)

content = (args.fixture.read_bytes() if args.fixture is not None and args.fixture.exists()
    else _workbook_bytes(report_date='01.02.2019', kemerovo_name='Кемеровская область'))
if args.fixture is not None and not args.fixture.exists():
    args.fixture.write_bytes(content)
source = 'cbr.corporate_lending.debt_0105a'
name = '01_05_A_Debt_corp_20190201.xlsx'
material = Material(content, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    source, metadata={'name': name})

def quick(inputs, settings, context):
    return {'value': inputs['value']}

# The module is importable by MethodRef in either implementation snapshot.
sys.modules['ownership_probe'] = sys.modules[__name__]
command = BoundCommand('command.test.independent', MethodRef('ownership_probe:quick'), {},
    {'value': PortContract('integer', int)}, {'value': PortContract('integer', int)},
    reuse=ReuseContract(shareable=False, completed=False))
small = PreparedPlan('probe', (CommandTask('short', command, {'value': 7}),), (),
    {'value': ValueRef('short')}, 'probe', 'probe')

with StrategyBox() as box:
    begin = perf_counter()
    plan = box.prepare('operation.series.extract_workbook', inputs={'material': material},
        parameters={'source_name': name}, target=SeriesTarget(source))
    prepared_seconds = perf_counter() - begin
    start = perf_counter()
    handle = box.session.submit(plan)
    admitted_seconds = perf_counter() - start
    latencies = []
    next_check = perf_counter()
    peak_resident = peak_working = 0
    while not handle.done():
        if perf_counter() >= next_check and len(latencies) < args.samples:
            clock = perf_counter()
            with box.session.run(small) as independent:
                assert independent.outcome == 'succeeded', independent.diagnostics
                assert independent.output() == 7
            latencies.append(perf_counter() - clock)
            next_check = perf_counter() + 1
        stats = box.session.value_statistics() if hasattr(box.session, 'value_statistics') else {}
        peak_resident = max(peak_resident, stats.get('resident_bytes', 0))
        peak_working = max(peak_working, stats.get('working_bytes', 0))
        sleep(.01)
    execution_seconds = perf_counter() - start
    result = handle.result()
    assert result.outcome == 'succeeded', result.diagnostics
    reader_start = perf_counter()
    dataset = result.output('dataset')
    reader_seconds = perf_counter() - reader_start
    statistics = box.session.value_statistics() if hasattr(box.session, 'value_statistics') else None
    frozen_counts = dict(counts)
    for _ in range(100):
        box.session.status(result.run_id)
        if statistics is not None:
            box.session.value_statistics()
    polling_identity_delta = sum(counts.values()) - sum(frozen_counts.values())
    report = dict(route='operation.series.extract_workbook', fixture='debt_0105a',
        fixture_bytes=len(content), physical_cells=15720, dataset_rows=len(dataset.rows),
        preparation_seconds=prepared_seconds, admission_seconds=admitted_seconds,
        execution_including_admission_seconds=execution_seconds, reader_copy_seconds=reader_seconds,
        independent_command_seconds=latencies,
        peak_observed_resident_bytes=peak_resident if statistics is not None else None,
        peak_observed_working_bytes=peak_working if statistics is not None else None,
        value_statistics=statistics,
        polling_payload_traversal_delta=polling_identity_delta,
        traversals=[dict(kind=kind, value_type=typ, thread=thread, count=count,
                         seconds=timings[(kind, typ, thread)])
                    for (kind, typ, thread), count in sorted(counts.items())])
    result.close()
if args.output is not None:
    args.output.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
