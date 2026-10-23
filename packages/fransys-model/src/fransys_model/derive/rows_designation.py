"""The row of a printed designation: one sign and one label (EL-9, model-0331).

It sits beside `rows.py`. The scheme (`vocab.designation_scheme`) joins a tuple of them.
"""

from fransys_model.kernel import value


@value
class Segment:
    """One piece of a designation: its sign (`=`, `+`, `-`) and its label, as `-` and `K1`."""

    sign: str
    label: str
