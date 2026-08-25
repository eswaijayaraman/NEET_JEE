# Repository Architecture

## Active Application

**Current behavior:** The active runtime is the Node.js/Express application in `app.js`. It serves `/`, loads exams through `POST /unified-test-board`, submits through `POST /submit-unified-exam`, exposes `/dashboard` and `/download-excel`, and serves media from `/static`.

`getSubjectFile`, `loadQuestionsFromDocx`, `renderUnifiedExamPanel`, and the submit route are the main ownership points for question-bank and exam changes.

## Question Banks And Media

Root `.docx` files are discovered at runtime. Extracted images are written to `static/` with generated filenames. The current repository contains NEET Biology, Chemistry, and Physics banks and a JEE Physics bank; JEE Chemistry and Mathematics banks are not currently present.

## Legacy Reference

`sixth-app.py` is a separate Flask implementation using `python-docx`. It is not the package entry point and is not referenced by the Node scripts or README. Do not modify it for a Node application requirement unless the requirement explicitly includes the Flask implementation.

## Build Output

`build.js` creates `dist/` from scratch and copies the Node runtime files, root DOCX files, and `static/`. Knowledge and SDLC documentation are repository guidance and are not copied into the runtime artifact.

## Known Limitations

- Assessment results live only in Node process memory and disappear on restart.
- Dashboard and CSV routes have no authentication in the current implementation.
- User names and parsed content are interpolated into generated HTML and need security review before broad exposure.
- Catalyst script references exist, but no Catalyst SDK dependency or deployment configuration is present in this repository.