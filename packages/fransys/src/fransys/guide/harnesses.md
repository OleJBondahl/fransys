# Harnesses

This page teaches how to add a harness to a design with `d.harness`, and how its cables and plugs
print. It follows `authoring.md`, which holds the rest of the authoring calls.

## Add a harness

`d.harness("W5")` adds a part-less harness item and returns its handle, which a document can take
as its subject (see `documents.md`). A harness holding a cable needs a tag: `d.harness(name="loom")`
with no tag builds, then fails with `HARNESS_WITHOUT_TAG`. A part-less harness holding exactly one
cable prints that cable as its own designation (`-W5`, its cores `-W5:1`); its plugs stay `-W5-J1`.
With two cables they print `-W5-W1` and `-W5-W2`.
A harness with one cable prints the cable with the harness's designation. The cable's own tag is not printed.

## Wires on a harness

`d.harness("W1")` marks the item as a harness, so plugs and plain wires need no cable. A wire with an
end on a plug of `W1` is a wire of `W1`: `fransys.derive.harness_wires(model, w1_id)` lists its rows.
A wire between plugs of two harnesses is the ERROR `WIRE_ON_TWO_HARNESSES`. A cable beside a wire
prints `-W1-W1`; a cable that is the whole harness prints `-W1`.
A harness of plain wires draws on a harness drawing as one block, with its end boxes and one line per wire, and no cable box.

## Fit a housing on a part's leads

`d.device("J1", "DEMO-HSG-4F", parent=k1, joins={"1": k1.coil["A1"], 2: k1.coil["A2"]})` fits the
housing on the leads of `K1`. Each pair joins a pin of the new device to a pin of `K1`, with no wire
and no cable (a `LEAD` link). The housing prints `-K1-J1`. `joins=` needs a parent device and refuses
a pin twice or a pin of another device with an `AuthorError`.

## Add crimp contacts

`d.device("P1", "DEMO-HSG-4M", parent=w1, contacts="DEMO-CRIMP-M")` fits that contact part in every
used pin of a connector item: a plug, a housing, or any part with a connector function.
A mapping gives mixed contacts: `contacts={"1": "DEMO-CRIMP-M", "2": "DEMO-CRIMP-F"}`.

A used pin is one where a wire or a core lands. The BOM gets one line per contact part. Its count is
the used pins, and its designations are the housings, so one more wire adds one contact.
`contacts=` on a part with no connector function, an unknown pin name or an unknown part raises
`AuthorError`, and the call adds nothing. The contact part is a part file with no function.

## Read a harness line's texts

`fransys.derive.draws_as_line(model, item)` says whether a cable or harness draws as a harness line.
It does when its line carries two or more conductors, cores and single wires together. A cable on a
harness answers for its harness. `line_conductors(model)` maps each line's owner to those conductors.

`fransys.derive.harness_line_ends(model, subject)` returns one `HarnessLineEnd` per end of a harness or
cable line. It holds `branch` (the n of `-W13.n`), `plug` or `ports`, and the function `plug` mates.
Cable ends and single-wire ends merge into one order, plugs first by designation. Read the branch
number from it; never number ends yourself.

`line_designation(model, harness, branch)` prints `-W13` between two ends and `-W13.n` on a branch of
three or more. `line_stub_line(line, north=, far=)` prints a leaving line's one stub, `-W3 → +EXT-M1`.
An off stub prints that form when its cable draws as a line; a one-conductor cable keeps the per-core form.
`connector_box_lines(model, function, unit=)` returns a connector box's lines: its designation, the
part's MPN when every function of its item is a connector function, and the interface name when it
differs from the designation.
A schematic page prints no wire label but a harness line's designation (`-W13`), with one leg per wire
where no plug stands. `line_designation` and `connector_box_lines` take the `unit` of the document that
prints them: on a unit's own document no text names that unit's tag.

`connector_at_line_end(model, function)` says whether a connector stands at a harness line's end: a
plug, the function a plug mates, or a fan-out pin's function, on a line that `draws_as_line` holds.
`supply_share(model, function)` returns the share, as a `Fraction`, of an interface's connected pins
on a supply potential (a rail, 24 V or GND). It is a rank, not a direction.
`check_side_hints(model)` returns the WARNING for each side hint whose interface is not at a line end.
