# Keywords of the d calls

This page has one table for each `d.*` and `d.detail.*` call: each named keyword, its default, its effect and an example fragment.
A call that takes only `*args` has no table, and one sentence says what it takes.

`place=` is the same on every call that takes it: the `place=` table in `authoring.md` says what it changes.
The `fr.*` functions are in `keywords-output.md`, the handle methods and layout hints in `keywords-handles.md`.

## `d.device`

| keyword | default | effect | example |
|---|---|---|---|
| `tag` | required | The printed tag, bare and with no lowercase letter. `None` numbers the device from its class code and needs `name=`. | `d.device("Q1", P.Q)` |
| `part` | required | A part class or an MPN string. `None` makes an `external=True` box of `pins=`, with a tag and no BOM line. | `d.device("Q1", "DEMO-MCB-3P")` |
| `pins` | `None` | Names the pins of a part-less box (`part=None`). Ignored for a real part. | `d.device("A1", None, pins=("1", "2"), external=True)` |
| `place` | `...` | Where the device stands. See the `place=` table in `authoring.md`. | `d.device("Q1", P.Q, place="HOLD")` |
| `parent` | `None` | The device, strip or cable that holds this one. An accessory prints its holder's designation and uses no number. | `d.device("J1", P.HSG, parent=k1)` |
| `name` | `None` | The key a released number holds to. A floating device, with `tag=None`, raises without it. | `d.device(None, P.Q, name="main-breaker")` |
| `interface` | `False` | Marks the device's functions as the unit's boundary: `True` marks all, a tuple of function names marks those. | `d.device("X1", P.CONN, interface=True)` |
| `unused` | `False` | Marks functions as unused, so no unused-pin finding is raised for them: `True` marks all, a tuple marks those. | `d.device("X1", P.CONN, unused=("x2",))` |
| `mounted_on` | `None` | Mounts the device on a carrier device or function, as a contactor on a protective switch. The carrier's load pins join this device's line pins pole by pole. | `d.device("K1", P.CTR, mounted_on=q1)` |
| `joins` | `None` | Maps the housing's pins to the parent's pins. A housing fitted on a parent's own leads joins them with no wire. Needs `parent=` to be a device. | `d.device("J1", P.HSG, parent=k1, joins={1: k1.coil["A1"]})` |
| `description` | `''` | Text for the designation list in place of the part's description. Empty falls back to the part's. | `d.device("Q1", P.Q, description="Pump breaker")` |
| `position` | `None` | The physical order within the parent, such as the slot of a PLC module or a place on a rail. It orders the rack and the lists. | `d.device("A2", P.DI8, parent=rack, position=2)` |
| `installed` | `True` | `False` keeps the device in drawings and reservations but drops it from the BOM. | `d.device("Q9", P.Q, installed=False)` |
| `external` | `False` | `True` marks the device as supplied by others: no BOM line, and every drawing marks it dashed "(by others)". | `d.device("M1", P.MOTOR, external=True)` |
| `contacts` | `None` | Fits a contact part in every pin of a housing, or a mapping of pin name to part for mixed contacts. | `d.device("P1", P.HSG, parent=w1, contacts="DEMO-CRIMP-M")` |

## `d.terminal_strip`

| keyword | default | effect | example |
|---|---|---|---|
| `tag` | required | The printed tag. `None` numbers the strip and needs `name=`. | `d.terminal_strip("X1", P.TB, 10)` |
| `part` | required | The terminal part. `None` makes part-less terminals with only `.outer`, and needs `external=True`. | `d.terminal_strip("X9", None, external=True)` |
| `count` | `None` | The number of terminals. `X1[3]` takes terminal 3 and makes it on first use. | `d.terminal_strip("X1", P.TB, count=10)` |
| `name` | `None` | The key a released number holds to. A floating strip, with `tag=None`, raises without it. | `d.terminal_strip(None, P.TB, name="field")` |
| `description` | `''` | Text for the strip in the designation list. Empty falls back to the part's. | `d.terminal_strip("X1", P.TB, description="Field strip")` |
| `place` | `...` | Where the strip stands. See the `place=` table in `authoring.md`. | `d.terminal_strip("X1", P.TB, place="HOLD")` |
| `pe` | `None` | The part of the strip's protective-earth terminals. A run labelled `"PE"` takes it, and raises without one. | `d.terminal_strip("X1", P.TB, pe="DEMO-TB-PE-2.5")` |
| `interface` | `False` | Marks terminals as the unit's boundary: `True` marks all, a tuple of terminal numbers marks those. | `d.terminal_strip("X1", P.TB, 4, interface=(1, 2))` |
| `unused` | `False` | Marks terminals as unused: `True` marks all, a tuple of terminal numbers marks those. | `d.terminal_strip("X1", P.TB, 4, unused=(3, 4))` |
| `bridged` | `False` | Bridges plain terminals with jumpers: `True` bridges all, `(first, last)` a range, a tuple of ranges several. | `d.terminal_strip("X4", P.TB, 6, bridged=(2, 6))` |
| `external` | `False` | `True` flags the strip and its terminals as supplied by others. | `d.terminal_strip("X9", P.TB, 4, external=True)` |

