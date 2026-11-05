# Keywords of the handle methods and layout hints

This page has one table for each handle method and each `d.layout.*` hint: each named keyword, its default, its effect and an example fragment.
A call that takes only `*args` has no table, and one sentence says what it takes.

The design calls are in `keywords-design.md`, the `fr.*` functions in `keywords-output.md`.
`d.layout.profile` keeps its table in `layout-numbers.md`.

## `Fn.plc`

| keyword | default | effect | example |
|---|---|---|---|
| [`signal`](../authoring/index.md#how-channels-are-numbered) | required | The `fr.SignalType` of the PLC channel this function needs, such as `fr.DI`. It picks the channel kind allocated. | `k1.coil.plc(fr.DO, "pump-run")` |
| [`name`](../authoring/index.md#request-a-plc-channel) | required | The channel's name. It prints in the PLC lists and on the channel's address. | `k1.coil.plc(fr.DO, "pump-run")` |
| `priority` | `0` | A lower number is served first when channels are short. Ties go by the requesting function's key, then its id. | `k1.coil.plc(fr.DO, "pump-run", priority=1)` |

## `Fn.pole`

`fn.pole(n)` takes one pole number, counted from 1 in pole order, and gives that one pole of the function as a series element: `d.series(s1.main.pole(2), f2.element, wire=(BK, 1.5))`.

A pin, or a tuple of one device's pins, is a series element anywhere. First, its pins are the load ends: `d.series(k1.coil["A1"], a1.di_1, wire=(BK, 1.0))` leaves from A1, where `d.series(k1.coil, a1.di_1)` leaves from A2. Last, they are the line ends. In the middle a pin is both: it takes as many pins as its neighbours have poles.

`fn.pins` is the function's pins as a typed tuple in the connector list's order (`1, 2, 10, A1`): `a.pins[i]` is the i-th pin from 0, and a loop over it types as `fr.Pin`.

## `TerminalStrip.run`

| keyword | default | effect | example |
|---|---|---|---|
| [`label`](../authoring/index.md#bridges) | required | The run's label. It prints on each terminal of the run. A run labelled `"PE"` takes the strip's `pe=` part. | `x1.run("24V", 4)` |
| [`count`](../authoring/index.md#bridges) | `None` | The number of terminals in the run. With none, the run is bridged and grows as it is used. | `x1.run("24V", 4)` |
| [`bridged`](../authoring/index.md#bridges) | `False` | Bridges the run's terminals with jumpers: `True` bridges all, `(first, last)` bridges a range. | `x1.run("24V", 4, bridged=True)` |
| [`rail`](../authoring/index.md#power-rails) | `False` | Declares the bridged run a power rail: its terminals draw as the rail's power symbol, not as terminals. A run of one terminal is allowed. | `x1.run("24V", 4, bridged=True, rail=True)` |
| [`interface`](../units/index.md#the-interface) | `False` | Marks the run's terminals as the unit's boundary: `True` marks all, a tuple of terminal numbers marks those. | `x1.run("24V", 4, interface=True)` |
| [`unused`](../units/index.md#the-interface) | `False` | Marks the run's terminals as unused: `True` marks all, a tuple marks those. | `x1.run("SPARE", 2, unused=True)` |

`TerminalStrip.label` is the strip's label as the design printed it (`"X5"`); `Run.label` is the run's own label (`"PE"`). Both are read-only.

## `Cable.core`

Use `d.series` through the cable first: it takes the next free core. Use `core` to choose one core.

| keyword | default | effect | example |
|---|---|---|---|
| [`which`](../detail/index.md#w1core) | required | The core, by colour or by 1-based number. | `w1.core(BN, a, b)` |
| [`a`](../detail/index.md#w1core) | required | The first pin of the core. With no `b`, the core is a shield core. | `w1.core(1, x1[1], m1["U"])` |
| [`b`](../detail/index.md#w1core) | `None` | The second pin of the core. `None` is for a shield core only. | `w1.core(BN, x1[1], m1["U"])` |

## `Cable.spare`

`Cable.spare(*cores, ...)` takes the cores to mark spare, by colour or number. With none, it marks every core not wired or marked so far, so wire first.

| keyword | default | effect | example |
|---|---|---|---|
| `at` | `None` | A pin that parks one spare core. `None` leaves it unparked. An `SH` core refuses it: use `core(which, a)`. | `w1.spare(BK, at=x1[9])` |

## `d.layout.order`

`d.layout.order(*groups)` takes function groups: each neighbour pair is drawn in this order. It has no named keyword. Example: `d.layout.order("pumps", "valves")`.

## Keywords a consumer never passes

- `engine` on `Layout`: the design's engine. `d.layout` builds the layout around it, so you never pass it.
- `pe_mpn` on `TerminalStrip`: the strip's PE terminal part. Pass `pe=` to `d.terminal_strip` instead.
- `rail_group` on `TerminalStrip`: the design's rail declaration. Pass `rail=True` to `run` or `d.terminal_strip` instead.
