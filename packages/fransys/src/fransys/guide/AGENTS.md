# For coding agents

> Offline copy. Read the official docs for your version at https://olejbondahl.github.io/fransys/X.Y.Z/ (X.Y.Z is `fransys.__version__`), or https://olejbondahl.github.io/fransys/X.Y.Z/llms.txt. Use this copy only offline.

The official Fransys documentation is the site, one version per release. Read it there, never in the
installed package folder (`site-packages/fransys/`). Paste this block into your project's
`CLAUDE.md` or `AGENTS.md` so every agent that works on the project finds it:

```markdown
## Fransys documentation

- The official documentation is https://olejbondahl.github.io/fransys/ .
- Take the version from the installed package: `importlib.metadata.version("fransys")` is `X.Y.Z`.
- Start at https://olejbondahl.github.io/fransys/X.Y.Z/llms.txt. Its `llms-full.txt` is the whole guide in one file.
- Read a page as Markdown at its URL plus `index.md`, such as https://olejbondahl.github.io/fransys/X.Y.Z/guide/index.md.
- Import only `fransys`. Write with the calls the guide index names under "Which call first".
- Do not read `site-packages/fransys/`. Its guide is an offline fallback for when the site is unreachable.
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
