"""The export ledger: each export's place in `out_dir`, and the refusal of a repeated name."""

from typing import TYPE_CHECKING, Any
lazy from collections.abc import Callable

from fransys_reports import changes_csv

from fransys_model.derive import export_bytes, export_form_of, export_path
lazy from fransys_model.derive.baseline import ListingDiff

from ._codes import finding
from ._finding_text import described
from ._release_reader import BASELINE_FILES
from ._times import Timer

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model


def changes_csv_file(model: Model, diff: ListingDiff) -> dict[str, bytes]:
    """The `changes.csv` export of `diff`, placed and encoded by the `[export]` record."""
    form = export_form_of(model)
    name = export_path(form, BASELINE_FILES["changes_csv"])
    return {name: export_bytes(form, name, changes_csv(diff, model=model))}


class ExportNameClashError(Exception):
    """Two subjects resolve to the same export file name in `out_dir`."""


def _export_name_clash(name: str, a: Id[Any], b: Id[Any], model: Model, *, hint: str | None = None) -> ExportNameClashError:
    if hint is None:
        message = f"two subjects both resolve to the export name {name!r}"
    else:
        message = f"two units, both instances of release {hint!r}, both export the file {name!r}; keep one document per release."
    return ExportNameClashError(described(finding("EXPORT_NAME_CLASH", (a, b), message), model))


class _ExportLedger:
    """Export names, and with `names_only=False` their bytes, refusing a name two subjects want.

    `names` maps `(kind, subject)` to the name: one traversal gives `write` its bytes and
    `export_names` its names, so the naming rule has one home.
    """

    def __init__(self, model: Model, *, names_only: bool = False, timer: Timer | None = None) -> None:
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
        form = export_form_of(self._model)
        name = export_path(form, name)
        held = self._subjects_by_name.get(name)
        if held is not None and subject is not None and held != subject:
            raise _export_name_clash(name, held, subject, self._model, hint=hint)
        self.names[(kind, subject)] = name
        self._subjects_by_name[name] = subject
        if not self._names_only:
            made = self._timer.run(name, data)
            self.exports[name] = export_bytes(form, name, made) if isinstance(made, str) else made
