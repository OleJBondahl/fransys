"""The default-symbol table (T2): every row alone, the row order as the contract, the value sets."""

import pytest

import fransys_layout.engines.schematic  # noqa: F401 -- importing registers every fact
from fransys_layout.conventions import FACTS, Row, Table, first_match, validate
from fransys_layout.conventions.symbols import SYMBOL_DEFAULTS
from fransys_layout.engines.schematic.read.symbol_facts import SymbolSubject

# row id -> (kind, rest, protection type, category, gender, symbol): each hits that row alone
_CASES: dict[str, tuple[str, str | None, str | None, str | None, str | None, str]] = {
    "T2.1": ("switch", "operated", None, None, None, "make-contact"),
    "T2.2": ("switch", "rest", None, None, None, "break-contact"),
    "T2.3": ("generic", "operated", None, None, None, "make-contact"),
    "T2.4": ("generic", "rest", None, None, None, "break-contact"),
    "T2.5": ("protection", None, None, None, None, "circuit-breaker"),
    "T2.6": ("protection", None, "fuse", None, None, "fuse"),
    "T2.7": ("protection", None, "mcb", None, None, "circuit-breaker"),
    "T2.8": ("protection", None, "motor_breaker", None, None, "circuit-breaker"),
    "T2.9": ("protection", None, "overload", None, None, "thermal-overload"),
    "T2.10": ("protection", None, "rcd", None, None, "rcd"),
    "T2.11": ("coil", None, None, None, None, "operating-device"),
    "T2.12": ("connector", None, None, None, "female", "contact-female"),
    "T2.13": ("connector", None, None, None, "male", "contact-male"),
    "T2.14": ("connector", None, None, None, "neutral", "contact"),
    "T2.15": ("contact_co", None, None, None, None, "change-over-contact"),
    "T2.16": ("contact_nc", None, None, None, None, "break-contact"),
    "T2.17": ("contact_no", None, None, None, None, "make-contact"),
    "T2.18": ("protection", None, "unknown", None, None, "circuit-breaker"),
    "T2.19": ("plc_channel", None, None, None, None, "plc-channel"),
    "T2.20": ("switch", None, None, None, None, "make-contact"),
    "T2.21": ("terminal", None, None, None, None, "terminal"),
}


def _hit(subject: SymbolSubject, table: Table = SYMBOL_DEFAULTS) -> tuple[str, str] | None:
    row = first_match(table, subject, FACTS)
    return None if row is None else (row.id, str(row.then))


def test_the_table_has_21_rows_and_every_case() -> None:
    """A row added or dropped fails here until it has its own case."""
    assert [r.id for r in SYMBOL_DEFAULTS.rows] == list(_CASES)


@pytest.mark.parametrize("row_id", list(_CASES))
def test_each_row_is_hit_alone(row_id: str) -> None:
    """The subject of a case reaches that row, and no earlier one, with its symbol."""
    kind, rest, protection, category, gender, symbol = _CASES[row_id]
    assert _hit(SymbolSubject(kind, rest, protection, category, gender)) == (row_id, symbol)


@pytest.mark.parametrize("rest", [None, "both"])
def test_a_generic_without_a_rest_has_no_row(rest: str | None) -> None:
    """No row: the function draws a labelled box (SYMBOL_DEFAULTED)."""
    assert _hit(SymbolSubject("generic", rest, None, None, None)) is None


def test_the_row_order_is_the_contract() -> None:
    """Swapping the connector's plain row ahead of its female row changes the symbol."""
    rows = list(SYMBOL_DEFAULTS.rows)
    i, j = (next(n for n, r in enumerate(rows) if r.id == t) for t in ("T2.12", "T2.14"))
    rows[i], rows[j] = rows[j], rows[i]
    female = SymbolSubject("connector", None, None, None, "female")
    assert _hit(female, Table("swapped", "first match", tuple(rows))) == ("T2.14", "contact")
    assert _hit(female) == ("T2.12", "contact-female")


def test_a_misspelt_kind_value_is_caught_by_validate() -> None:
    """The value sets come from the model's enums, so a typo in a row fails at load."""
    bad = Table("bad", "first match", (Row("X", ("function_kind", "coill"), "operating-device"),))
    with pytest.raises(ValueError, match="coill"):
        validate(bad, FACTS)
    validate(SYMBOL_DEFAULTS, FACTS)
