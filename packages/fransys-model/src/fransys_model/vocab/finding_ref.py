"""A finding message names a thing by a reference that `name_findings` prints (overview-0003).

`vocab` cannot import `derive`, where a thing's printed text lives (`printed_designation`,
`port_designation`, `wire_text`). A validator writes `ref(record)` into its message instead of an
authoring key; the pipeline replaces each reference with the thing as the drawings print it.
"""

import re
from typing import Final

from fransys_model.kernel import Id, Record

__all__ = ["REF", "ref"]

#: One reference: `<`kind`:`value`>` with angle quotation marks, which no message holds otherwise.
REF: Final[re.Pattern[str]] = re.compile("⟨([^:⟩]+):([^⟩]+)⟩")


def ref(target: Id[Record] | Record) -> str:
    """The reference to a record or an id, for a finding message."""
    one = target if isinstance(target, Id) else target.id
    return f"⟨{one.kind}:{one.value}⟩"
