# Finding codes

Every code Fransys can emit, with severity, stage, who acts, meaning and fix, on five pages by source.

A finding's message names each thing as the drawings print it. An item reads as its designation, a port as its port designation, a wire as its ends and a tagged unit as the word unit and its tag, `unit -U1`. A unit with no tag reads as its name and revision alone, as its title block prints them. A thing with no printed text reads as its kind alone. A message never prints a `name=` key or an Id. A renamed key changes no message (decision overview-0003).

"Who acts" is one of four. `consumer`: change your design as the fix says. `part author`: the part library's author fixes the part file as the fix says. `Fransys`: a defect in layout or an output, so send the smallest model that shows it. `note`: nothing is wrong.

- [`findings-validators.md`](../findings-validators/index.md): the model checks, the build, `release`, `verify` and the library load.
- [`findings-render.md`](../findings-render/index.md): layout and the drawing stage.
- [`findings-pdf.md`](../findings-pdf/index.md): the PDF output.
- [`findings-kicad.md`](../findings-kicad/index.md): the KiCad import.
- [`findings-parts.md`](../findings-parts/index.md): the part-file lint.
