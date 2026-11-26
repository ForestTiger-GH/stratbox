"""Logical command boundaries are charged for every admitted consumer.

Sharing saves physical work such as transport, decoding and temporary writes.
It does not waive the input or returned-value limits of a consuming run.
"""
from collections.abc import Mapping
from dataclasses import fields, is_dataclass

from stratbox.shared.data.materials import StagedMaterialRef, staged_references
from stratbox.shared.data.values import EncodedProduct, ImmutableMaterialRef, Material, fingerprint

from .owned_values import _cells, _size


def _input_materials(value):
    """Deduplicate physical carriers within one boundary, without parent bodies.

    A reference's lineage describes prior processing; it does not request those
    bodies as additional command inputs. Compact and attributed references to
    the same qualified physical object count as one supplied body.
    """
    pending, visited, references = [value], set(), {}
    while pending:
        item = pending.pop()
        if id(item) in visited:
            continue
        visited.add(id(item))
        if isinstance(item, StagedMaterialRef):
            key = ("staged", item.session_id, item.stage_id)
            if key in references and references[key] != item:
                raise ValueError("stage.conflicting_descriptor")
            references[key] = item
        elif isinstance(item, ImmutableMaterialRef):
            key = ("retained", item.provider_id, item.provider_scope, item.location,
                   item.identity, item.guarantee, item.effect_id, item.accepted_value_id)
            references[key] = item
        elif isinstance(item, (Material, EncodedProduct)):
            continue  # Their supplied bytes are already measured as resident data.
        elif isinstance(item, Mapping):
            pending.extend(item.values())
        elif isinstance(item, (tuple, list, set, frozenset)):
            pending.extend(item)
        elif is_dataclass(item) and not isinstance(item, type):
            pending.extend(getattr(item, descriptor.name) for descriptor in fields(item))
    return tuple(references.values())


def account_inputs(meter, inputs):
    cells_before = meter.used("cells")
    meter.charge("input_bytes", _size(inputs))
    for reference in _input_materials(inputs):
        meter.charge("input_bytes", reference.identity.size)
    meter.charge("cells", _cells(inputs))
    return cells_before


def account_outputs(meter, outputs, *, cells_before, output_owner):
    output_cells = _cells(outputs)
    charged = meter.used("cells") - cells_before
    if output_cells > charged:
        meter.charge("cells", output_cells - charged)
    # Completed representations still consume the byte boundary after a deadline.
    # Descriptor RAM and the bytes behind a staged carrier are separate resources.
    meter.charge("output_bytes", _size(outputs), completed=True)
    for reference in staged_references(outputs):
        meter.account_output(fingerprint(("returned", output_owner, reference.stage_id)),
                             reference.identity, completed=True)
