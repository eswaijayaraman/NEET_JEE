# Development

## Start With A Branch

```bash
git switch main
git pull origin main
git switch -c <short-requirement-name>
```

Use a focused branch name tied to the requirement. Never begin requirement work directly on `main`.

## Implement

1. Identify the owning function or route using the Knowledge references.
2. Make the smallest change that satisfies the acceptance criteria.
3. Preserve existing DOCX filename and paragraph contracts unless the requirement changes them explicitly.
4. Update the relevant Knowledge or SDLC reference when behavior or workflow changes.
5. Add or update focused tests and fixtures when the change affects parsing, scoring, or endpoints.
6. Keep generated output and unrelated working-tree changes out of the commit unless required by repository policy.

For question-bank work, validate the document locally before changing parser code. For parser or scoring work, test both the normal path and malformed or missing input.