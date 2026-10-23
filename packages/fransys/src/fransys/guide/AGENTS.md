# For coding agents

> Offline copy. Read the official docs for your version at https://olejbondahl.github.io/fransys/X.Y.Z/ (X.Y.Z is `fransys.__version__`), or https://olejbondahl.github.io/fransys/X.Y.Z/llms.txt. Use this copy only offline.

The official Fransys documentation is the site, one version per release. Paste this block into
your project's `CLAUDE.md` or `AGENTS.md` so every agent that works on the project finds it:

```markdown
## Fransys documentation
- Official docs for the installed version: https://olejbondahl.github.io/fransys/X.Y.Z/llms.txt, where X.Y.Z is `importlib.metadata.version("fransys")`.
- Look a public name or a finding code up with `python -m fransys help KEY`: it prints the signature, the docstring and the guide page.
- Import only `fransys`. Write with the calls the guide index names under "Which call first".
- Offline only: the installed guide is `importlib.resources.files("fransys").joinpath("guide")`; start at `index.md`.
```

The part-file format is in
[the part-file contract](https://olejbondahl.github.io/fransys/X.Y.Z/contracts/part-file/index.md), at the same version path.
For type checking a design script, read [Type checking](keywords.md#type-checking).

## Offline fallback

Without network access the guide ships inside the installed package. Find the version you have
installed with `importlib.metadata.version("fransys")`. Find the guide folder with the standard
resource-loading call for package data, in Python:

```
importlib.resources.files("fransys").joinpath("guide")
```

Read `index.md` next. This file restates no API. The guide pages and the package's own docstrings
are the reference.
