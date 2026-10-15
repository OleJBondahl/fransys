# Finding codes: PDF

Codes the PDF output emits. Who acts is explained in [`findings.md`](findings.md).

| Code | Severity | Stage | Who acts | Meaning | Fix |
| --- | --- | --- | --- | --- | --- |
| COVER_OVERFLOW | WARNING | pdf | consumer | A document's cover text plus revision table are estimated taller than the content box. | Shorten the cover or revision text. |
| DOCUMENT_EMPTY_LIST | INFO | pdf | note | A document's list page (PLC, terminal, connector, wire-label, designation, cable or BOM) has no rows and is left out. | Usually nothing to fix (pdf-0019); add records to show it. |
| DOCUMENT_MIXED_SHEET_FORMATS | ERROR | pdf | consumer | A document's pages use more than one sheet format. | Give the document (or its unit/layout profile) one sheet format for all pages. |
| DOCUMENT_NO_DRAWINGS | ERROR | pdf | consumer | A SCHEMATIC page has no drawing set and the document has no other content page, or a HARNESS_DRAWING or BLOCK_DIAGRAM page has no cable or diagram, or a drawing is missing, too large or not drawable yet: interleaved harness cables, or a block diagram whose tallest column is taller than one sheet (a known limit of the system diagram; `DIAGRAM_COLUMN_TOO_TALL` names the column). | Add the missing content, remove the page kind or shorten the texts. |
| DOCUMENT_NO_TOP_LEVEL_CABLES | INFO | pdf | note | A SYSTEM document's HARNESS_DRAWING section has nothing to draw: the model has no top-level cable. | Usually nothing to fix: add a top-level cable if one was expected. |
| DRAWING_SET_REPLICA_ONLY | INFO | pdf | note | A document's drawing set holds only black-box replicas of another unit's boundary. | Usually nothing to fix; add content if a page is intended. |
| MARKDOWN_UNSUPPORTED | ERROR | pdf | consumer | A document's cover or notes text uses a Markdown construct the PDF renderer does not support. | Rewrite it using only the supported Markdown subset. |
| TITLE_BLOCK_NOTICE_OVERFLOW | WARNING | pdf | consumer | The `notice` text passed to `fr.document(notice=)` does not fit the notice cell and would be cut. | Shorten the `notice` text in `fr.document(notice=)`. |
| TITLE_BLOCK_NO_ROOM | WARNING | pdf | consumer | The sheet format's title-block band is under the required 20mm. | Use a sheet format with a taller title-block band. |
| TITLE_BLOCK_TEXT_OVERFLOW | WARNING | pdf | consumer | A one-line title-block field (title, number, customer, revision, date, author, page title, scope or sheet counter) does not fit its cell. | Shorten the text; for a page title, set a shorter one with `d.layout.page_title`. |
| TITLE_BLOCK_UNIT_IDENTITY_MISSING | WARNING | pdf | consumer | A unit document's unit has an empty `title` or `number`, so that title-block cell will print empty. | Give the unit release a `title` and/or `number`. |
