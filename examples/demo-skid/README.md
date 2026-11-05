# Demo skid

A cabinet design of a small plant skid, drawn from `examples/demo-parts` only: a 3-pole mains
breaker feeding a terminal strip, three fan starters, a PLC, and sixteen valve relays behind one
breaker whose contacts read back into a digital input module. Every part, name and value is invented.

`skid.py` has one unit, `skid`, and `design()`, which adds the unit as `U1` to a cabinet design and returns it with its cabinet document, so every tag prints under `U1`. It is
written as a consumer writes: `import fransys as fr`, `d.series` for the current paths, and
`d.series` for the jumpers between strip rows too (three per row after the first: six at M=3). It imports no `fransys_*` package
(`tests/test_demo_skid_imports.py`). `VALVES` and `STARTERS` set the size.

```python
import importlib.util

import fransys as fr

spec = importlib.util.spec_from_file_location("skid", "examples/demo-skid/skid.py")
skid = importlib.util.module_from_spec(spec)
spec.loader.exec_module(skid)
design, document = skid.design()
result = fr.build(fr.parts("demo_parts"), design, document)
```

The readability counts of its pages are held by `tests/test_demo_skid_ratchet.py`: a count may
fall and never rise. It has no byte golden, since its drawings are meant to change.
