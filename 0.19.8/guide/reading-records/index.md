# Reading: records, lookups and ratings

This page covers the records that describe a model's structure, the lookups that find them,
and the ratings and currents that say what a circuit may carry. Each record type has a
table function that returns every record of that type, keyed by id. Every name here is
reached as `fr.derive.NAME`.

## Records

- `Aspect` is one of the three IEC 81346 views of the same objects: `FUNCTION`, `PRODUCT` and `LOCATION`.
- `AspectNode` is a node in one aspect tree. Its fields are `id`, `key`, `aspect`, `parent` (an `AspectNode` id, or `None` at the root), `label`, `description` and `ext`. A `LOCATION` node with label `C1` is the place `+C1`. The table is `aspect_nodes`.
- `Placement` puts one item at one aspect node. Its fields are `id`, `key`, `item`, `node` and `ext`. An item has at most one placement per aspect, so one item can have a product placement and a location placement. The table is `placements`.
- `Boundary` marks a function as part of a unit's interface. Its fields are `id`, `key`, `unit`, `function`, `name` and `ext`. `name` is the field name the unit gave the function, or `None`. One function can be the boundary of several units. The table is `boundaries`.
- `Port` is a connection point on a function. Its fields are `id`, `key`, `function`, `template`, `name`, `role`, `marking` and `ext`. `template` is `None` for a port without a part template. The `marking` field is the pin text printed on the drawing: `None` prints the port's name, an empty string prints nothing, and any other string prints as given.
- `PortRole` says what a port is for. Its members are `GENERIC`, `INTERNAL`, `EXTERNAL`, `PE`, `COMMON`, `BREAK` and `MAKE`. A terminal's two ports are `INTERNAL` (panel side) and `EXTERNAL` (field cable side). A contact's ports are `COMMON`, `BREAK` (closed at rest) or `MAKE` (closed when operated).
- `Conductor` is a physical connection with exactly two ends. Its fields are `id`, `key`, `a`, `b`, `kind`, `carrier` (the item that carries it, or `None`) and `ext`. `a` and `b` are stored in id order, so they do not say a direction. The table is `conductors`.
- `ConductorKind` says what realises a conductor. Its members are `WIRE`, `CORE`, `JUMPER`, `BUSBAR`, `MOUNT`, `RAIL` and `LEAD`. `MOUNT`, `BUSBAR`, `RAIL` and `LEAD` are links: they close a net and are never wires.
- `PhysicalNet` is one net found from real connectivity: a maximal set of ports joined by conductors. Its only field is `ports`, sorted by id. It differs from a declared net, which is the intent the author wrote. Two closures over the same wiring compare equal.
- `NetClass` says what kind of potential or signal a `Net` carries. Its members are `POWER`, `CONTROL`, `SIGNAL`, `PE` and `GENERIC`. A 24 V supply rail is `POWER`; a 4-20 mA transmitter loop is `SIGNAL`. Read it as `net.net_class` on a row of `fr.derive.nets`.

## Lookups

- `aspect_nodes(model)` returns every `AspectNode`, keyed by id. It is the model's own table, not a copy, and it is empty when the model has none.
- `placements(model)` returns every `Placement`, keyed by id, in the same way.
- `boundaries(model)` returns every `Boundary`, keyed by id, in the same way.
- `conductors(model)` returns every `Conductor`, keyed by id, in the same way.
- `item_location(model, item)` returns the id of the `LOCATION` node the item is placed at. It uses the item's own placement, or the nearest placed ancestor's. It returns `None` when there is none. It raises `SchemaError` when `item` is not an item of the model.
- `items_at(model, node)` returns the ids of every item at `node` or at any node below it, once each and sorted by id. An item counts by its own placement, or by its nearest placed ancestor's. It raises `SchemaError` when `node` is not an aspect node of the model.
- `effective_placement(model, item, aspect)` returns the id of the `AspectNode` where `item` sits in `aspect`: its own placement, else its nearest placed ancestor's, else `None`. It walks `Item.parent` and stops on a cycle. A tie in one aspect resolves to the smallest placement id. It raises `SchemaError` when `item` is not an item of the model. Use it when you need one aspect's node; `item_location` is its `LOCATION` case.
- `subtree` takes a model and a node. It returns the ids of every descendant of `node`, following `parent`, with `node` itself left out. The result is sorted by id. It follows `parent` in any aspect and stops on a cycle. It raises `SchemaError` when `node` is not an aspect node.
- `net_of` takes a model and a port. It returns the `PhysicalNet` that contains the port. It returns `None` when the port is not a port of the model.
- `revision_history` takes a model and an optional release. It returns the `Revision` records of a release, in date order, then by version and revision as numbers, so revision 2 comes before revision 10. With `release=None` it returns the project's own history. It raises `SchemaError` when `release` is not `None` and is not a release of the model.

Use `item_location` when a list needs an item's place and the place may be inherited. Use `items_at` when you need everything in a cabinet or on a board, including the items under it.

## Ratings and currents

- `Rating` says what a function or a part is rated for. Its fields are `voltage_ac_v`, `voltage_dc_v`, `current_ac_a`, `current_dc_a`, `min_breaking_current_a`, `power_loss_w`, `breaking_ac` and `breaking_dc`. A field is `None` when the datasheet gives no value. AC voltages are RMS, and DC voltages are the highest permissible potential. Currents are continuous ratings, except `min_breaking_current_a`, which is the lowest current a partial-range fuse breaks. The model checks the types only; comparing a rating with the plant is a check's job.
- `CurrentPosition` is one rated current path. Its fields are `functions` (sorted), `bounds` and `ports`. `bounds` holds at most one `CurrentBound` per current kind, AC before DC. `ports` are the two end ports of the path, and they tell apart paths that pass through the same functions, one per pole.
- `CurrentChain` is a block of the current graph. Its only field is `positions`, in the order that the chain lists them. The graph treats every switched link as closed. A position that exists only in some switch state is a chain on its own.
- `LimitRole` says what set a bound. Its members are `SOURCE`, a source's continuous limit, and `PROTECTION`, a full-range protective device.
- `port_potential_current` takes a model and a port. It returns the current kind, `AC` or `DC`, of the supply behind the port's potential. It returns `None` when the port has no potential rank, and it always returns `None` for protective earth, which belongs to no supply.
