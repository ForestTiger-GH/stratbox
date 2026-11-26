"""Interpret an explicitly supplied source file through a standard scenario.

Usage: python examples/source_route.py fns.sme release.json --issue 2026-11-10
Add --parameters '{"format":"xlsx"}' only when the source format is ambiguous.
"""
from argparse import ArgumentParser
import json
from pathlib import Path
from stratbox.sdk import StrategyBox
from stratbox.shared.data.values import Material

MEDIA = {'.json':'application/json', '.csv':'text/csv', '.xlsx':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
         '.xls':'application/vnd.ms-excel', '.pdf':'application/pdf', '.docx':'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
         '.zip':'application/zip', '.rar':'application/vnd.rar'}


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('series')
    parser.add_argument('file', type=Path)
    parser.add_argument('--issue', required=True)
    parser.add_argument('--parameters', default='{}')
    args = parser.parse_args()
    original = Material(args.file.read_bytes(), MEDIA.get(args.file.suffix.lower(), 'application/octet-stream'),
                        args.series, metadata={'issue_id': args.issue})
    with StrategyBox() as box:
        result = box.invoke('scenario.series.refresh', target=args.series,
            inputs={'material': original, 'issue': args.issue}, parameters=json.loads(args.parameters))
        print(result.outcome, result.diagnostics)
        if result.outcome != 'succeeded': return 1
        value = result.output('dataset')
        print(value.source_id, value.issue_id, len(value.rows), value.identity)
        result.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
