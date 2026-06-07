from __future__ import annotations

from dataclasses import dataclass

from app.core.context import AppContext
from app.integrations.appdock_bridge import AppDockBridge
from app.integrations.platform_services import PlatformServices
from app.presence.service import PresenceService
from app.product.registry import build_product_registry
from app.product.models import ProductRegistry
from app.runs.service import RunCoordinator
from app.state.app_surface_state import AppSurfaceStateService
from app.state.user_preferences import PreferencesService
from app.timeline.store import FeedStore


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
    run_coordinator: RunCoordinator



def build_runtime(context: AppContext) -> AppRuntime:
    registry = build_product_registry(context)
    feed_store = FeedStore()
    presence_service = PresenceService(context)
    preferences = PreferencesService(context)
    surface_state = AppSurfaceStateService(context)
    platform = PlatformServices()
    bridge = AppDockBridge(context)
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
