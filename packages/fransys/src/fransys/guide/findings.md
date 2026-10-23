# Finding codes

> Offline copy. Read the official docs for your version at https://olejbondahl.github.io/fransys/X.Y.Z/ (X.Y.Z is `fransys.__version__`), or https://olejbondahl.github.io/fransys/X.Y.Z/llms.txt. Use this copy only offline.

Every code Fransys can emit, with severity, stage, who acts, meaning and fix, on five pages by source.

A finding's message names each thing as the drawings print it. An item reads as its designation, a port as its port designation, a wire as its ends and a tagged unit as the word unit and its tag, `unit -U1`. A unit with no tag reads as its name and revision alone, as its title block prints them. A thing with no printed text reads as its kind alone. A message never prints a `name=` key or an Id. A renamed key changes no message (decision overview-0003).

"Who acts" is one of four. `consumer`: change your design as the fix says. `part author`: the part library's author fixes the part file as the fix says. `Fransys`: a defect in layout or an output, so send the smallest model that shows it. `note`: nothing is wrong.

Every `Finding` row carries its own `fix`: `<valid values>. Write: <corrected call>`, filled with that finding's names and values. A test reads `exc.findings` (from `BuildErrors`) or `fr.check(result)` and finds the template: `<subject>` and `<other>` stand for the finding's first and second subject. `fr.report` and the `BuildErrors` message print them filled with those subjects' names. A code no call clears starts with `No call clears this:`. The worked example is in `build.md`, under "write".

- [`findings-validators.md`](findings-validators.md): the model checks and the library load.
- [`findings-release.md`](findings-release.md): the build, `release`, `verify` and the baseline check.
- [`findings-render.md`](findings-render.md): layout and the drawing stage.
- [`findings-pdf.md`](findings-pdf.md): the PDF output.
- [`findings-kicad.md`](findings-kicad.md): the KiCad import.
- [`findings-parts.md`](findings-parts.md): the part-file lint.
