"""Public, validated codecs for portable computation and input evidence.

These records contain data and pinned identities only. Decoding never imports
classes or recreates execution providers. Material descriptors and domain
snapshots use the same validation rules.
"""
from __future__ import annotations

from stratbox.shared.data.datasets import ComputationReceipt
from stratbox.shared.evidence import UsedInputReceipt


def computation_value(value: ComputationReceipt | None) -> dict | None:
    from stratbox.shared.materials import _computation
    return _computation(value)


def computation_from(value: dict | None) -> ComputationReceipt | None:
    from stratbox.shared.materials import _read_computation
    return _read_computation(value)


def input_value(value: UsedInputReceipt) -> dict:
    from stratbox.shared.materials import _input, _read_input
    result = _input(value)
    _read_input(result)
    return result


def input_from(value: dict) -> UsedInputReceipt:
    from stratbox.shared.materials import _read_input
    return _read_input(value)


__all__ = ("computation_value", "computation_from", "input_value", "input_from")
