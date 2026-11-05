"""The errors of `fransys_parts`: a failed library, and an unreadable part-file text or value."""

from fransys_model.derive import error_count
from fransys_model.kernel import Finding, ModelError

__all__ = ["PartLibraryError", "PartTextError"]


class PartLibraryError(ModelError):
    """A part library failed `lint`; `findings` holds every finding of that run.

    Warnings included, not only the `ERROR`s that triggered the raise: a caller
    fixing the library wants the whole report, not a partial one.
    """

    def __init__(self, findings: tuple[Finding, ...]) -> None:
        """Store every finding `lint` returned, in its own order."""
        errors = error_count(findings)
        super().__init__(f"{errors} error(s) in the part library")
        self.findings = findings


class PartTextError(PartLibraryError):
    """A part-file value that is not a figure, or a value the schema 2 reader refuses."""

    def __init__(self, reason: str) -> None:
        """Keep `reason` as the message; no finding is attached."""
        ModelError.__init__(self, reason)
        self.findings = ()
