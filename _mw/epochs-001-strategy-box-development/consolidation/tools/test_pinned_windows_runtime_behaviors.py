#!/usr/bin/env python3
"""Executed pinned Windows source characterization with synthetic inputs, NOT Qt/host testing.

CI checks out ForestTiger-GH/stratbox-windows at the exact pinned SHA and
loads its original Python modules. No desktop UI, distributed host or AppDock
session is started. These tests characterize known source risks rather than
assert requirements for a future release.
"""
from __future__ import annotations

import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase, main
from unittest.mock import patch

from stratbox_windows.application.operations.catalog.models import OperationRegistry, OperationSpec
from stratbox_windows.application.operations.execution.requests import OperationResult
from stratbox_windows.application.scenarios.models import ScenarioSpec, ScenarioStepSpec
from stratbox_windows.application.scenarios import runner
from stratbox_windows.application.operations.execution import runner as operation_runner


class WindowsObservedSourceCases(TestCase):
    def perform(self, *, error_policy="continue_with_warnings", first_required=True,
                first_result=None, second_result=None, raise_first=False):
        operations = OperationRegistry(items=(
            OperationSpec(id="synthetic.first", title="Synthetic first",
                          description="offline fake", handler="synthetic:first"),
            OperationSpec(id="synthetic.second", title="Synthetic second",
                          description="offline fake", handler="synthetic:second"),
        ))
        scenario = ScenarioSpec(
            id="synthetic.composite", title="Synthetic case", description="offline characterization",
            kind="composite", group="Tests", error_policy=error_policy,
            steps=(
                ScenarioStepSpec(id="one", operation_id="synthetic.first", title="first",
                                 order=1, required=first_required),
                ScenarioStepSpec(id="two", operation_id="synthetic.second", title="second", order=2),
            ),
        )
        context = SimpleNamespace(user_id="synthetic_user", account_name="Synthetic actor")
        params = {"synthetic_password": "SENTINEL_PRIVATE_VALUE"}
        case = runner.build_case_for_scenario(scenario=scenario, context=context, params=params)
        events, artifacts, logs, updates, calls = [], [], [], [], []

        def fake_operation(spec, **_):
            calls.append(spec.id)
            if raise_first and spec.id == "synthetic.first":
                raise RuntimeError("synthetic failure before normal operation return")
            if spec.id == "synthetic.first":
                return first_result or OperationResult(ok=False, message="synthetic step failure")
            return second_result or OperationResult(ok=True, message="synthetic success")

        with patch.object(runner, "run_operation", side_effect=fake_operation):
            try:
                result = runner.run_scenario(
                    scenario=scenario, operation_registry=operations, context=context,
                    params=params, case=case, on_case_updated=updates.append,
                    on_event=events.append, on_artifacts=artifacts.extend,
                    on_log=logs.append,
                )
                raised = None
            except RuntimeError as exc:
                result, raised = case, exc
        return result, events, artifacts, logs, updates, calls, raised

    def test_continue_with_warnings_reports_case_success_after_failed_required_step(self):
        case, events, _, _, _, calls, raised = self.perform()
        self.assertIsNone(raised)
        self.assertEqual(calls, ["synthetic.first", "synthetic.second"])
        self.assertEqual([s.status for s in case.steps], ["failed", "success"])
        self.assertEqual(case.status, "success")
        self.assertEqual(events[-1].kind, "case_completed")
        self.assertEqual(events[-1].status, "success")

    def test_required_false_does_not_override_fail_fast_policy(self):
        case, events, _, _, _, calls, raised = self.perform(
            error_policy="fail_fast", first_required=False)
        self.assertIsNone(raised)
        self.assertEqual(calls, ["synthetic.first"])
        self.assertEqual(case.status, "failed")
        self.assertEqual(case.steps[1].status, "pending")
        self.assertEqual(events[-1].kind, "case_failed")

    def test_start_event_contains_unredacted_synthetic_parameter_value(self):
        case, events, _, _, _, _, raised = self.perform()
        self.assertIsNone(raised)
        self.assertEqual(events[0].kind, "case_started")
        self.assertIn("SENTINEL_PRIVATE_VALUE", events[0].body)
        self.assertEqual(case.params["synthetic_password"], "SENTINEL_PRIVATE_VALUE")

    def test_failed_operation_log_output_is_promoted_to_artifact(self):
        with TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "synthetic_failure.log")
            case, events, artifacts, _, _, _, raised = self.perform(
                error_policy="fail_fast",
                first_result=OperationResult(
                    ok=False, message="offline error", outputs=(path,),
                    details={"operation_log": path},
                ))
            self.assertIsNone(raised)
            self.assertEqual(case.status, "failed")
            self.assertEqual(len(artifacts), 1)
            self.assertEqual(artifacts[0].kind, "log")
            self.assertEqual(artifacts[0].path, path)
            self.assertIn(artifacts[0].artifact_id,
                          next(e for e in events if e.kind == "step_failed").artifact_ids)

    def test_exception_before_operation_result_leaves_direct_runner_unfinalized(self):
        case, events, _, _, _, calls, raised = self.perform(raise_first=True)
        self.assertIsNotNone(raised)
        self.assertEqual(calls, ["synthetic.first"])
        self.assertEqual(case.status, "running")
        self.assertIsNone(case.finished_at)
        self.assertFalse(any(e.kind in {"case_failed", "case_completed"} for e in events))
        # The separate Qt ScenarioWorker has a catch boundary; this test is
        # specifically about direct run_scenario's absent final event/finalization.

    def test_workspace_missing_branch_leaves_operation_file_handler_attached(self):
        with TemporaryDirectory() as tmp:
            logs_dir = Path(tmp) / "operation_logs"
            spec = OperationSpec(id="synthetic.workspace_missing_case",
                                 title="Missing workspace", description="offline test",
                                 handler="synthetic:not_loaded", requires_workspace=True)
            workspace_status = SimpleNamespace(available=False, to_dict=lambda: {"available": False})
            context = SimpleNamespace(
                paths=SimpleNamespace(operation_logs_dir=logs_dir),
                workspace_root_path=None, filestore=None,
                workspace_status=workspace_status,
                logger=logging.getLogger("synthetic_window_source_characterization"),
            )
            with patch.object(operation_runner, "_build_operation_context",
                              return_value=SimpleNamespace()):
                result = operation_runner.run_operation(spec, context=context)
            self.assertFalse(result.ok)
            self.assertIn("operation_log", result.details)
            internal_logger = logging.getLogger(
                "app.operation.manual.step.synthetic_workspace_missing_case"
            )
            # Early return precedes the normal try/finally close/remove branch.
            self.assertTrue(any(isinstance(h, logging.FileHandler)
                                for h in internal_logger.handlers))
            for h in list(internal_logger.handlers):
                h.close()
                internal_logger.removeHandler(h)


