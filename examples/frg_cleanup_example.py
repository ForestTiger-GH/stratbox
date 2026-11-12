"""Preview an FRG directory plan and apply it when given the reviewed digest."""

import argparse

from stratbox.base.filestore import LocalFileStore
from stratbox.macrobanks import frg


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory")
    parser.add_argument("--delete-older", action="store_true")
    parser.add_argument("--apply-digest")
    args = parser.parse_args()
    store = LocalFileStore(root=args.directory)
    planned = frg.plan_cleanup(frg.PlanCleanupRequest(".", args.delete_older), store=store)
    if planned.outcome != "succeeded":
        raise SystemExit(tuple(item.code for item in planned.diagnostics))
    plan = planned.value
    print(plan.identity.sha256, plan.actions)
    if args.apply_digest:
        applied = frg.apply_cleanup(frg.ApplyCleanupRequest(plan, ".", args.apply_digest), store=store)
        print(applied.outcome, applied.value, applied.diagnostics)


if __name__ == "__main__":
    main()
