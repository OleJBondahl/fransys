# For coding agents

You are an agent pointed at an installed `fransys` package, looking for its consumer guide.
Find the version you have installed with `importlib.metadata.version("fransys")`. Find the
guide folder that ships inside it with the standard resource-loading call for package data, in
Python:

```
importlib.resources.files("fransys").joinpath("guide")
```

Read `index.md` next.

Import only `fransys`. Every guide example follows that one rule.

For the part-file format itself, see `docs/contracts/part-file.md` in the Fransys
repository, at the tag you pinned.

This file restates no API. The guide pages and the package's own docstrings are the reference.
