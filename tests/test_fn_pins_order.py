"""`fn.pins` reads a function's pins in the connector list's order, not the part file's (PN1)."""

import fransys as fr


def test_pins_follow_the_connector_list_for_a_part_listed_out_of_marking_order() -> None:
    d = fr.design("demo_parts", place="C1")
    j1 = d.device("J1", "DEMO-CONN-4P-MIXED")
    model = fr.build(d).model
    (row,) = fr.derive.connector_rows(model, j1.id)
    listed = [pin.marking for pin in row.pins]
    assert listed == ["1", "2", "10", "A1"]
    assert [pin.name for pin in j1.x1.pins] == listed
    assert [pin.id for pin in j1.x1.pins] == [pin.port for pin in row.pins]
