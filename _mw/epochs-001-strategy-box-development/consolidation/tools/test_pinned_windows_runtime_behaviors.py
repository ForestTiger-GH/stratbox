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



class ExplorerAndChatProjectionObservedCases(TestCase):
    def test_direct_explorer_absolute_external_navigation_is_rejected(self):
        from stratbox_windows.application.workspace.explorer_service import WorkspaceExplorerService
        with TemporaryDirectory() as tmp:
            parent = Path(tmp)
            root = parent / "workspace"
            outside = parent / "external"
            root.mkdir()
            outside.mkdir()
            service = WorkspaceExplorerService(
                mount_root_path=root, start_root_path=root, root_label="Workspace"
            )
            self.assertIsNone(service.location_for_path(outside))
            self.assertIsNone(service.location_for_path(Path("..") / "external"))

    def test_directory_symlink_entry_bypasses_location_guard_during_enter_and_list(self):
        from stratbox_windows.application.workspace.explorer_service import WorkspaceExplorerService
        from stratbox_windows.application.workspace.explorer_models import ExplorerSort
        with TemporaryDirectory() as tmp:
            parent = Path(tmp)
            root = parent / "workspace"
            outside = parent / "external"
            root.mkdir()
            outside.mkdir()
            (outside / "PRIVATE_SYNTHETIC_FILE.txt").write_text("test only", encoding="utf-8")
            try:
                (root / "linked_outside").symlink_to(outside, target_is_directory=True)
            except (NotImplementedError, OSError):
                self.skipTest("Platform cannot create directory symlink")
            service = WorkspaceExplorerService(
                mount_root_path=root, start_root_path=root, root_label="Workspace"
            )
            self.assertIsNone(service.location_for_path(root / "linked_outside"))
            start = service.initial_location()
            self.assertIsNotNone(start)
            listing = service.list_location(start, ExplorerSort())
            alias = next(x for x in listing.entries if x.name == "linked_outside")
            self.assertTrue(alias.is_navigable)
            entered = service.enter_entry(start, alias)
            self.assertIsNotNone(entered)
            names = {x.name for x in service.list_location(entered, ExplorerSort()).entries}
            self.assertIn("PRIVATE_SYNTHETIC_FILE.txt", names)

    def test_chat_case_projection_exposes_synthetic_parameter_and_raw_local_artifact_path(self):
        from stratbox_windows.application.artifacts.store import ArtifactStore
        from stratbox_windows.application.artifacts.models import ArtifactRecord
        from stratbox_windows.application.cases.models import ScenarioRunCase, ScenarioStepRun
        from stratbox_windows.presentation.common.scenario_chat.projector import project_case
        with TemporaryDirectory() as tmp:
            case = ScenarioRunCase.create(
                scenario_id="scenario.synthetic", scenario_title="Synthetic",
                params={"synthetic_password": "SENTINEL_PRIVATE_VALUE"},
                author_id="synthetic_author", author_label="Synthetic user",
                steps=[ScenarioStepRun(step_id="s", operation_id="fake", title="Fake")],
            )
            store = ArtifactStore()
            path = str(Path(tmp) / "PRIVATE_SYNTHETIC_OUTPUT.xlsx")
            store.add(ArtifactRecord.from_path(
                path, scenario_id="scenario.synthetic", case_id=case.case_id,
                operation_id="fake", author_id="synthetic_author", author_label="Synthetic user",
            ))
            msg = project_case(case, store, current_user_id="another_synthetic_user")
            self.assertIn("SENTINEL_PRIVATE_VALUE", msg.params_summary)
            self.assertEqual(msg.artifacts[0].path, path)
            self.assertEqual(msg.placement, "incoming")

    def test_chat_case_projector_copies_aggregate_success_despite_failed_substep(self):
        from stratbox_windows.application.artifacts.store import ArtifactStore
        from stratbox_windows.application.cases.models import ScenarioRunCase, ScenarioStepRun
        from stratbox_windows.presentation.common.scenario_chat.projector import project_case
        case = ScenarioRunCase.create(
            scenario_id="scenario.synthetic", scenario_title="Synthetic",
            params={}, author_id="synthetic_author", author_label="Synthetic user",
            steps=[ScenarioStepRun(step_id="failed", operation_id="fake", title="Required", status="failed")],
        )
        case.status = "success"
        message = project_case(case, ArtifactStore(), current_user_id="synthetic_author")
        self.assertEqual(message.status, "success")
        self.assertEqual(message.steps[0].status, "failed")
        self.assertEqual(message.status_label, "Завершено")


    def test_non_drive_selector_is_current_workspace_not_nested_named_child(self):
        from stratbox_windows.application.workspace.models import WorkspaceSchema
        from stratbox_windows.application.workspace.resolver import resolve_workspace_root
        with TemporaryDirectory() as tmp:
            data_root = Path(tmp) / "selected_data"
            data_root.mkdir()
            schema = WorkspaceSchema(
                id="default", title="Default", required_dirs=("input", "output"),
                root_mode="derived_from_selector", workspace_dirname="Strategy Box Data"
            )
            answer = resolve_workspace_root(
                schema, data_root, run_mode="appdock_managed", create_missing=True
            )
            self.assertEqual(answer.resolution_mode, "explicit_workspace_root")
            self.assertEqual(answer.workspace_root_path, data_root)
            self.assertTrue((data_root / "input").is_dir())
            self.assertTrue((data_root / "output").is_dir())
            self.assertFalse((data_root / "Strategy Box Data").exists())


if __name__ == "__main__":
    main(verbosity=2)
