# Word Document Parsing

## File Selection

`getSubjectFile(subject, stream)` scans only the application directory for `.docx` files. It selects the first file whose lowercase name contains the subject token and stream token. No file match returns `null`, which becomes an empty subject section.

## Conversion Pipeline

`loadQuestionsFromDocx(filePath)` performs this sequence:

1. Return an empty list if the path is missing or does not exist.
2. Convert the DOCX to HTML with Mammoth.
3. Convert embedded images to files in `static/` and replace them with `/static/<generated-file>` URLs.
4. Parse only `<p>` elements with Cheerio.
5. Detect question, option, and answer paragraphs using regular expressions.
6. Group paragraphs into records and flush the final question.
7. Apply `formatLogSubscripts` to question and option text.

Each parsed record has this shape:

```js
{
  id: 1,
  question: "...",
  options: ["...", "..."],
  correct: "B"
}
```

## Grouping Rules

- A new question flushes the previous record.
- A-D-shaped paragraphs become options.
- Recognized answer paragraphs set `correct`.
- Other non-empty paragraphs before the first option are appended to the question with `<br>`.
- A paragraph containing an image is added to the current question; a blank image paragraph can start a question when no question is active.

**Known limitation:** The parser has no explicit error report for malformed documents. Unsupported structures can silently produce empty or incomplete records.

## Formatting

`formatLogSubscripts` protects existing HTML tags, wraps raw backslash LaTeX, adds vector marks, converts selected notation to `<sup>` and `<sub>`, removes carets, and restores tags. This is presentation normalization, not a general mathematical parser.

When changing parsing or formatting, test question numbering, all answer forms, multiline text, images, LaTeX, units, chemical formulas, and JEE numeric answers.