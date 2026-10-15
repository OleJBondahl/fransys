# Keywords of the handle methods and layout hints

This page has one table for each handle method and each `d.layout.*` hint: each named keyword, its default, its effect and an example fragment.
A call that takes only `*args` has no table, and one sentence says what it takes.

The design calls are in `keywords-design.md`, the `fr.*` functions in `keywords-output.md`.
`d.layout.profile` and `d.layout.sheet` keep their tables in `layout-numbers.md`.

## `Fn.plc`

| keyword | default | effect | example |
|---|---|---|---|
| `signal` | required | The `fr.SignalType` of the PLC channel this function needs, such as `fr.DI`. It picks the channel kind allocated. | `k1.coil.plc(fr.DO, "pump-run")` |
| `name` | required | The channel's name. It prints in the PLC lists and on the channel's address. | `k1.coil.plc(fr.DO, "pump-run")` |
| `priority` | `0` | A lower number is served first when channels are short. Ties go by the requesting function's key, then its id. | `k1.coil.plc(fr.DO, "pump-run", priority=1)` |

## `Fn.scale`

| keyword | default | effect | example |
|---|---|---|---|
| `unit` | required | The engineering unit of the scaled value. It prints in the PLC list. | `ai.scale("bar", (0, 27648), (0, 10))` |
| `raw` | required | The raw range as two integers. | `raw=(0, 27648)` |
| `eng` | required | The engineering range as two strings or Decimals. Floats are refused. | `eng=("0", "10")` |

## `Fn.limits`

| keyword | default | effect | example |
|---|---|---|---|
| `rating` | `None` | The rating the unit states about this boundary function. `None` states none. | `q1.line.limits(rating=r)` |
| `operating` | `None` | The operating envelope the unit states about this boundary function. `None` states none. | `q1.line.limits(operating=o)` |

## `Terminal.limits`

| keyword | default | effect | example |
|---|---|---|---|
| `rating` | `None` | The rating the unit states about this terminal. `None` states none. The terminal must be in a unit. | `x1[1].limits(rating=r)` |
| `operating` | `None` | The operating envelope the unit states about this terminal. `None` states none. Giving neither value raises. | `x1[1].limits(operating=o)` |

## `TerminalStrip.run`

| keyword | default | effect | example |
|---|---|---|---|
| `label` | required | The run's label. It prints on each terminal of the run. A run labelled `"PE"` takes the strip's `pe=` part. | `x1.run("24V", 4)` |
| `count` | `None` | The number of terminals in the run. With none, the run is bridged and grows as it is used. | `x1.run("24V", 4)` |
| `bridged` | `False` | Bridges the run's terminals with jumpers: `True` bridges all, `(first, last)` bridges a range. | `x1.run("24V", 4, bridged=True)` |
| `interface` | `False` | Marks the run's terminals as the unit's boundary: `True` marks all, a tuple of terminal numbers marks those. | `x1.run("24V", 4, interface=True)` |
| `unused` | `False` | Marks the run's terminals as unused: `True` marks all, a tuple marks those. | `x1.run("SPARE", 2, unused=True)` |

## `Cable.core`

Use `d.series` through the cable first: it takes the next free core. Use `core` to choose one core.

| keyword | default | effect | example |
|---|---|---|---|
| `which` | required | The core, by colour or by 1-based number. | `w1.core(BN, a, b)` |
| `a` | required | The first pin of the core. With no `b`, the core is a shield core. | `w1.core(1, x1[1], m1["U"])` |
| `b` | `None` | The second pin of the core. `None` is for a shield core only. | `w1.core(BN, x1[1], m1["U"])` |

## `Cable.spare`

`Cable.spare(*cores, ...)` takes the cores to mark spare, by colour or number. With none, it marks every core not wired or marked so far, so wire first.

| keyword | default | effect | example |
|---|---|---|---|
| `at` | `None` | A pin that parks one spare core. `None` leaves it unparked. An `SH` core refuses it: use `core(which, a)`. | `w1.spare(BK, at=x1[9])` |

## `d.layout.break_before`

| keyword | default | effect | example |
|---|---|---|---|
| `group` | required | The function group that starts a new page. | `d.layout.break_before("pumps")` |

## `d.layout.chain`

`d.layout.chain(*functions, ...)` takes the functions to draw as one current path, source first.

| keyword | default | effect | example |
|---|---|---|---|
| `beside` | `None` | A host function: the chain is drawn next to it, joined at each end net it shares. It raises `AuthorError` when no end net is the host's. `None` draws the chain alone. | `d.layout.chain(a, b, beside=c)` |

## `d.layout.draw_in`

| keyword | default | effect | example |
|---|---|---|---|
| `function` | required | The function or device to draw in the group, whatever its device's place says. | `d.layout.draw_in(run, "pumps")` |
| `group` | required | The function group whose pages draw it. | `d.layout.draw_in(run, "pumps")` |

## `d.layout.keep_together`

`d.layout.keep_together(*groups)` takes the function groups that share a page when they fit. It has no named keyword. Example: `d.layout.keep_together("pumps", "valves")`.

## `d.layout.order`

`d.layout.order(*groups)` takes function groups: each neighbour pair is drawn in this order. It has no named keyword. Example: `d.layout.order("pumps", "valves")`.

## `d.layout.page_title`

| keyword | default | effect | example |
|---|---|---|---|
| `thing` | required | The group, function, device, strip or nested unit (what `d.add` returned) whose drawing pages get the title. One thing takes one title. | `d.layout.page_title("pumps", "Pump circuits")` |
| `text` | required | The title text. The page prints it before its blocks' texts. Empty raises `AuthorError`. | `d.layout.page_title("pumps", "Pump circuits")` |

## `d.layout.side`

| keyword | default | effect | example |
|---|---|---|---|
| `target` | required | A field of a unit's interface, as `u1.bus_in`. An interface with no harness line ignores it. | `d.layout.side(f1, fr.ABOVE)` |
| `side` | required | `fr.ABOVE` or `fr.BELOW`: the edge the interface stands on. | `d.layout.side(f1, fr.BELOW)` |

## `d.layout.symbol`

| keyword | default | effect | example |
|---|---|---|---|
| `target` | required | A function, a device, or a `FunctionKind` such as `FunctionKind.X`, passed as a name. A string raises. | `d.layout.symbol(P.Q, "breaker")` |
| `symbol` | required | The library symbol to draw. | `d.layout.symbol(P.Q, "breaker")` |
| `port_map` | `None` | Maps a model port name to a symbol port name where they differ. A port not listed keeps its name. | `port_map={"13": "1.in"}` |

## Keywords a consumer never passes

- `engine` on `Layout`: the design's engine. `d.layout` builds the layout around it, so you never pass it.
- `pe_mpn` on `TerminalStrip`: the strip's PE terminal part. Pass `pe=` to `d.terminal_strip` instead.
