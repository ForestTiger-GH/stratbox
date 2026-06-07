"""Runtime assembly for Strategy Box app.

This module is the canonical place where the desktop product surface wires
runtime, platform and application services together.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from app.runtime.context import AppContext
from app.platform.appdock.bridge import AppDockBridge
from app.platform.appdock.surface_state import AppSurfaceStateService
from app.platform.desktop.services import PlatformServices
from app.application.presence.service import PresenceService
from app.application.product.catalog.registry import build_product_registry
from app.application.product.catalog.models import ProductRegistry
from app.runtime.user_preferences import PreferencesService
from app.application.timeline.store import FeedStore

if TYPE_CHECKING:
    from app.presentation.desktop.run_coordinator import RunCoordinator


@dataclass(slots=True)
class AppRuntime:
    context: AppContext
    product_registry: ProductRegistry
    feed_store: FeedStore
    presence_service: PresenceService
    preferences: PreferencesService
    surface_state: AppSurfaceStateService
    platform: PlatformServices
    appdock_bridge: AppDockBridge
    run_coordinator: Any


def _build_application_services(context: AppContext) -> tuple[ProductRegistry, FeedStore, PresenceService, PreferencesService]:
    registry = build_product_registry(context)
    feed_store = FeedStore()
    presence_service = PresenceService(context)
    preferences = PreferencesService(context)
    return registry, feed_store, presence_service, preferences


def _build_platform_services(context: AppContext) -> tuple[AppSurfaceStateService, PlatformServices, AppDockBridge]:
    surface_state = AppSurfaceStateService(context)
    platform = PlatformServices()
    bridge = AppDockBridge(context)
    return surface_state, platform, bridge


def _build_presentation_services(context: AppContext):
    from app.presentation.desktop.run_coordinator import RunCoordinator

    return RunCoordinator(context=context, on_log=context.logger.info)


def build_runtime(context: AppContext) -> AppRuntime:
    registry, feed_store, presence_service, preferences = _build_application_services(context)
    surface_state, platform, bridge = _build_platform_services(context)
    run_coordinator = _build_presentation_services(context)
    return AppRuntime(
        context=context,
        product_registry=registry,
        feed_store=feed_store,
        presence_service=presence_service,
        preferences=preferences,
        surface_state=surface_state,
        platform=platform,
        appdock_bridge=bridge,
        run_coordinator=run_coordinator,
    )
