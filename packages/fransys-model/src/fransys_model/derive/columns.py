"""The fields each list output prints of a row shape: the PDF lists and the CSVs read them here."""

# The human-readable fields of each row shape, in the row's field order. An `Id` field is left
# out where the row carries its rendered twin (`terminal` and `designation`, `part` and `mpn`,
# `internal` and `internal_ends`).
TERMINAL_COLUMNS = (
    "designation",
    "group",
    "index",
    "internal_ends",
    "external_ends",
    "jumper_group",
)
# The terminal list's two ends columns are the terminal's port roles, internal then external
# (owner ruling 2026-09-24): headed by these labels, not by the field name. The CSV's header is
# the same label lower-cased with `_` for the space (`side_a`, `side_b`).
TERMINAL_LABELS = {"internal_ends": "Side A", "external_ends": "Side B"}
PLC_COLUMNS = ("channel_designation", "signal", "wired_to", "signal_name")
BOM_COLUMNS = ("mpn", "revision", "manufacturer", "description", "count", "designations")
WIRE_COLUMNS = ("from_", "to", "colour", "cross_section_mm2", "label")
WIRE_LABELS = {"from_": "from"}  # the CSV header of the one column whose field name is a keyword
DESIGNATION_COLUMNS = ("designation", "reference", "description")
# A connector row repeats on each of its pins, so a line is the connector's fields, then the pin's.
CONNECTOR_COLUMNS = ("designation", "style", "pincount", "gender", "mate_designation")
PIN_COLUMNS = ("marking", "net", "mate_port_designation", "ends")
# The PDF connector table prints the pin's fields only, headed Pin, Net, Mate and Ends (pdf-0030).
CONNECTOR_LABELS = {"marking": "Pin", "mate_port_designation": "Mate"}
_CABLE_FIELDS = ("designation", "mpn", "description", "core_count", "gauge_mm2", "length_mm")
CABLE_LIST_COLUMNS = (*_CABLE_FIELDS, "from_label", "to_label", "pairs")
CONTENTS_COLUMNS = (*_CABLE_FIELDS, "ends")
CORE_LIST_COLUMNS = ("cable", "core", "colour", "pair", "end_a", "end_b", "note")
