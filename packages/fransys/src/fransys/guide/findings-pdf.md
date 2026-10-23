# Finding codes: PDF

> Offline copy. Read the official docs for your version at https://olejbondahl.github.io/fransys/X.Y.Z/ (X.Y.Z is `fransys.__version__`), or https://olejbondahl.github.io/fransys/X.Y.Z/llms.txt. Use this copy only offline.

Codes the PDF output emits. Who acts is explained in [`findings.md`](findings.md).

| Code | Severity | Stage | Who acts | Meaning | Fix |
| --- | --- | --- | --- | --- | --- |
| COVER_OVERFLOW | ERROR | write, release | consumer | A document's cover text plus revision table, measured by Typst at write, are taller than the content box; the write raises and writes nothing. | Shorten the cover file or the revision table of <subject>. Write: fr.document(<preset>, <subject>, cover=<shorter cover file>) |
| DOCUMENT_EMPTY_LIST | INFO | pdf | note | A document's list page (PLC, terminal, connector, wire-label, designation, cable or BOM) has no rows and is left out. | Usually nothing to fix (pdf-0019); add records to show it. |
| DOCUMENT_MIXED_SHEET_FORMATS | ERROR | pdf | consumer | A document's pages use more than one sheet format. | Give <subject> one sheet format for all its pages. Write: [paper] default = "A2" in the settings file, passed as fr.build(settings=fr.settings(path)) |
| DOCUMENT_NO_DRAWINGS | ERROR | pdf | consumer | A SCHEMATIC page has no drawing set and the document has no other content page, or a HARNESS_DRAWING or BLOCK_DIAGRAM page has no cable or diagram, or a drawing is missing, too large or not drawable yet: interleaved harness cables, or a block diagram whose tallest column is taller than one sheet (a known limit of the system diagram; `DIAGRAM_COLUMN_TOO_TALL` names the column). | Add the missing content, shorten the texts, or remove the page kind from <subject>. Write: fr.document(<preset>, <subject>, cover=<cover>, remove=(<page kind>,)) |
| DOCUMENT_NO_TOP_LEVEL_CABLES | INFO | pdf | note | A SYSTEM document's HARNESS_DRAWING section has nothing to draw: the model has no top-level cable. | Usually nothing to fix: add a top-level cable if one was expected. |
| DRAWING_SET_REPLICA_ONLY | INFO | pdf | note | A document's drawing set holds only black-box replicas of another unit's boundary. | Usually nothing to fix; add content if a page is intended. |
| MARKDOWN_UNSUPPORTED | ERROR | pdf | consumer | A document's cover or notes text uses a Markdown construct the PDF renderer does not support. | No call clears this: rewrite the cover or notes text of <subject> using only the supported Markdown subset. |
| TITLE_BLOCK_UNIT_IDENTITY_MISSING | WARNING | pdf | consumer | A unit document's unit has an empty `title` or `number`, so that title-block cell will print empty. | Give the unit release a title and a number. Write: fr.unit(<name>, title=<title>, number=<number>, ...) |