class WindowsConfigAndProvenanceCases(TestCase):
    def test_missing_git_repository_reports_unknown_not_installed_revision(self):
        from stratbox_windows.runtime.version import get_version_info
        with TemporaryDirectory() as tmp:
            version = get_version_info(Path(tmp))
        self.assertEqual(version.commit, "unknown")
        self.assertEqual(version.branch, "unknown")
        self.assertEqual(version.last_commit_time, "unknown")
        self.assertFalse(version.dirty)

    def test_saved_form_values_roundtrip_as_unredacted_local_json(self):
        from stratbox_windows.runtime.config import (
            AppUserConfig, load_user_config, save_user_config
        )
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "app.json"
            conf = AppUserConfig()
            conf.scenario_form_values = {
                "scenario.synthetic": {"synthetic_password": "SENTINEL_PRIVATE_VALUE"}
            }
            save_user_config(path, conf)
            self.assertIn("SENTINEL_PRIVATE_VALUE", path.read_text(encoding="utf-8"))
            loaded = load_user_config(path)
        self.assertEqual(
            loaded.scenario_form_values["scenario.synthetic"]["synthetic_password"],
            "SENTINEL_PRIVATE_VALUE",
        )

    def test_malformed_saved_window_width_raises_unwrapped_value_error(self):
        import json
        from stratbox_windows.runtime.config import load_user_config
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "app.json"
            path.write_text(json.dumps({"window": {"width": "bad-int"}}), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_user_config(path)



if __name__ == "__main__":
    main(verbosity=2)
