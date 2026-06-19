"""Runtime assembly for Strategy Box app.

This module is the canonical place where the desktop surface wires runtime,
platform and application services together. The UI is scenario-first: operations
remain atomic internal steps, while ScenarioRunCase is the user-visible working unit.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.application.artifacts.store import ArtifactStore
from app.application.assignments.store import AssignmentStore
from app.application.background.registry import build_background_registry
from app.application.background.store import BackgroundProcessStore
from app.application.cases.store import ScenarioCaseStore
from app.application.events.store import OperationalEventStore
from app.application.logs.store import LogStore
from app.application.history.persistence import HistoryPersistenceService
from app.application.operations.catalog.models import OperationRegistry
from app.application.operations.catalog.registry import build_operation_registry
from app.application.presence.service import PresenceService
from app.application.scenarios.models import ScenarioRegistry
from app.application.scenarios.registry import build_scenario_registry
from app.platform.appdock.bridge import AppDockBridge
from app.platform.appdock.surface_state import AppSurfaceStateService
from app.platform.desktop.services import PlatformServices
from app.runtime.context import AppContext
from app.runtime.user_preferences import PreferencesService


@dataclass(slots=True)
class AppRuntime:
    context: AppContext
    operation_registry: OperationRegistry
    scenario_registry: ScenarioRegistry
    case_store: ScenarioCaseStore
    event_store: OperationalEventStore
    artifact_store: ArtifactStore
    log_store: LogStore
    background_store: BackgroundProcessStore
    assignment_store: AssignmentStore
    history_persistence: HistoryPersistenceService
    presence_service: PresenceService
    preferences: PreferencesService
    surface_state: AppSurfaceStateService
    platform: PlatformServices
    appdock_bridge: AppDockBridge
    scenario_coordinator: Any


def _build_application_services(context: AppContext) -> tuple[
    OperationRegistry,
    ScenarioRegistry,
    ScenarioCaseStore,
    OperationalEventStore,
    ArtifactStore,
    LogStore,
    BackgroundProcessStore,
    AssignmentStore,
    PresenceService,
    PreferencesService,
]:
    operation_registry = build_operation_registry(context)
    scenario_registry = build_scenario_registry(operation_registry)
    case_store = ScenarioCaseStore()
    event_store = OperationalEventStore()
    artifact_store = ArtifactStore()
    log_store = LogStore()
    background_store = BackgroundProcessStore(build_background_registry())
    assignment_store = AssignmentStore()
    presence_service = PresenceService(context)
    preferences = PreferencesService(context)
    return (
        operation_registry,
        scenario_registry,
        case_store,
        event_store,
        artifact_store,
        log_store,
        background_store,
        assignment_store,
        presence_service,
        preferences,
    )


def _build_platform_services(context: AppContext) -> tuple[AppSurfaceStateService, PlatformServices, AppDockBridge]:
    surface_state = AppSurfaceStateService(context)
    platform = PlatformServices()
    bridge = AppDockBridge(context)
    return surface_state, platform, bridge


def build_runtime(context: AppContext) -> AppRuntime:
    (
        operation_registry,
        scenario_registry,
        case_store,
        event_store,
        artifact_store,
        log_store,
        background_store,
        assignment_store,
        presence_service,
        preferences,
    ) = _build_application_services(context)
    history_persistence = HistoryPersistenceService(context.paths.runtime_dir)
    history_persistence.load_into(
        case_store=case_store,
        event_store=event_store,
        artifact_store=artifact_store,
        log_store=log_store,
        assignment_store=assignment_store,
    )
    surface_state, platform, bridge = _build_platform_services(context)
    from app.presentation.desktop.scenario_coordinator import ScenarioCoordinator

    scenario_coordinator = ScenarioCoordinator(
        context=context,
        operation_registry=operation_registry,
        case_store=case_store,
        event_store=event_store,
        artifact_store=artifact_store,
        log_store=log_store,
    )
    return AppRuntime(
        context=context,
        operation_registry=operation_registry,
        scenario_registry=scenario_registry,
        case_store=case_store,
        event_store=event_store,
        artifact_store=artifact_store,
        log_store=log_store,
        background_store=background_store,
        assignment_store=assignment_store,
        history_persistence=history_persistence,
        presence_service=presence_service,
        preferences=preferences,
        surface_state=surface_state,
        platform=platform,
        appdock_bridge=bridge,
        scenario_coordinator=scenario_coordinator,
    )
