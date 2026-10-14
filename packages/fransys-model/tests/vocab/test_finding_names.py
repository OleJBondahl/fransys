"""Tests: `name_findings` prints each reference as the drawings print the thing (overview-0003)."""

import re
from pathlib import Path

from plant import Plant

from fransys_model.derive.numbering_pins import name_findings, name_of
from fransys_model.kernel import Finding, Id, Severity
from fransys_model.vocab import validators
from fransys_model.vocab.finding_ref import REF, ref
from fransys_model.vocab.tables import items


def _finding(message: str) -> Finding:
    return Finding(code="X", severity=Severity.INFO, subjects=(), message=message)


def test_a_reference_of_a_record_equals_the_reference_of_its_id() -> None:
    plant = Plant()
    made = plant.item("a")
    item = items(plant.model())[made]
    assert ref(item) == ref(item.id)
    assert REF.fullmatch(ref(item))


def test_a_thing_with_no_printed_text_is_named_by_its_kind_alone() -> None:
    plant = Plant()
    model = plant.model()
    assert name_of(model, Id(kind="unit", value="0" * 32)) == "unit"
    assert name_of(model, Id(kind="port", value="0" * 32)) == "port"
    assert name_of(model, Id(kind="harness", value="0" * 32)) == "harness"


def test_every_reference_in_a_message_is_replaced_and_no_key_is_left() -> None:
    plant = Plant()
    one, two = plant.unit("first-key"), plant.unit("second-key")
    model = plant.model()
    (named,) = name_findings(model, (_finding(f"of {ref(one)} and of {ref(two)} clash"),))
    assert named.message == "of unit rev 1.1 and of unit rev 1.1 clash"
    assert "key" not in named.message


def test_an_untagged_unit_is_named_by_the_name_and_revision_its_title_block_prints() -> None:
    plant = Plant()
    one, two = (
        plant.unit("first-key", name="relay-board"),
        plant.unit("second-key", name="io-board"),
    )
    model = plant.model()
    (named,) = name_findings(model, (_finding(f"of {ref(one)} and of {ref(two)} clash"),))
    assert named.message == "of relay-board rev 1.1 and of io-board rev 1.1 clash"


def test_no_rendered_message_for_a_unit_holds_unit_unit() -> None:
    plant = Plant()
    untagged = plant.unit("a-key", name="relay-board")
    tagged = plant.unit("b-key", name="io-board", tag="U1", class_code="U")
    unheld = Id(kind="unit", value="0" * 32)
    model = plant.model()
    for target, expected in (
        (untagged, "of relay-board rev 1.1"),
        (tagged, "of unit -U1"),
        (unheld, "of unit"),
    ):
        (named,) = name_findings(model, (_finding(f"of {ref(target)}"),))
        assert named.message == expected
        assert "unit unit" not in named.message


def test_no_validator_template_writes_unit_right_before_a_unit_reference() -> None:
    root = Path(validators.__file__).parent
    joined = {path: re.sub(r'"\s*f"', "", path.read_text()) for path in root.glob("*.py")}
    bad = [path.name for path, text in joined.items() if re.search(r"\bunit \{ref\(", text)]
    assert bad == []
