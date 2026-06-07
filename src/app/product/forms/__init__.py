"""Product form contracts for Strategy Box.

GUI factories/widgets are imported explicitly from their submodules so service
routes and AppDock preflight can import defaults/models without PySide.
"""

from .models import FieldSection, ParamType, ProductParamSpec

__all__ = ['FieldSection', 'ParamType', 'ProductParamSpec']
