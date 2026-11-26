"""Execute the standard SORS route from explicit local source files or a retained value.

The JSON input map contains the role names declared by cbr.sors, each mapped to a
local workbook path. Originals are interpreted by their own SeriesTarget before
all ten required datasets enter the coupled calculation.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from stratbox.sdk import StrategyBox
from stratbox.capabilities.model.targets import SeriesTarget, CalculationTarget, ProductTarget
from stratbox.shared.data.values import Material
from stratbox.domains.cbr.calculations.sors.catalog import SORS
from stratbox.domains.cbr.calculations.sors.results import SorsRestorationResult
from stratbox.domains.cbr.calculations.sors.contracts import (
    SorsRunConfig, SorsOptimizationConfig, SorsCrosswalkConfig,
)


def value(result, port):
    if result.outcome != 'succeeded':
        raise RuntimeError(f'{result.outcome}: {result.diagnostics}')
    return result.output(port)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--input-map', type=Path, help='JSON object: SORS input role -> local workbook')
    source.add_argument('--resume-input', type=Path, help='Retained SORS source bundle or strict result')
    parser.add_argument('--as-of', required=True, help='One common reporting date, YYYY-MM-DD')
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--optimization', choices=('none', 'priority'), default='none')
    parser.add_argument('--max-targets', type=int, default=250)
    parser.add_argument('--crosswalk', action='store_true', help='Add explicitly conditional crosswalk evidence')
    args = parser.parse_args()
    with StrategyBox() as box:
        target = CalculationTarget('cbr.sors')
        if args.resume_input:
            datasets = value(box.invoke('command.value.decode',
                inputs={'representation': args.resume_input.read_bytes()}, target=target), 'value')
            retained = getattr(datasets, 'native', None) or datasets
            if isinstance(retained, SorsRestorationResult):
                datasets = retained.source_bundle
        else:
            paths = json.loads(args.input_map.read_text())
            if set(paths) - SORS.inputs.keys():
                raise ValueError('Unknown source roles in input map')
            datasets = {}
            for role, declaration in SORS.inputs.items():
                location = paths.get(role)
                if location is None:
                    if declaration['required']:
                        raise ValueError('Missing required source role: ' + role)
                    continue
                path = Path(location)
                material = Material(path.read_bytes(),
                    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    declaration['source_id'], metadata={'name': path.name, 'issue_id': args.as_of})
                datasets[role] = value(box.invoke('operation.series.extract_workbook',
                    inputs={'material': material}, parameters={'source_name': path.name},
                    target=SeriesTarget(declaration['source_id'])), 'dataset')
        config = SorsRunConfig(args.as_of, optimization=SorsOptimizationConfig(
            mode=args.optimization, max_targets=args.max_targets))
        dataset = value(box.invoke('operation.constraints.restore', inputs={'datasets': datasets},
            parameters={'config': config}, target=target), 'dataset')
        args.output_dir.mkdir(parents=True, exist_ok=True)
        encoded = value(box.invoke('command.value.encode', inputs={'value': dataset}, target=target), 'representation')
        (args.output_dir / 'sors-strict.json').write_bytes(encoded.data)
        if args.crosswalk:
            dataset = value(box.invoke('operation.constraints.restore', inputs={'datasets': dataset},
                parameters={'config': SorsCrosswalkConfig(mode='feasibility')},
                target=CalculationTarget('cbr.sors.crosswalk')), 'dataset')
        product = ProductTarget('cbr.sors.workbook')
        view = value(box.invoke('command.view.prepare', inputs={'dataset': dataset}, target=product), 'view')
        encoded_view = value(box.invoke('command.value.encode', inputs={'value': view}, target=product), 'representation')
        (args.output_dir / 'sors-view.json').write_bytes(encoded_view.data)
        workbook = value(box.invoke('command.product.render', inputs={'view': view}, target=product), 'product')
        (args.output_dir / 'sors.xlsx').write_bytes(workbook.data)


if __name__ == '__main__':
    main()
