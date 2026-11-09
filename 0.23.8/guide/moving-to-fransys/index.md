# Moving to Fransys

This page lists every change a script written for version 0.6.1 under the old name must make for Fransys 0.7.0.
Each entry gives the old spelling, the new one and one line of why.
The old spellings sit in text blocks: they no longer run.

## Import and alias

```text
import schematika as sk
from schematika.colours import BU
```

```python
import fransys as fr
from fransys.colours import BU

d = fr.design("demo_parts")
d.device("Q1", "DEMO-RLY-2CO-24")
model = fr.build(d)
```

Every `sk.` call becomes `fr.` with the same name and arguments. The distribution and the import
name are both `fransys` now, so no `schematika` module remains.

## The pin line

```text
schematika @ git+<the old repository>@v0.6.1#subdirectory=packages/schematika
```

```text
fransys @ git+https://github.com/OleJBondahl/fransys@v0.7.0#subdirectory=packages/fransys
```

Pin the exact tag, as before. The repository is the public one, and the subdirectory is the
`fransys` package.

## The parts module command

| old | new |
|---|---|
| `python -m schematika parts-module` | `python -m fransys parts-module` |

The arguments are the same. Regenerate the parts module with the new command, then rebuild.
The generated file records the library's digest, which the rename does not change.

## The intermediates folder

| old | new |
|---|---|
| `.schematika/` | `.fransys/` |

Per-page SVGs and other intermediates go to `.fransys/`. Replace the `.schematika/` line in your
`.gitignore` with this one.

```text
.fransys/
```

Stored baselines verify unchanged: the rename moves no listing text.
