# Reading a model

`fransys.derive` is the read side of a model: every designation, table, row and rating a
script might need already has a function here, and layout, render and every output call the
same ones. This page does not restate `fr.derive`'s whole surface. Every function carries its
own docstring at its definition, and that docstring is the full reference. What follows is a
short tour of the read surface as this release documents it explicitly: enough to know what is
there and how to reach for it.

Two facts hold across the whole surface, so they are said once, here:

- Ids are opaque keys. A script looks a record up by its id (in a table, or by passing the id
  to a `derive` function); it never builds, parses or prints an id itself.
- An item's name is `item.key[-1]`. There is no separate `.name` field.

## The tables

`fransys.derive.units(model)` returns every `Unit` of `model`, by id, as a
`frozendict[Id[Unit], Unit]`. The other tables (`nets`, `unit_releases`, `supply_systems`,
and more) follow the same shape: one function per record kind, keyed by id.

- `fransys.derive.nets(model)`: every `Net` of `model`, by id.
- `fransys.derive.unit_releases(model)`: every `UnitRelease` of `model`, by id. A
  `UnitRelease` is the product a `Unit` instantiates (its name, version, revision, interface,
  title and document number); several `Unit`s can share one release.
- `fransys.derive.supply_systems(model)`: every `SupplySystem` of `model`, by id. A
  `SupplySystem` is a declared supply and its rails (a potential name, its maximum voltage and,
  for AC, its phase).

## One unit's release

`fransys.derive.unit_release(model, unit)` reads the one `UnitRelease` record a `Unit`
instance is of. It is the one reader of a unit's release facts.

`fransys.derive.unit_location(model, unit)` returns the location node `unit` is placed at:
its root items' own location, or their nearest common ancestor; `None` when no root is placed.

## Rails, boundaries and function kinds

`fransys.derive.port_rails(model, port)` returns the rails a port carries, as a
`frozenset[str]` of potential names: empty for a port that carries none, or is not in
`model`. A rail only exists once some `SupplySystem` declares the potential and some `Net`
carries it; wiring alone declares no rail.

