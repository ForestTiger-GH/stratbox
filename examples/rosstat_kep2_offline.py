"""Process a supplied KEP2 workbook through standard commands and retain values.

Run with --source /path/2026-08.xlsx --issue 2026-08 --output-root /path/output.
The publication issue is explicit; economic periods come from worksheet evidence.
"""
from argparse import ArgumentParser
from pathlib import Path

from stratbox.capabilities.model.targets import ProductTarget, SeriesTarget
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.sdk import StrategyBox
from stratbox.shared.data.values import Material


def required(result, output):
    if result.outcome != "succeeded":
        raise RuntimeError(result.diagnostics)
    return result.output(output)


def build(source: Path, issue: str, output_root: Path):
    output_root.mkdir(parents=True, exist_ok=True)
    source_id = "rosstat.short_term_indicators"
    original = Material(source.read_bytes(),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", source_id,
        metadata={"issue_id": issue, "asset_id": "main_workbook", "format": "xlsx"})
    with StrategyBox(providers={"filestore": LocalFileStore(str(output_root))}) as box:
        def commit(material, destination):
            return required(box.invoke("command.artifact.commit",
                inputs={"material": material, "destination": destination}), "reference")

        def retained(value, destination):
            encoded = required(box.invoke("command.value.encode", inputs={"value": value}), "representation")
            reference = commit(encoded, destination)
            read = required(box.invoke("command.material.read", inputs={"location": reference}), "material")
            return required(box.invoke("command.value.decode", inputs={"representation": read}), "value")

        commit(original, "originals")
        physical = required(box.invoke("command.workbook.decode", inputs={"material": original}), "physical")
        physical = retained(physical, "physical")
        dataset = required(box.invoke("operation.series.extract_workbook", inputs={"physical": physical},
            target=SeriesTarget(source_id)), "dataset")
        dataset = retained(dataset, "observations")
        product_target = ProductTarget("rosstat.kep2.monthly.xlsx")
        view = required(box.invoke("command.view.prepare", inputs={"dataset": dataset},
            target=product_target), "view")
        view = retained(view, "views")
        product = required(box.invoke("command.product.render", inputs={"view": view},
            target=product_target), "product")
        reference = commit(product, "products")
        return {"source_sha256": original.identity.sha256, "physical_sheets": len(physical.workbook.sheets),
            "selected_values": len(dataset.rows), "monthly_values": len(view.value.rows), "artifact": reference.location}


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--issue", required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    print(build(args.source, args.issue, args.output_root))


if __name__ == "__main__":
    main()
