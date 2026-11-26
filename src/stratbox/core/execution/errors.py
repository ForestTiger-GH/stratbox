"""Backend-independent diagnostics for technical and scientific failures."""
from dataclasses import dataclass

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
