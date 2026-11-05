# The required-drawn ledger

> Offline copy. Read the official docs for your version at https://olejbondahl.github.io/fransys/X.Y.Z/ (X.Y.Z is `fransys.__version__`), or https://olejbondahl.github.io/fransys/X.Y.Z/llms.txt. Use this copy only offline.

`fr.derive.required_drawn` lists what a drawing of a model must show: both ends of each conductor, and each function that gets a symbol. Each row is drawn, carried by a named reason, or an error.

## Rows

`required_drawn(model, scope)` takes the model and the ports whose conductors count. It returns a tuple of rows.

- `ConductorEnd(conductor, port, far)`: the conductor leaves `port` and reaches `far`. A conductor between two ports of the scope gives two rows.
- `FunctionSymbol(function)`: a function the schematic draws as a symbol. An accessory declared open on purpose is not listed.

`Required` names either row type. The end rows come first, lowest far port first; the function rows follow in id order.

A port the model does not hold raises `SchemaError`. Pass the port ids of the same model.

## Carried

`Carried(reason, end=, symbol=)` says a row stands undrawn on purpose. Exactly one of `end` and `symbol` is set. `CarriedReason` is a closed list: `SPARE`, `UNWIRED` and `OFF_DOCUMENT`.

## Example

```python
import fransys as fr

d = fr.design("demo_parts")
dc = d.dc_supply("24VDC", d.device("G1", "DEMO-PSU-24"))
k1 = d.device("K1", "DEMO-RLY-2CO-24")
k2 = d.device("K2", "DEMO-CTR-3P-24")
d.series(dc.plus, k1.co_1.no, k2.coil, dc.minus, wire=0.75)
model = fr.build(d).model
rows = fr.derive.required_drawn(model, tuple(fr.derive.ports(model)))
ends = [r for r in rows if isinstance(r, fr.derive.ConductorEnd)]
assert ends
assert len(ends) % 2 == 0  # two rows per conductor
```
