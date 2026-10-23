"""The export ledger: each export's place in `out_dir`, and the refusal of a repeated name."""

from typing import Any
lazy from collections.abc import Callable

from fransys_model.kernel import Finding, Id, Model, Severity

from ._codes import fix_text
from ._finding_text import described
from ._times import Timer

# CSV and XML exports live in `<out_dir>/data/`; PDFs, `overview.html` and `changes.md` stay on top.
_DATA_DIR = "data"
_DATA_SUFFIXES = (".csv", ".xml")


def _placed(name: str) -> str:
    """`name` as its path from `out_dir`: CSV and XML go into `data/`, the rest stay (0197)."""
    return f"{_DATA_DIR}/{name}" if name.endswith(_DATA_SUFFIXES) else name


class ExportNameClash(Exception):  # noqa: N818 -- the exact name the contract gives it
    """Two subjects resolve to the same export file name in `out_dir`."""


def _export_name_clash(
    name: str, a: Id[Any], b: Id[Any], model: Model, *, hint: str | None = None
) -> ExportNameClash:
    if hint is None:
        message = f"two subjects both resolve to the export name {name!r}"
    else:
        message = (
            f"two units, both instances of release {hint!r}, both export the file {name!r}; "
            "keep one document per release."
        )
    finding = Finding(
        code="EXPORT_NAME_CLASH",
        severity=Severity.ERROR,
        subjects=(a, b),
        message=message,
        fix=fix_text("EXPORT_NAME_CLASH"),
    )
    return ExportNameClash(described(finding, model))


class _ExportLedger:
    """Export names, and with `names_only=False` their bytes, refusing a name two subjects want.

    `names` maps `(kind, subject)` to the name: one traversal gives `write` its bytes and
    `export_names` its names, so the naming rule has one home.
    """

    def __init__(
        self, model: Model, *, names_only: bool = False, timer: Timer | None = None
    ) -> None:
        self._model = model
        self._timer = timer or Timer()
        self._names_only = names_only
        self.exports: dict[str, bytes] = {}
        self.names: dict[tuple[str, Id[Any] | None], str] = {}
        self._subjects_by_name: dict[str, Id[Any] | None] = {}

    def add(
        self,
        kind: str,
        name: str,
        subject: Id[Any] | None,
        data: Callable[[], str | bytes],
        *,
        hint: str | None = None,
    ) -> None:
        name = _placed(name)
        held = self._subjects_by_name.get(name)
        if held is not None and subject is not None and held != subject:
            raise _export_name_clash(name, held, subject, self._model, hint=hint)
        self.names[(kind, subject)] = name
        self._subjects_by_name[name] = subject
        if not self._names_only:
            made = self._timer.run(name, data)
            self.exports[name] = made.encode("utf-8") if isinstance(made, str) else made
