# Local Validation

Run these commands from `/workspaces/NEET_JEE`.

## Install And Build

```bash
npm install
npm run build
```

The build recreates `dist/` and installs production dependencies there.

## Start The Server

```bash
npm start
```

The default URL is `http://127.0.0.1:5000/`. Use another `PORT` if 5000 is occupied, and point the smoke test at that port only after updating its `BASE_URL`.

## Run Smoke Tests

The existing suite uses Python `requests` and BeautifulSoup, but these are not declared in `requirements.txt`:

```bash
python -m pip install requests beautifulsoup4
python test_app.py
```

The suite checks the portal, NEET and JEE board responses, static files, submission, and dashboard. Also manually verify the relevant new acceptance criteria and inspect generated image URLs.

## Before Push

```bash
git status
git diff --check
git diff
```

Confirm the diff contains only the intended requirement, documentation, tests, and required bank files.