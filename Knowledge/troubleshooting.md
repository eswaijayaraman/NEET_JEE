# Troubleshooting

## Empty Subject Section

Check that the DOCX is in the repository root and its filename contains both subject and stream tokens, for example `Mathematics-JEE.docx`. Confirm the file is included in `dist/` after `npm run build`.

## Questions Missing Or Incomplete

Check that questions, options, and answers are separate paragraphs. Confirm question numbering matches `Q1.`, `1)`, or another accepted form, options begin with A-D, and answers use a supported form.

## Images Missing

Check that the image is embedded in the DOCX, that the application can write to `static/`, and that the generated `/static/...` URL returns HTTP 200. Browser support for unusual formats such as EMF is not guaranteed.

## Local Test Failure

Confirm the server is running on port 5000, then install the smoke-test dependencies if needed:

```bash
python -m pip install requests beautifulsoup4
```

Run `python test_app.py` from the repository root. These Python dependencies are not currently listed in `requirements.txt`.

## Build Failure

Run `npm install` from the repository root and inspect whether `dist/` is writable. Remember that the build removes and recreates `dist/`.

## Deployment Failure

Check the Render deploy log for the build and start command, confirm the required DOCX and static files are present, then test `/`, `/unified-test-board`, `/submit-unified-exam`, `/dashboard`, and `/download-excel` against the deployed URL.