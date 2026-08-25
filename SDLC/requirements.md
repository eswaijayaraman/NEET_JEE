# Requirements

Write each requirement so another developer can implement and test it without guessing.

## Required Content

- User or teacher outcome
- NEET or JEE stream and affected subject
- Whether the change affects application code, a DOCX bank, parsing, scoring, deployment, or documentation
- Current behavior and desired behavior
- Acceptance criteria with observable results
- Test data, including the relevant Word format if a bank changes
- Risks, security implications, and rollback considerations

## Example

```text
Requirement: Add a JEE Mathematics question bank.
Outcome: JEE candidates can see and answer Mathematics questions.
Input: Root file named Mathematics-JEE.docx using the Knowledge Word contract.
Acceptance: The JEE board shows Mathematics questions; NEET remains unchanged; the bank is included by npm run build; local and Render smoke tests pass.
```

Before development, resolve ambiguities such as timer duration, missing subject-bank policy, numeric-answer rules, and whether `sixth-app.py` is in scope.