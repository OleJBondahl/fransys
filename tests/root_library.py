"""A `freeze` that adds the drawing library record the facade writes (GRID-HOME G6).

The tests build models without the facade; `derive` reads the grid from the record, so a model
needs one. `drawing_library` is this folder's own copy of the bundled library's numbers.
"""

from decimal import Decimal

from fransys._drawing_library import with_drawing_library
from fransys._house import with_house
from fransys.settings import settings
from library_records import drawing_library

from fransys_model.derive import print_sizes
from fransys_model.kernel import Draft, Model
from fransys_model.kernel import freeze as kernel_freeze

_KEY = ("test", "library")
_EM = Decimal(2048)


def with_library(model: Model) -> Model:
    """`model` with the record, the facade's own (so digests agree with a built model)."""
    return with_drawing_library(with_house(model, settings()))


def freeze(draft: Draft) -> Model:
    """`draft` frozen, with the record."""
    return with_library(kernel_freeze(draft))


_MODEL = freeze(Draft())
CAPITAL_RATIO = Decimal(1493) / _EM
ASCENT_RATIO = drawing_library().ascent_ratio


def font_size_mm(capital_height_mm: Decimal) -> Decimal:
    """The font size whose capitals are `capital_height_mm`, read through `derive`."""
    return print_sizes.font_size_mm(_MODEL, capital_height_mm)


def role_height_mm(role: print_sizes.TextRole) -> Decimal:
    """The capital height `role` prints at, read through `derive`."""
    return print_sizes.role_height_mm(_MODEL, role)
