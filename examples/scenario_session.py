"""Read local originals with a portable bounded workflow.

Usage: PYTHONPATH=src python examples/scenario_session.py DIRECTORY FILE [FILE ...]
"""
from __future__ import annotations

import argparse

from stratbox.sdk import (
    ExecutionSettings, InputRef, MapStep, OperationStep, PlanOutputRef,
    ScenarioDefinition, StrategyBox,
)
from stratbox.composition import ExecutionPlan
from stratbox.core.storage.filestore import LocalFileStore


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory")
    parser.add_argument("files", nargs="+")
    args = parser.parse_args()
    read = ScenarioDefinition("read", (
        OperationStep("original", "material.read_location",
                      parameters={"locator": InputRef("locator")}),
    ), inputs={"locator": None}, outputs={"source": PlanOutputRef("original", "source")})
    workflow = ScenarioDefinition("originals", (
        MapStep("files", read, tuple(args.files), item_input="locator", window=2),
    ), outputs={"sources": PlanOutputRef("files", "source")})
    with StrategyBox(settings=ExecutionSettings(max_workers=2),
                     providers={"filestore": LocalFileStore(args.directory)}) as box:
        plan = ExecutionPlan.from_dict(box.compile(workflow).to_dict())
        result = box.submit(plan).result()
        print(result.outcome)
        if result.outcome != "succeeded":
            for task in result.tasks:
                if task.reason:
                    print(task.task_id, task.state, task.reason)
            return 1
        for key, output in result.outputs["sources"].items:
            print(key, output.value.identity.sha256, output.value.identity.size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
