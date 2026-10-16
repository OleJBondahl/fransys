"""`ref` writes the id through the kernel's `render_id`, inside angle quotes (T8)."""

import re

from fransys_model.kernel import make_id, render_id
from fransys_model.vocab.core import Unit
from fransys_model.vocab.finding_ref import REF, ref


def test_a_reference_is_the_rendered_id_in_angle_quotes() -> None:
    unit = make_id(Unit, ("cab",))
    assert ref(unit) == f"⟨{render_id(unit)}⟩"
    assert re.fullmatch(REF, ref(unit))
