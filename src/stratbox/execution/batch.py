"""Ordered attempts for computations whose parsed items can be retained."""

from dataclasses import dataclass
from typing import Generic, TypeVar

from stratbox.base.limits import BudgetExceeded

from .contracts import Diagnostic, OperationFailure

T = TypeVar("T")
R = TypeVar("R")


@dataclass(frozen=True, slots=True)
class BatchAttempt(Generic[T, R]):
    values: tuple[R, ...]
    failed: tuple[tuple[T, Diagnostic], ...]
    interrupted: T | None
    remaining: tuple[T, ...]
    stopped: Diagnostic | None


def attempt_batch(items, read, invocation, *, continue_on_error):
    values, failed = [], []
    stopped = interrupted = None
    attempted = 0
    for index, item in enumerate(items):
        try:
            invocation.progress(index, len(items))
        except (BudgetExceeded, OperationFailure) as error:
            stopped = error.diagnostic if isinstance(error, OperationFailure) else Diagnostic(error.code)
            break
        attempted += 1
        try:
            values.append(read(item))
        except OperationFailure as error:
            if error.outcome == "cancelled":
                stopped, interrupted = error.diagnostic, item
                break
            failed.append((item, error.diagnostic))
            if not continue_on_error:
                stopped = error.diagnostic
                break
        except BudgetExceeded as error:
            stopped, interrupted = Diagnostic(error.code), item
            break
        except Exception as error:
            stopped, interrupted = invocation.incident(error), item
            break
    return BatchAttempt(tuple(values), tuple(failed), interrupted, tuple(items[attempted:]), stopped)


def require_batch_values(batch, empty_code):
    if not batch.values:
        if batch.stopped is not None:
            code = batch.stopped.code
            raise OperationFailure(batch.stopped, outcome="cancelled" if code == "operation.cancelled" else "failed")
        raise OperationFailure(empty_code)
