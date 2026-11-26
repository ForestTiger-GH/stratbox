"""Backend-independent diagnostics for technical and scientific failures."""
from dataclasses import dataclass
import re


def error_code(error):
    candidate = getattr(error, "code", None)
    if candidate is None:
        # Domain validation may raise a qualified code directly. Unexpected
        # exceptions can contain caller data even when it resembles a token.
        if not isinstance(error, (ValueError, TypeError)):
            return "internal.error"
        candidate = str(error)
        if "." not in candidate:
            return "internal.error"
    return candidate if isinstance(candidate, str) and re.fullmatch(r"[a-z][a-z0-9_.:-]{0,191}", candidate) else "internal.error"

@dataclass(frozen=True)
class Diagnostic:
    code: str
    message: str = ""
    stage: str | None = None
    evidence_ref: str | None = None

class OperationFailure(RuntimeError):
    def __init__(self, diagnostic, *, outcome="failed"):
        self.diagnostic = diagnostic if isinstance(diagnostic, Diagnostic) else Diagnostic(str(diagnostic))
        self.code, self.outcome = self.diagnostic.code, outcome
        super().__init__(self.code)
