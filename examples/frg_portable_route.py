"""Run an exact-material Frank route on an explicitly synthetic workbook.

This fixture supplies no evidence of an actual publisher layout.
Requires the excel extra; performs no network or filesystem effects.
"""
from io import BytesIO

from openpyxl import Workbook

from stratbox.capabilities.model.targets import SeriesTarget
from stratbox.domains.frank_rg.methods.tables import CellRule, TableRules
from stratbox.sdk import StrategyBox
from stratbox.shared.data.values import Material


def required(result, output):
    if result.outcome != "succeeded":
        raise RuntimeError(result.diagnostics)
    return result.output(output)


def main():
    source_id = "frg.express.portfolios"
    book = Workbook()
    sheet = book.active
    sheet.title = "Synthetic layout"
    sheet.append(("Subject", "Amount"))
    sheet.append(("Synthetic bank", "100.1234567890123456789012345"))
    stream = BytesIO()
    book.save(stream)
    book.close()
    material = Material(stream.getvalue(), source_id=source_id,
        metadata={"issue_id": "2026-05-01", "format": "xlsx"})
    rules = TableRules(source_id, (CellRule(
        "Synthetic layout", 2, 2, "synthetic.stock", "synthetic-bank", "RUB", "stock",
        "2026-04-30", "monthly", "synthetic_reporting_population", subject_namespace="bank"),
    ), original_identity=material.identity)
    target = SeriesTarget(source_id)

    with StrategyBox() as box:
        physical = required(box.invoke("command.workbook.decode", inputs={"material": material}), "physical")
        encoded = required(box.invoke("command.value.encode", inputs={"value": physical}), "representation")
        restored = required(box.invoke("command.value.decode", inputs={"representation": encoded}), "value")
        dataset = required(box.invoke("operation.series.extract_workbook",
            inputs={"physical": restored}, parameters={"table_rules": rules}, target=target), "dataset")
        encoded_dataset = required(box.invoke("command.value.encode", inputs={"value": dataset}), "representation")
        dataset = required(box.invoke("command.value.decode", inputs={"representation": encoded_dataset}), "value")
        view = required(box.invoke("command.view.prepare", inputs={"dataset": dataset}), "view")
        product = required(box.invoke("command.product.render",
            inputs={"view": view}, parameters={"format": "json"}), "product")
        assert dataset.rows[0]["raw_token"] == "100.1234567890123456789012345"
        print({"synthetic_observations": len(dataset.rows), "dataset_identity": dataset.identity,
            "physical_identity": physical.material.identity.sha256, "rendered_bytes": len(product.data)})


if __name__ == "__main__":
    main()