## `d.cable`

| keyword | default | effect | example |
|---|---|---|---|
| `tag` | required | The printed tag. `None` numbers the cable and needs `name=`. | `d.cable("W1", P.CBL)` |
| `part` | required | The cable part. Its cores come from the part. | `d.cable("W1", "DEMO-CBL-4G1.5")` |
| `length_m` | `None` | The length in metres, stored as whole millimetres. It prints in the cable list. `None` leaves the length out. | `d.cable("W1", P.CBL, length_m=5)` |
| `place` | `...` | Where the cable stands. See the `place=` table in `authoring.md`. | `d.cable("W1", P.CBL, place="HOLD")` |
| `parent` | `None` | The harness that holds the cable. | `d.cable("W5", P.CBL, parent=h1)` |
| `name` | `None` | The key a released number holds to. A floating cable, with `tag=None`, raises without it. | `d.cable(None, P.CBL, name="motor-cable")` |
| `external` | `False` | `True` flags the cable as supplied by others. Its cores carry no flag. | `d.cable("W1", P.CBL, external=True)` |

## `d.add`

| keyword | default | effect | example |
|---|---|---|---|
| `definition` | required | The unit made by `fr.unit`. The call builds it as an instance and returns the unit function's result. | `u1 = d.add(board, "U1")` |
| `tag` | required | The instance's printed tag, bare and capitals. `None` numbers it from the unit's class code and needs `name=`. | `d.add(board, "U1")` |
| `place` | `...` | Where the instance stands. See the `place=` table in `authoring.md`. | `d.add(board, "U1", place="HOLD")` |
| `name` | `None` | The identity a released number holds to. A floating add raises without it. | `d.add(board, None, name="module1")` |
| `unused` | `()` | Names interface fields or functions the instance leaves unused, such as `"X1"` or `"X1.x1"`. | `d.add(board, "U1", unused=("X1.x1",))` |

## `d.ac_supply`

`d.ac_supply(name, voltage, *phases, ...)` takes the phase pins in phase order as `phases`: one or three.

| keyword | default | effect | example |
|---|---|---|---|
| `name` | required | The supply's name. Its rails are `ac.L1` and so on. | `d.ac_supply("230V", 230, x0[1], n=x0[2])` |
| `voltage` | required | Each phase's RMS voltage to the star point. It is not read from a part. | `d.ac_supply("400V", 400, q1["L1"], q1["L2"], q1["L3"])` |
| `n` | `None` | The neutral pin. A series joins N only where an element has a pole for it. | `n=q1["N"]` |
| `names` | `None` | Renames the potentials: one name per phase pin in order, then one for `n`. The rails keep their `ac.L1` names. | `names=("A", "B", "C")` |
| `earthing` | `fr.EARTHED` | `fr.IT` declares a floating supply. | `earthing=fr.IT` |
| `fault_current_a` | `None` | The prospective fault current in amps, positive. The supply becomes a source for the breaking-capacity check. | `fault_current_a=10000` |

## `d.dc_supply`

