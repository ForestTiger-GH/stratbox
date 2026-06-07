"""Runtime assembly for Strategy Box app.

This module is the canonical place where the desktop product surface wires
runtime, platform and application services together.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from app.runtime.context import AppContext
from app.platform.appdock.bridge import AppDockBridge
from app.platform.desktop.services import PlatformServices
from app.application.presence.service import PresenceService
from app.application.product.catalog.registry import build_product_registry
from app.application.product.catalog.models import ProductRegistry
if TYPE_CHECKING:
    from app.presentation.desktop.run_coordinator import RunCoordinator
from app.runtime.app_surface_state import AppSurfaceStateService
from app.runtime.user_preferences import PreferencesService
from app.application.timeline.store import FeedStore


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



def build_runtime(context: AppContext) -> AppRuntime:
    registry = build_product_registry(context)
    feed_store = FeedStore()
    presence_service = PresenceService(context)
    preferences = PreferencesService(context)
    surface_state = AppSurfaceStateService(context)
    platform = PlatformServices()
    bridge = AppDockBridge(context)
    from app.presentation.desktop.run_coordinator import RunCoordinator
    run_coordinator = RunCoordinator(context=context, on_log=context.logger.info)
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
