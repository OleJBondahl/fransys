"""A `freeze` that adds the drawing library record the facade writes (GRID-HOME G6).

The tests build models without the facade; `derive` reads the grid from the record, so a model
needs one. `drawing_library` is this folder's own copy of the bundled library's numbers.
"""

from decimal import Decimal

from fransys._drawing_library import with_drawing_library
from fransys._house import with_house
from fransys.settings import settings

from fransys_model.derive import print_sizes
from fransys_model.kernel import Draft, Model, make_id
from fransys_model.kernel import freeze as kernel_freeze
from fransys_model.layout import DrawingLibrary

_KEY = ("test", "library")
_EM = Decimal(2048)


def drawing_library(divisions: int = 8) -> DrawingLibrary:
    """The record with the bundled library's numbers."""
    return DrawingLibrary(
        id=make_id(DrawingLibrary, _KEY),
        key=_KEY,
        module_mm=Decimal("2.5"),
        divisions=divisions,
        wire_pitch=8,
        wire_pitch_fine=4,
        font_family="DejaVu Sans",
        ascent_ratio=Decimal(1556) / _EM,
        descent_ratio=Decimal(426) / _EM,
        ems=frozendict(
            {
                h: Decimal(h) * _EM / 1493
                for h in ("1", "1.8", "2", "2.2", "2.5", "3", "3.2", "3.5", "4", "5", "6")
            }
        ),
        lines=frozendict(
            {"normal": Decimal("0.25"), "thick": Decimal("0.5"), "rule": Decimal("0.18")}
        ),
        heights=frozendict(
            {
                "smallest": Decimal("1.8"),
                "body": Decimal("2.5"),
                "heading_2": Decimal("3.5"),
                "heading_1": Decimal(5),
            }
        ),
    )


def with_library(model: Model) -> Model:
    """`model` with the record, the facade's own (so digests agree with a built model)."""
    return with_house(with_drawing_library(model), settings())


def freeze(draft: Draft) -> Model:
    """`draft` frozen, with the record."""
    return with_library(kernel_freeze(draft))


_MODEL = freeze(Draft())
CAPITAL_RATIO = Decimal(1493) / _EM
ASCENT_RATIO = drawing_library().ascent_ratio


def font_size_mm(capital_height_mm: Decimal) -> Decimal:
    """The font size whose capitals are `capital_height_mm`, read through `derive`."""
    return print_sizes.font_size_mm(_MODEL, capital_height_mm)


def role_height_mm(role: print_sizes.TextRole, profile_text_height_mm: Decimal) -> Decimal:
    """The capital height `role` prints at, read through `derive`."""
    return print_sizes.role_height_mm(_MODEL, role, profile_text_height_mm)