| keyword | default | effect | example |
|---|---|---|---|
| `name` | required | The supply's name. Its rails are `dc.plus` and `dc.minus`. | `d.dc_supply("24VDC", psu.output)` |
| `source` | `None` | A device or function whose L+ and L- pins and nominal voltage are the supply. With none, `plus`, `minus` and `voltage` are required. | `d.dc_supply("24VDC", g1.output)` |
| `plus` | `None` | The plus pin, with no `source`. | `plus=x1[1]` |
| `minus` | `None` | The minus pin, with no `source`. | `minus=x1[2]` |
| `mid` | `None` | A middle conductor. With it, `mid` is 0 V and plus and minus are plus and minus the voltage. | `mid=x1[3]` |
| `voltage` | `None` | The voltage, required with no `source` or a source whose part states none. | `voltage=24` |
| `names` | `None` | Renames the potentials, in the order plus, minus, mid. | `names=("P24", "M24")` |
| `earthing` | `fr.EARTHED` | `fr.IT` declares a floating supply. | `earthing=fr.IT` |
| `fault_current_a` | `None` | The prospective fault current in amps, positive. A `source` refuses it, since the part states its own. | `fault_current_a=500` |
| `fault_time_constant_ms` | `None` | The fault time constant in milliseconds, positive. A `source` refuses it. | `fault_time_constant_ms=5` |

## `d.earth`

`d.earth(*pins)` takes the pins to join to protective earth, one `PE` net. It has no named keyword, and a terminal lands on its inner side. Example: `d.earth(x1[3], q1["PE"])`.

## `d.function`

| keyword | default | effect | example |
|---|---|---|---|
| `name` | required | The function block's name, printed `=name`. The devices made inside the `with` block belong to it, which sets their designation; the `d.series` a function is written in sets where it draws. | `with d.function("RUN", "Pump run"):` |
| `text` | required | The block's description. It prints on the pages that draw the block. | `with d.function("RUN", "Pump run"):` |

## `d.location`

| keyword | default | effect | example |
|---|---|---|---|
| `name` | required | The place's bare tag, printed `+name`. | `d.location("HOLD", "Engine hold")` |
| `text` | required | The place's description. | `d.location("HOLD", "Engine hold")` |
| `within` | `None` | The outer place, which must exist. The place then prints `+outer+name`. `None` puts it at the root. | `d.location("BATT", "Batteries", within="HOLD")` |

## `d.harness`

| keyword | default | effect | example |
|---|---|---|---|
| `tag` | `None` | The part-less harness's printed tag. `None` numbers it and needs `name=`. | `d.harness("H1")` |
| `name` | `None` | The key a released number holds to. | `d.harness(None, name="main-loom")` |
| `place` | `...` | Where the harness stands. `None` gives it no place. See the `place=` table in `authoring.md`. | `d.harness("H1", place=None)` |
| `external` | `False` | `True` flags the harness as supplied by others. | `d.harness("H1", external=True)` |

## `d.rack`

| keyword | default | effect | example |
|---|---|---|---|
| `tag` | required | The part-less PLC rack's printed tag. Modules go under it with `parent=`. | `d.rack("U1")` |
| `name` | `None` | The key a released number holds to. | `d.rack("U1", name="plc")` |
| `place` | `...` | Where the rack stands. `None` gives it no place. See the `place=` table in `authoring.md`. | `d.rack("U1", place="HOLD")` |
| `external` | `False` | `True` flags the rack as supplied by others. | `d.rack("U1", external=True)` |

## `d.mate`

| keyword | default | effect | example |
|---|---|---|---|
| `a` | required | The connector to plug in: a device with one function, or that function. | `d.mate(j1, j2)` |
| `b` | required | The connector `a` plugs into. | `d.mate(j1, j2)` |

## `d.series`

`d.series(*elements, ...)` takes the elements to wire end to end, each one's load to the next one's line.

| keyword | default | effect | example |
|---|---|---|---|
| `wire` | `None` | The wire of every pole: a size, a table of rows that replaces only those rows, or one `(colour, size)`. `None` uses the rows' defaults, and a row with no size raises. | `d.series(dc.plus, k1.aux, h1.lamp, dc.minus, wire=(BU, 0.75))` |

## `d.parallel`

`d.parallel(*members)` takes the members to group, so a series puts each between the previous load and the next line. It has no named keyword and connects nothing alone. Example: `d.series(dc.plus, d.parallel(h1.lamp, h2.lamp), dc.minus)`.

## `d.poles`

`d.poles(*functions, ...)` takes one-pole contacts of one device, in pole order, as one element drawn multi-pole. It wires nothing: a series wires the group.

| keyword | default | effect | example |
|---|---|---|---|
| `selector` | `False` | `True` turns a changeover group's throws to the line side, so a series enters at the throws and leaves at the commons, and the group draws turned. `False` keeps the line at the commons. It raises on a part that already states a selector, and on a group that is not changeovers. | `q = d.poles(k1.co_1, k1.co_2, k1.co_3, selector=True)` |

