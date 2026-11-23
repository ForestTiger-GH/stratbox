"""Family-bound entry points for independently retained processing stages."""
from ..pipeline import execute
from . import definitions as _definitions

def extract(request, *, context=None, rar_reader=None):
    return execute(_definitions.EXTRACT, _definitions.DATASET, "extract", request,
                   context=context, rar_reader=rar_reader)

def readable(request, *, context=None):
    return execute(_definitions.READABLE, _definitions.DATASET, "readable", request,
                   context=context)

def validate(request, *, context=None):
    return execute(_definitions.VALIDATE, _definitions.DATASET, "validate", request,
                   context=context)

def compare_flakes(request, *, context=None):
    return execute(_definitions.COMPARE_FLAKES, _definitions.DATASET, "compare_flakes", request,
                   context=context)

def project(request, *, context=None):
    return execute(_definitions.PROJECT, _definitions.DATASET, "project", request,
                   context=context)

def align(request, *, context=None):
    return execute(_definitions.ALIGN, _definitions.DATASET, "align", request,
                   context=context)

def compare_datasets(request, *, context=None):
    return execute(_definitions.COMPARE_DATASETS, _definitions.DATASET, "compare_datasets", request,
                   context=context)

def calculate_changes(request, *, context=None):
    return execute(_definitions.CALCULATE_CHANGES, _definitions.DATASET, "calculate_changes", request,
                   context=context)

def calculate_shares(request, *, context=None):
    return execute(_definitions.CALCULATE_SHARES, _definitions.DATASET, "calculate_shares", request,
                   context=context)

def view(request, *, context=None):
    return execute(_definitions.VIEW, _definitions.DATASET, "view", request,
                   context=context)

def render(request, *, context=None):
    return execute(_definitions.RENDER, _definitions.DATASET, "render", request,
                   context=context)

def flake_snapshot(request, *, context=None):
    return execute(_definitions.FLAKE_SNAPSHOT, _definitions.DATASET, "flake_snapshot", request,
                   context=context)

def read_flake_snapshot(request, *, context=None):
    return execute(_definitions.READ_FLAKE_SNAPSHOT, _definitions.DATASET, "read_flake_snapshot", request,
                   context=context)

def projection_snapshot(request, *, context=None):
    return execute(_definitions.PROJECTION_SNAPSHOT, _definitions.DATASET, "projection_snapshot", request,
                   context=context)

def read_projection_snapshot(request, *, context=None):
    return execute(_definitions.READ_PROJECTION_SNAPSHOT, _definitions.DATASET, "read_projection_snapshot", request,
                   context=context)

def dataset_snapshot(request, *, context=None):
    return execute(_definitions.DATASET_SNAPSHOT, _definitions.DATASET, "dataset_snapshot", request,
                   context=context)

def read_dataset_snapshot(request, *, context=None):
    return execute(_definitions.READ_DATASET_SNAPSHOT, _definitions.DATASET, "read_dataset_snapshot", request,
                   context=context)

def calculation_snapshot(request, *, context=None):
    return execute(_definitions.CALCULATION_SNAPSHOT, _definitions.DATASET, "calculation_snapshot", request,
                   context=context)

def read_calculation_snapshot(request, *, context=None):
    return execute(_definitions.READ_CALCULATION_SNAPSHOT, _definitions.DATASET, "read_calculation_snapshot", request,
                   context=context)

def view_snapshot(request, *, context=None):
    return execute(_definitions.VIEW_SNAPSHOT, _definitions.DATASET, "view_snapshot", request,
                   context=context)

def read_view_snapshot(request, *, context=None):
    return execute(_definitions.READ_VIEW_SNAPSHOT, _definitions.DATASET, "read_view_snapshot", request,
                   context=context)

def process(request, *, context=None, rar_reader=None):
    return execute(_definitions.PROCESS, _definitions.DATASET, "process", request,
                   context=context, rar_reader=rar_reader)

def capture_full(request, *, context=None, transport=None, rar_reader=None):
    return execute(_definitions.CAPTURE_FULL, _definitions.DATASET, "capture_full", request,
                   context=context, transport=transport, rar_reader=rar_reader)


def render_artifact(request, *, context=None):
    return execute(_definitions.RENDER_ARTIFACT, _definitions.DATASET, "render_artifact", request, context=context)


def readable_artifact(request, *, context=None):
    return execute(_definitions.READABLE_ARTIFACT, _definitions.DATASET, "readable_artifact", request, context=context)
