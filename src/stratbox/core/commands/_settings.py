"""Narrow settings access shared by technical command handlers."""
from collections.abc import Mapping


def _get(settings, name, default=None):
    return settings.get(name, default) if isinstance(settings, Mapping) else getattr(settings, name, default)


def _option(context, settings, name, default=None):
    return context.parameters.get(name, _get(settings, name, default))