## `d.project`

| keyword | default | effect | example |
|---|---|---|---|
| `title` | required | The project title. It prints in every document's title block. | `d.project(title="Pump", ...)` |
| `number` | required | The drawing number, printed in the title block. | `number="DC-1"` |
| `customer` | required | The customer, printed in the title block. | `customer="Demo Ltd"` |
| `revision` | required | The current revision, an integer from 1. Its date is that of the matching `d.revision` entry. | `revision=2` |
| `author` | required | The author. A project document's Author cell prints it. | `author="AB"` |
| `notice` | `None` | Not accepted: passing it raises `AuthorError`. The notice moved to `fr.document(notice=)`. | `fr.document(preset, None, cover=c, notice="...")` |
| `version` | `1` | The project's release version. `d.revision` without `version=` writes entries of it. Set it before any `d.revision`. | `version=2` |

## `d.revision`

| keyword | default | effect | example |
|---|---|---|---|
| `revision` | required | The revision number of this history entry. | `d.revision(1, date="2026-01-01", text="first", created="AB")` |
| `date` | required | The entry's date. The title block shows it for the current revision. | `date="2026-01-01"` |
| `text` | required | What the revision changed. | `text="first issue"` |
| `created` | required | Who made the revision. | `created="AB"` |
| `checked` | `''` | Who checked it. Empty leaves the field empty. | `checked="CD"` |
| `approved` | `''` | Who approved it. Empty leaves the field empty. | `approved="EF"` |
| `version` | `None` | The version the entry belongs to. `None` takes the project's version, or 1 before `d.project`. | `version=2` |

## `d.rating`

| keyword | default | effect | example |
|---|---|---|---|
| `part` | required | A part class or MPN string. An MPN made by two makers raises. | `d.rating("DEMO-MCB-3P")` |
| `function` | `None` | A function template of the part. `None` reads the part's own rating. | `d.rating("DEMO-MCB-3P", "main")` |

## `d.operating`

| keyword | default | effect | example |
|---|---|---|---|
| `part` | required | A part class or MPN string. An MPN made by two makers raises. | `d.operating("DEMO-PSU-24", "output")` |
| `function` | required | The function template whose operating envelope is read. Returns `None` if the part states none. | `d.operating("DEMO-PSU-24", "output")` |

## `d.draft`

`d.draft()` takes nothing. It returns the records written so far, and it does not freeze them or merge the library: `fr.build` does both.

## `d.detail.wire`

`d.detail.wire(*pins, ...)` takes the pins to wire: two make one wire, more make a daisy chain.

| keyword | default | effect | example |
|---|---|---|---|
| `wire` | required | The wire as `(colour, size)`. | `d.detail.wire(x1[1], h1[1], wire=(BU, 0.75))` |
| `label` | `None` | Text printed on the wire. `None` prints none. | `label="L1"` |
| `n` | `None` | `n=2` draws a second wire in parallel between the same two pins. `None` draws one. | `n=2` |

## `d.detail.net`

`d.detail.net(name, *pins, ...)` takes the pins the net spans as `pins`.

| keyword | default | effect | example |
|---|---|---|---|
| `name` | required | The net's name. It prints on the net in the drawings and the wire list. | `d.detail.net("CAN", a[1], b[1])` |
| `kind` | `fr.CONTROL` | The `NetClass` of the net. It cannot make a `PE` or `POWER` net, which earth and supplies own. | `d.detail.net("CAN", a[1], b[1], kind=fr.SIGNAL)` |

## `d.detail.busbar`

| keyword | default | effect | example |
|---|---|---|---|
| `a` | required | The first pin of the busbar, a conductor of kind `bus`. | `d.detail.busbar(x1[1], x1[2])` |
| `b` | required | The second pin. The same pin twice raises. | `d.detail.busbar(x1[1], x1[2])` |

## `d.detail.rail_bond`

| keyword | default | effect | example |
|---|---|---|---|
| `a` | required | The first pin of the bond, a conductor of kind `rail`. | `d.detail.rail_bond(x1[1], x1[2])` |
| `b` | required | The second pin, of the same rail. The same pin twice raises. | `d.detail.rail_bond(x1[1], x1[2])` |
