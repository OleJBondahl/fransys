"""The build's drawing library record: written once after `freeze()`, refused if authored (G6)."""

from decimal import Decimal
from typing import TYPE_CHECKING

from electrical_symbols import LIBRARY, Library, em_heights
from fransys_model.derive.print_sizes import capital_heights, height_key
from fransys_model.kernel import Draft, Origin, SchemaError, evolve, make_id
from fransys_model.layout import DrawingLibrary, layout_of

from ._settings_library import weight_name

if TYPE_CHECKING:
    from fransys_model.kernel import Model

__all__ = ["refuse_authored_library", "with_drawing_library"]

_KEY = ("build", "drawing_library")
_ORIGIN = Origin(
    file="fransys/_drawing_library.py", line=0, note="the symbol library's grid and font"
)


def _record(model: Model, library: Library = LIBRARY) -> DrawingLibrary:
    """The record for the build's `library`; ratios are exact, `Decimal(units / em)`.

    `ems` holds symdef's em of every capital height the build prints at, as the shortest decimal
    of symdef's float (no rounding), under `derive.print_sizes.height_key` of the height.
    """
    font = library.font
    assert font is not None  # noqa: S101 - the bundled library always carries its font
    em = Decimal(font.units_per_em)
    heights = {name: Decimal(str(h)) for name, h in font.heights.items()}
    wanted = capital_heights(model, heights)
    made = em_heights(library, [float(h) for h in wanted])
    return DrawingLibrary(
        id=make_id(DrawingLibrary, _KEY),
        key=_KEY,
        module_mm=Decimal(str(library.grid.module_mm)),
        divisions=library.grid.divisions_per_module,
        wire_pitch=library.grid.wire_pitch,
        wire_pitch_fine=library.grid.wire_pitch_fine,
        font_family=font.family,
        ascent_ratio=Decimal(font.ascent) / em,
        descent_ratio=Decimal(font.descent) / em,
        heights=frozendict(heights),
        lines=frozendict({weight_name(w): Decimal(repr(mm)) for w, mm in library.lines.items()}),
        ems=frozendict({height_key(h): Decimal(repr(made[float(h)])) for h in wanted}),
    )


def _refusal() -> SchemaError:
    msg = "an input authors a layout.drawing_library record: the facade writes it, never an input"
    return SchemaError(msg, kind="layout.drawing_library")


def refuse_authored_library(draft: Draft) -> None:
    """Raise when the merged `draft` holds the kind, before it freezes (spec GRID-HOME, Q2)."""
    if any(isinstance(record, DrawingLibrary) for record in draft.records()):
        raise _refusal()


def with_drawing_library(model: Model, library: Library = LIBRARY) -> Model:
    """`model` with the build's library record; raises when a model already carries the kind."""
    if layout_of(model, DrawingLibrary):
        raise _refusal()
    return evolve(model, put=(_record(model, library),), origin=_ORIGIN)
