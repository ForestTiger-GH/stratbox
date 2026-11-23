"""Family-bound entry points for independently retained processing stages."""
from .family import OPERATIONS
from . import definitions as _definitions

def extract(request, *, context=None, rar_reader=None):
    return OPERATIONS.invoke(_definitions.EXTRACT, OPERATIONS.extract, request,
                   context=context, rar_reader=rar_reader)

def readable(request, *, context=None):
    return OPERATIONS.invoke(_definitions.READABLE, OPERATIONS.readable, request,
                   context=context)

def validate(request, *, context=None):
    return OPERATIONS.invoke(_definitions.VALIDATE, OPERATIONS.validate, request,
                   context=context)

def compare_flakes(request, *, context=None):
    return OPERATIONS.invoke(_definitions.COMPARE_FLAKES, OPERATIONS.compare_flakes, request,
                   context=context)

def project(request, *, context=None):
    return OPERATIONS.invoke(_definitions.PROJECT, OPERATIONS.project, request,
                   context=context)

def align(request, *, context=None):
    return OPERATIONS.invoke(_definitions.ALIGN, OPERATIONS.align, request,
                   context=context)

def compare_datasets(request, *, context=None):
    return OPERATIONS.invoke(_definitions.COMPARE_DATASETS, OPERATIONS.compare_datasets, request,
                   context=context)

def calculate_changes(request, *, context=None):
    return OPERATIONS.invoke(_definitions.CALCULATE_CHANGES, OPERATIONS.calculate_changes, request,
                   context=context)

def calculate_shares(request, *, context=None):
    return OPERATIONS.invoke(_definitions.CALCULATE_SHARES, OPERATIONS.calculate_shares, request,
                   context=context)

def view(request, *, context=None):
    return OPERATIONS.invoke(_definitions.VIEW, OPERATIONS.view, request,
                   context=context)

def render(request, *, context=None):
    return OPERATIONS.invoke(_definitions.RENDER, OPERATIONS.render, request,
                   context=context)

def flake_snapshot(request, *, context=None):
    return OPERATIONS.invoke(_definitions.FLAKE_SNAPSHOT, OPERATIONS.flake_snapshot, request,
                   context=context)

def read_flake_snapshot(request, *, context=None):
    return OPERATIONS.invoke(_definitions.READ_FLAKE_SNAPSHOT, OPERATIONS.read_flake_snapshot, request,
                   context=context)

def projection_snapshot(request, *, context=None):
    return OPERATIONS.invoke(_definitions.PROJECTION_SNAPSHOT, OPERATIONS.projection_snapshot, request,
                   context=context)

def read_projection_snapshot(request, *, context=None):
    return OPERATIONS.invoke(_definitions.READ_PROJECTION_SNAPSHOT, OPERATIONS.read_projection_snapshot, request,
                   context=context)

def dataset_snapshot(request, *, context=None):
    return OPERATIONS.invoke(_definitions.DATASET_SNAPSHOT, OPERATIONS.dataset_snapshot, request,
                   context=context)

def read_dataset_snapshot(request, *, context=None):
    return OPERATIONS.invoke(_definitions.READ_DATASET_SNAPSHOT, OPERATIONS.read_dataset_snapshot, request,
                   context=context)

def calculation_snapshot(request, *, context=None):
    return OPERATIONS.invoke(_definitions.CALCULATION_SNAPSHOT, OPERATIONS.calculation_snapshot, request,
                   context=context)

def read_calculation_snapshot(request, *, context=None):
    return OPERATIONS.invoke(_definitions.READ_CALCULATION_SNAPSHOT, OPERATIONS.read_calculation_snapshot, request,
                   context=context)

def view_snapshot(request, *, context=None):
    return OPERATIONS.invoke(_definitions.VIEW_SNAPSHOT, OPERATIONS.view_snapshot, request,
                   context=context)

def read_view_snapshot(request, *, context=None):
    return OPERATIONS.invoke(_definitions.READ_VIEW_SNAPSHOT, OPERATIONS.read_view_snapshot, request,
                   context=context)

def process(request, *, context=None, rar_reader=None):
    return OPERATIONS.invoke(_definitions.PROCESS, OPERATIONS.process, request,
                   context=context, rar_reader=rar_reader)

def capture_full(request, *, context=None, transport=None, rar_reader=None):
    return OPERATIONS.invoke(_definitions.CAPTURE_FULL, OPERATIONS.capture_full, request,
                   context=context, transport=transport, rar_reader=rar_reader)


def render_artifact(request, *, context=None):
    return OPERATIONS.invoke(_definitions.RENDER_ARTIFACT, OPERATIONS.render_artifact, request, context=context)


def readable_artifact(request, *, context=None):
    return OPERATIONS.invoke(_definitions.READABLE_ARTIFACT, OPERATIONS.readable_artifact, request, context=context)
