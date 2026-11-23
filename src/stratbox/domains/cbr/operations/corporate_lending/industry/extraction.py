"""Source-local extraction receipts shared by atomic and composed operations."""
from dataclasses import replace

from stratbox.core.execution import OperationFailure
from stratbox.shared.data.datasets import ComputationReceipt, build_dataset_version, computation_identity
from stratbox.shared.data.tables import TABLE_ENCODING, TABLE_MEDIA_TYPE, table_identity
from stratbox.shared.evidence import UsedInputReceipt


def seal_flake(value, payload, definition, invocation, *, parameters):
    """Seal exactly one parsed publication under its extraction contract.

    The outer composition retains one budget and one execution envelope. The
    inner receipt identifies the same extraction as an independent parse call,
    with only this original as its input instead of all earlier batch items.
    """
    invocation.budget.charge("cells", value.df_stream.size)
    try:
        output = table_identity((("stream", value.df_stream),), checkpoint=invocation.check_cancelled)
    except (TypeError, ValueError, UnicodeError, RecursionError):
        raise OperationFailure("input.table_value_unsupported") from None
    inputs = (UsedInputReceipt.for_payload(payload, "source_workbook"),)
    parameters = {"encoding": TABLE_ENCODING, **parameters}
    if invocation.definition == definition:
        evidence = invocation.record(output, parameters=parameters, inputs=inputs)
    else:
        version = build_dataset_version(definition.operation_id, f"contract-{definition.contract_version}",
            definition.method_version, inputs, output, parameters=parameters)
        identity = computation_identity(definition.operation_id, definition.contract_version,
            definition.method_version, inputs, parameters=parameters)
        evidence = ComputationReceipt(version, output, inputs, identity, tuple(invocation.context.input_computations))
    return replace(value, evidence=evidence)


def record_flakes(values, invocation):
    """Attach already completed extraction receipts to their composition."""
    for index, value in enumerate(values):
        receipt = value.evidence
        role = f"flake_{index}"
        invocation.use(UsedInputReceipt(role, receipt.output, TABLE_MEDIA_TYPE, "inline",
            source_id=receipt.version.dataset_id, version=receipt.version.identity))
        invocation.parents.append((role, receipt))
