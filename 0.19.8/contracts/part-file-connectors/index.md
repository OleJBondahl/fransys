# Part-file contract: connectors

This page holds the `[function.connector]` table of the part-file contract. It is read with `part-file.md`, which holds the rest of the contract.

### `[function.connector]`

A sub-table of the `[[function]]` entry it describes (P1): the `connector` facet's subject is a
`FunctionTemplate`, not the `Part`, so a part with more than one connector-style function names
each one under its own `[[function]]` entry, never in one top-level table. Maps to the model's
`connector` facet.

```toml
[[function]]
name = "x1"
kind = "connector"
symbol = "connector-fixed"
ports = [{ name = "1", role = "generic", symbol_port = "in" }, { name = "2", role = "generic", symbol_port = "out" }]

[function.connector]
style = "header-2p"
pincount = 2
gender = "male"
```

| Field | Type | Meaning |
|---|---|---|
| `style` | string | |
| `pincount` | integer | At least 1 |
| `gender` | string | Optional. A `Gender` value: `"male"`, `"female"`, `"neutral"`. Absent means not stated, which is not `neutral` (model-0080) |
| `marking` | string | Optional. The label printed on the part, e.g. `"X1"`. Omit it to print the function's name; write `""` for no label, and the connector's pins print under the item |
| `mates` | list of strings | Optional. The MPNs of the parts this connector mates with, e.g. `["DEMO-HSG-4M"]`. Data only: no check reads it yet (parts-0016) |

Port names are unique within a function. Two functions of one part may share a port name unless
they would print one designation (`PORT_NAME_SHARED`, parts-0005): a labelled connector function
(its `marking`, else its name; `marking = ""` is no label) prints `-<label>` behind the item's
designation only when the part has two or more labelled connector functions, so `X1:1` and
`X2:1` differ, and so do a clamp group's `1` and `X1:1`, while a clamp group and a lone labelled
connector sharing `1` collide. The lint and the build ask the same segment rule
(`derive.connector_segments`). Two connectors of one part never print one label
(`CONNECTOR_MARKING_REUSED`). A pin prints as `-<item>-<label>:<pin>`, e.g. `-A1-X1:1` (decisions parts-0003, model-0071).

### A header pin that joins a function port

A port of a connector function may carry `joins = "<function>.<port>"`. It names a port of another function of the same part (parts-0017).

```toml
{ name = "1", role = "generic", symbol_port = "in", joins = "k1.A1" }
```

The header ports are named by position, `"1"` to `"n"`, and the printed pin text goes in `marking`. The join is stored once, on the header port's template. It is a connection with no conductor: net closure puts both ports on one net.

Three lints, all `ERROR`:
- `JOIN_PORT_UNKNOWN`: the target is no port of the part, or the value is malformed.
- `JOIN_INTO_CONNECTOR`: the target is a port of a connector function.
- `JOIN_PORT_TWICE`: one function port is joined by two header pins.

A header position that repeats another function's port name is `PORT_NAME_SHARED`.

### A contact part

A crimp contact is a part file with a `[part]` table and no `[[function]]`, as a fuse link is
(`DEMO-CRIMP-F`, `DEMO-CRIMP-M`). A design fits it with `contacts=` on a connector item
(`guide/harnesses.md`); the BOM counts it once per used pin (model-0170). It has no family or gauge
field yet.
