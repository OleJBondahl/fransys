"""The row shape of `derive.export_set`: one export of a write (model-0283, model-0199).

It sits beside `rows.py`; a plain value: a kind, a name and the subject it is about.
"""

from typing import Any

from fransys_model.kernel import Id, value

__all__ = ["ExportRow"]


@value
class ExportRow:
    """One file a write makes, before it is placed in `data/`.

    - `export_kind`: `"bom"`, `"plc"`, `"wires"`, `"designations"`, `"cables"`, `"cores"`,
      `"overview"`, `"terminals"`, `"connectors"`, `"wago"` or `"pdf"`; `extension` ends the name.
    - `subject`: the strip, board, rack or document id; `None` for a whole-model report.
    - `name`: `export_name` or `document_export_name`; `hint` the unit-set name a clash of two
      units of one release should keep one document of, else `None`.
    """

    export_kind: str
    extension: str
    subject: Id[Any] | None
    name: str
    hint: str | None
