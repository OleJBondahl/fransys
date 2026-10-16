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
PLC_COLUMNS = ("pin", "channel_name", "signal", "signal_name", "wired_to")
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
# The CONTENTS table's headings, in the order of `CONTENTS_COLUMNS` (pdf-0044). They differ from a
# generic column label in three places: MPN, Cores, Gauge.
CONTENTS_LABELS = ("Designation", "MPN", "Description", "Cores", "Gauge", "Length mm", "Ends")


def column_label(field: str) -> str:
    """`field` as a table header: underscores to spaces, first letter upper-cased."""
    spaced = field.rstrip("_").replace("_", " ")
    return spaced[0].upper() + spaced[1:]


def csv_name(label: str) -> str:
    """A heading as its CSV header: spaces to `_`, lower-cased (`Side A` is `side_a`)."""
    return label.replace(" ", "_").lower()
