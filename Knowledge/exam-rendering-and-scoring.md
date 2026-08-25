# Exam Rendering And Scoring

## Rendering

`POST /unified-test-board` selects banks for the requested stream and calls `renderUnifiedExamPanel`.

- NEET shows Physics, Chemistry, and Biology.
- JEE shows Physics, Chemistry, and Mathematics.
- A subject with no matching bank displays a missing or unreadable DOCX message.
- Questions with options render as radio-button MCQs.
- JEE questions with no options render as type-in fields.
- MathJax is loaded for mathematical markup.

## Scoring

**Current behavior:** MCQ answers receive `+4` when correct, `-1` when wrong, and `0` when unanswered. JEE type-in questions receive `+4` when `typeinAnswersMatch` accepts the answer and `0` otherwise. Numeric comparison accepts equivalent numeric and fraction forms within a small tolerance.

The submit route reloads DOCX files, scores against the server-side parsed answers, builds a detailed report, and stores the summary in `performanceDb`.

## Timer

**Known limitation:** The visible timer says `03:00:00`, while the client-side countdown is initialized to 10 minutes. The submit button is locked until the configured threshold and expiry triggers automatic submission. Reconcile the displayed text and actual timing through an explicit requirement before changing either.

## Results

Results are rendered immediately, stored in process memory by student name, displayed by `/dashboard`, and exported by `/download-excel`.

**Expected contract:** Any change to scoring, answer matching, subject visibility, or timing should include a local submission check and acceptance criteria for unanswered, wrong, correct, MCQ, and numeric answers.

**Known limitation:** The displayed JEE “last five questions” rule is not independently enforced as a server-side policy in the current submit logic.