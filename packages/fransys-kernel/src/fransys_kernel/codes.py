"""Finding code registry entries (BUILD-MESSAGES M1, decision model-0223)."""

from dataclasses import dataclass

from .errors import SchemaError
from .findings import CODE_SHAPE, Severity

WHO_ACTS: tuple[str, ...] = ("consumer", "part author", "Fransys", "note")


@dataclass(frozen=True, slots=True, kw_only=True)
class CodeInfo:
    """One finding code's single home: its severity, who acts, cause, fix and guide page.

    Each package lists its codes as `CodeInfo` values in its codes module. The guide's
    findings rows are generated from them, and `fr.report` reads them. `who` is one of
    `WHO_ACTS`; `severities` holds more than one only when sites differ ("WARNING or ERROR").
    `fix` is a `str.format` template, `<valid values>. Write: <corrected call>`; its placeholders
    take the finding's specifics through `filled`.
    `page` is the guide page without `.md`; `see` is the anchor a message ends with.
    """

    code: str
    severities: tuple[Severity, ...]
    stage: str
    who: str
    cause: str
    fix: str
    page: str

    def __post_init__(self) -> None:
        """Refuse a malformed code, an unknown `who`, no severity, or an empty text."""
        problem = _problem(self)
        if problem is not None:
            msg = f"CodeInfo {self.code!r}: {problem}"
            raise SchemaError(msg, kind=type(self).__qualname__)

    def filled(self, **values: str) -> str:
        """The `fix` template with this finding's `values`; a missing value raises, naming the code.

        Raises `SchemaError` when the template names a value that `values` does not give.
        """
        try:
            return self.fix.format(**values)
        except (KeyError, IndexError) as exc:
            msg = f"CodeInfo {self.code!r}: the fix template needs the value {exc}"
            raise SchemaError(msg, kind=type(self).__qualname__) from exc

    @property
    def see(self) -> str:
        """The guide anchor a message ends with, e.g. `findings-render#lone_cell`."""
        return f"{self.page}#{self.code.lower()}"


def _problem(info: CodeInfo) -> str | None:
    if CODE_SHAPE.fullmatch(info.code) is None:
        return "code is not UPPER_SNAKE"
    if info.who not in WHO_ACTS:
        return f"who {info.who!r} is not one of {WHO_ACTS}"
    if not info.severities:
        return "no severity"
    if not (info.stage and info.cause and info.fix and info.page):
        return "stage, cause, fix and page must each be non-empty"
    return None
