---
name: neet-jee-product-knowledge
description: "Use when adding or changing NEET/JEE question banks, DOCX files, parsing, exam rendering, scoring, builds, deployment, or troubleshooting this assessment portal."
argument-hint: "Describe the product area or change you need to understand"
---

# NEET/JEE Product Knowledge

Use this skill before changing the application or adding a Word question bank. Start with the relevant reference below, then verify behavior against `app.js`, `build.js`, and the local smoke tests.

## Index

- [Repository architecture](./repository-architecture.md)
- [Word document authoring contract](./word-document-authoring.md)
- [Word document parsing](./word-document-parsing.md)
- [Exam rendering and scoring](./exam-rendering-and-scoring.md)
- [Build and deployment](./build-and-deployment.md)
- [Troubleshooting](./troubleshooting.md)

## Usage Rules

1. Treat sections labeled **Current behavior** as verified implementation facts.
2. Treat sections labeled **Expected contract** as the format or behavior new work should preserve.
3. Treat sections labeled **Known limitation** as gaps that require an explicit requirement before changing.
4. When documentation and code disagree, inspect the owning function and update the documentation only after deciding which behavior is authoritative.