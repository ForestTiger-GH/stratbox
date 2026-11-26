"""Preview explicitly requested file actions, then apply the exact reviewed plan.

Actions JSON is a list of source, operation(move/delete), optional destination,
expected_sha256 and expected_size. No older report is selected for deletion
automatically. --apply-digest is an explicit request to mutate the selected scope.
"""
import argparse
import json
from pathlib import Path

from stratbox.core.storage.filestore import LocalFileStore
from stratbox.sdk import StrategyBox
from stratbox.shared.data.values import canonical_tree, fingerprint
from stratbox.shared.identity import ByteIdentity


def required(result, output):
    if result.outcome != "succeeded":
        raise RuntimeError(result.diagnostics)
    return result.output(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--actions", type=Path, required=True)
    parser.add_argument("--apply-digest")
    args = parser.parse_args()
    root = args.directory.resolve()
    actions = []
    for item in json.loads(args.actions.read_text(encoding="utf-8")):
        action = dict(item)
        action["expected_identity"] = ByteIdentity(action.pop("expected_sha256"), action.pop("expected_size"))
        for key in ("source", "destination"):
            if action.get(key) is not None and not (root / action[key]).resolve().is_relative_to(root):
                raise ValueError("Requested action escapes its explicit directory")
        actions.append(action)
    with StrategyBox(providers={"filestore": LocalFileStore(root=str(root))}) as box:
        inventory = required(box.invoke("command.material.list", inputs={"location": "."}), "inventory")
        plan = required(box.invoke("command.material.maintenance_plan", inputs={"inventory": inventory},
            parameters={"actions": tuple(actions), "scope": "."}), "plan")
        digest = fingerprint((str(root), plan))
        print(json.dumps({"digest": digest, "plan": canonical_tree(plan)}, ensure_ascii=False))
        if args.apply_digest is not None:
            if args.apply_digest != digest:
                raise ValueError("The reviewed plan digest does not match")
            applied = box.invoke("command.material.maintenance_apply", inputs={"plan": plan},
                parameters={"scope": "."})
            print(applied.outcome, applied.effects)
            if applied.outcome != "succeeded":
                raise RuntimeError(applied.diagnostics)


if __name__ == "__main__":
    main()