`fransys.derive.port_potential_rank(model, port)` is the rank of the potential a pin carries, or `None`.
A smaller rank is drawn higher up. It reads the supply's facts, never a rail's name. The order is AC phases,
DC above 0 V, AC at 0 V, DC at 0 V, DC below 0 V, then PE. A pin behind a switch keeps its
rail's rank. A pin reached from two rails takes the lower. `fransys.derive.port_potential_current(model,
port)` gives the rail's `Current`, and `None` for PE or no rank.

`fransys.derive.takes_energy(model, function)` is `True` when `function` takes energy in: its part's
declared `energy` when it has one, else `True` for a `load` and `False` for any other kind. A box draws
the pins of an energy-in function above those of an energy-out one.

`fransys.derive.gives_energy(model, function)` is `True` when `function` gives energy out: its part's
declared `energy` when it has one, else `True` for a `supply` and `False` for any other kind. A box draws
a function that takes or gives energy above a signal function.

`fransys.derive.no_conductor_at(model, port)` is `True` when no conductor (wire, jumper, cable core
or link) ends at `port`. Unlike `unconnected_ports`, a mate or a declared net does not count.

`fransys.derive.box_pairs(model)` maps each function wired pin to pin to one function of another
item, to a `BoxPair` (`function`, `partner`, `port_pairs`). Every port needs a two-port net to the partner, one to one.

`fransys.derive.port_is_unused(model, port)` is `True` when no conductor ends at `port` and no declared
net has it. A mate does not count. `fransys.derive.function_is_unused(model, function)` is `True` when
every port of `function` is unused: the function `hide_unused_pins` leaves off the page, and a contact
among them is a spare in its coil's contact table.

`fransys.derive.power_kind(model, net)` returns a `PowerKind` for a declared net: `SUPPLY`,
`GROUND`, `PE` or `NONE`. A net of class `pe` is `PE`. A potential of a DC supply is `GROUND` at
0 V and `SUPPLY` otherwise. An AC rail, a potential in no supply, no potential, or two
potentials on one wired net is `NONE`. So is a wired net of exactly two ports. A point-to-point
connection is a wire; only a net of three or more ports is a rail. A PE net stays `PE`. `port_power_kind(model, port)` gives the kind of a
port's wired net. A DC supply declares its 0 V rail (`rails={"24V": ("24", None), "0V": ("0",
None)}`). Without it, the 0 V net gets references, not a ground symbol. `power_text(model, net)`
is the text a power symbol prints: the supply's name, else its potential. It is `None` for
`GROUND`, `PE` and `NONE`. `port_power_text(model, port)` gives the text of the symbol at a port.
`is_rail_terminal(model, terminal)` is true for a terminal on a DC rail or PE net, bridged to
another terminal of its strip.
A schematic page draws no rail terminal. A pin wired to one, or to another pin on a power net, draws the rail's power symbol. No wire joins two such pins. The terminal table and the wire list still hold every landing and wire.
A terminal is drawn at the pin it serves, once per page. A single-wire contact, and a coil on a PLC output channel, are drawn at the pin they serve, with a reference back to their device. A rail symbol faces away from its box: up above a top pin, down below a bottom pin.

`fransys.derive.wire_rows(model, *, unit=None)` returns the wire list: one `WireRow` per
wire, with `from_`, `to`, `colour`, `cross_section_mm2` and `label`. The `label` is the two end
designations joined by one space in a fixed order, the text the wire list and sleeves print. A schematic page prints no wire label. A jumper,
a cable core and a link give no row. `fr.write` writes these rows as `<set>-wires.csv`.

`fransys.derive.boundary(model, unit)` returns the functions that make up a unit's
interface, as a tuple of function ids in id order. Only `TERMINAL` and `CONNECTOR` functions
can be a unit's boundary.

`fransys.derive.FunctionKind` is the enum of what a `Function` exposes: `COIL`,
`CONTACT_NO`, `TERMINAL`, `CONNECTOR`, `SUPPLY`, and so on. A function's `kind` is one of
these.

`fransys.derive.connector_facets(model)` returns every `connector` facet, by the function
template it describes, as a `frozendict[Id[FunctionTemplate], ConnectorFacet]`.

## Rows

`fransys.derive.bom_lines(model, scope=None)` returns the parts list, one `BomLine` per
installed, non-external part (by mpn, revision and part), or one line per nested unit when
`scope` is a unit. `scope` narrows what is counted: `None` for the whole model, an item id for
that item's subtree, an aspect-node id for what is placed there, a unit id for that unit's
own items and its directly nested units, or `fransys.derive.TOP_LEVEL` for items with no
unit plus one line per top-level unit. `TOP_LEVEL`'s type, `fransys.derive.TopLevelScope`,
is exported only so a script can annotate a variable that holds it.

`fransys.derive.NO_PLACE` is the text "N/A" a coil's contact table prints after the mark of a
contact that no conductor reaches, in place of a page position.

`fransys.derive.bom_sort_key(model, item)` is the sort key `bom_lines` orders a line's
`designations` by: a terminal by its strip, group and index; any other item by its whole
designation string.

`fransys.derive.is_cable(model, item)` returns whether `item` is a cable: whether its part
carries a `cable_product` facet (decision model-0108). `fransys.derive.cable_items(model)`
returns every such item, as a `frozenset[Id[Item]]`. Neither reads `item`'s own `category` or
its `cable` facet, which records only the as-installed length of a cable already known to be
one. Every cable-selecting function on this page (`harness_cables`, `top_level_cables`,
`unit_cables`, `cable_list_rows`) reads through one of these two, so none can disagree about
what a cable is.

`fransys.derive.is_plc_module(model, item)` returns whether `item`'s part has category
`PLC_MODULE`. A rack is an item with at least one such child, and `plc_rack_modules` lists them.

`fransys.derive.unit_strips(model, unit)` and `fransys.derive.unit_boards(model, unit)`
return the terminal strips and the boards that `unit` owns directly, sorted by id, never those of
a unit nested in it.

`fransys.derive.terminal_items(model)` returns every item that carries a `terminal` facet, as a
`frozenset[Id[Item]]`. Select terminals through it, so no script rebuilds the set from the facets.

`fransys.derive.cable_list_rows(model)` returns one `CableListRow` per top-level cable
(every cable item, `is_cable`, with `unit=None`, harness cables included), with its product
facts and the designations of its two lowest-ranked ends.

`fransys.derive.contents_rows(cables)` reshapes a tuple of `HarnessCable`s (from
`harness_cables`, `top_level_cables` or `unit_cables`) into one `ContentsRow` per cable, its
product facts alongside `ends`: every end's designation, in the cable's own order, joined by an
en dash, with a blank end dropped along with its dash. `CONTENTS_COLUMNS` names its columns, in
print order.

## Designations

`fransys.derive.item_designation(model, item)` renders an item's own printed label, such as
`K1`, or `U1-K1` for one nested inside a board.

`fransys.derive.port_designation(model, port)` renders a port's label: the item's
designation plus the port's name, dash-prefixed like every physical tag (`-K1:13`).

`fransys.derive.reference_designation(model, item)` renders an item's full reference: its
location and its product designation together (`+C1-K1`).

`fransys.derive.printed_designation(model, item)` renders an item the way a list prints it:
dash-prefixed, product part only, with no location segment.

Each of these takes further keyword-only options (an inner board to render relative to, a unit
to render for that unit's own document); their docstrings cover the exact rules.

`fransys.derive.item_label(model, item)` is `item_designation`'s no-raise twin: an item's own
text, or its authoring key joined by `/` when it has none yet.

`fransys.derive.location_node_designation(model, node)` renders a location node's own signed
path, root to leaf (`+C1`, nested `+ER+C1`) -- the same segment `reference_designation` prints
for an item placed there. Caution: not for a title block's scope cell, which deliberately keeps
the bare label.

`fransys.derive.owned_contacts(model, device)` returns the contact functions `device` owns,
sorted by id: its own and those of its add-on contact blocks. A block is a child item whose
functions are all contacts; it carries no designation and prints `device`'s (decision model-0119).

`fransys.derive.item_of_port(model, port)` returns the item whose function owns `port`, the
lookup `port_designation` itself reads through.

## Ratings

`fransys.derive.part_rating(model, part)` returns the rating stated on a part itself, for a
part with no function to rate, such as a fuse link. `None` when the part states none. It reads
the model after the build.
`d.rating` and `d.operating` state a rating or an operating envelope while authoring; the
functions below read it back.

`fransys.derive.function_rating(model, function)` returns the rating a function's template
states, else its part's. `None` when neither states one.

`fransys.derive.function_operating(model, function)` returns the operating envelope a
function's template states. `None` with no template or no such facet.

`fransys.derive.boundary_rating(model, boundary)` returns the rating a unit states on one of
its boundaries. `None` when the unit states none.

`fransys.derive.boundary_operating(model, boundary)` returns the operating envelope a unit
states on one of its boundaries. `None` when the unit states none.

## A worked example

The design is authored with `fr.design`; every read below runs on `result.model` after the build.
A pin handle such as `housing[1]` has an `.id`; an item is found by its `tag` in
`fr.derive.items(model)`.

```python
from typing import NamedTuple

