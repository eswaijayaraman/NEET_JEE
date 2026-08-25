# Word Document Authoring Contract

## Filename

**Expected contract:** Save each bank in the application root with a name containing both subject and stream tokens:

```text
<subject>-<stream>.docx
```

Examples include `Biology-neet.docx`, `Chemistry-neet.docx`, and `Physics-JEE.docx`. Matching is case-insensitive. Temporary Word lock files beginning with `~$` are ignored.

Supported subject tokens are Physics, Chemistry, Mathematics, and Biology. Supported stream tokens are NEET and JEE.

## Paragraph Format

The parser reads paragraph elements produced by Mammoth. Put each question, option, and answer on its own Word paragraph.

```text
Q1. A projectile is launched with initial velocity u.
(A) Option one
(B) Option two
(C) Option three
(D) Option four
Correct answer: B
```

Question numbering may be `1.`, `Q1.`, `1)`, `Q1)`, `1:`, or `Q1:` followed by whitespace. Options must begin with A-D and may use parentheses, brackets, braces, or a period.

Accepted answer forms include `Correct answer: B`, `Answer: B`, `[B]`, and a standalone `(B)` paragraph. Use a single letter for MCQ answers.

## Images And Mathematics

Insert images in a question paragraph or in a blank paragraph immediately associated with the question. Mammoth converts embedded images and the application writes them under `static/`; the question stores an image URL in its HTML.

Use plain text for ordinary notation. Backslash LaTeX can be wrapped for MathJax. The application also applies custom formatting for logarithms, exponents, units, chemical subscripts, ion charges, and vector notation.

## Constraints

- Keep question, option, and answer content at paragraph level; tables and headers are not part of the verified contract.
- Keep option labels in A-D order because the UI assigns answer letters by option position.
- Ensure every question has an answer line if it is intended to be scored.
- For JEE numerical questions, omit option paragraphs and provide a numeric answer value.
- Avoid relying on rich Word formatting as semantic input; the parser primarily uses paragraph text and embedded images.

**Known limitation:** There is no schema validator or authoring template in the repository. Test a new bank locally before publishing it.