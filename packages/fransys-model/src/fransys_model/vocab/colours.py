"""What the colour grammar leaves to Fransys: the two reserved codes and the finding's sentence (decision model-0070).

`elecdef.core_colour` reads a colour (a base code, two joined, a base code and a core number, `SH`);
it gives `None` for the empty colour, which Fransys allows: no colour recorded.
"""

from typing import Final

from fransys_model.elecdef import Colour
from fransys_model.kernel import natural_key

# The two reserved conductor codes, by meaning (CABLE-05, CABLE-06): `SH` is the cable screen, a
# conductor and no colour of a core; `GNYE` is the protective-earth core (IEC 60204-1).
RESERVED_CODES: Final = frozendict({"shield": "SH", "protective earth": "GNYE"})

_GLOSS: Final = {colour.name: colour.gloss for colour in Colour if colour is not Colour.GNYE}

# What a finding says an allowed colour is, read from the library's colour glosses in natural order.
COLOUR_GRAMMAR: Final = (
    "an IEC 60757 colour code: a base code ("
    + ", ".join(f"{name} {_GLOSS[name]}" for name in sorted(_GLOSS, key=natural_key))
    + f"), two different base codes joined (GNYE), a base code and a core number (BK1), or {RESERVED_CODES['shield']} shield alone"
)