import fransys as fr
from fransys.colours import BN


class Io(NamedTuple):
    P1: fr.Device


@fr.unit("power-tap", revision=1, interface_version=1, date="2026-09-26", text="First", by="XX")
def power_tap(u):
    return Io(u.device("P1", "DEMO-CONN-2P", interface=True))


d = fr.design("demo_parts", place="C1")
d.location("C1", "Demo cabinet")
housing = d.device("X10", "DEMO-CONN-2P")
loose = d.device("X11", "DEMO-CONN-2P")
cable = d.cable("W1", "DEMO-CBL-4G1.5", length_m=2)
cable.core(BN, housing[1], loose[1])
d.mate(housing, loose)

supply = d.device("G1", "DEMO-PSU-24")
dc = d.dc_supply("main", supply)
d.wire(dc.plus.pin, housing[1], wire=(BN, 0.75))
d.add(power_tap, "U1")

result = fr.build(d)  # no document: no layout
model = result.model
ids = {item.tag: item.id for item in fr.derive.items(model).values() if item.tag}

(unit_id,) = fr.derive.units(model)
release = fr.derive.unit_release(model, unit_id)
assert release.name == "power-tap"

(boundary_function,) = fr.derive.boundary(model, unit_id)
assert fr.derive.functions(model)[boundary_function].kind is fr.derive.FunctionKind.CONNECTOR

assert fr.derive.port_rails(model, housing[1].id) == frozenset({"24V"})
assert fr.derive.nets(model)
assert len(fr.derive.bom_lines(model)) == 3  # connector, cable, supply
assert len(fr.derive.cable_list_rows(model)) == 1
assert len(fr.derive.contents_rows(fr.derive.top_level_cables(model))) == 1
assert fr.derive.printed_designation(model, ids["X11"]) == "-X11"

cable_part = fr.derive.items(model)[ids["W1"]].part
assert fr.derive.part_rating(model, cable_part).voltage_ac_v == 500
```
