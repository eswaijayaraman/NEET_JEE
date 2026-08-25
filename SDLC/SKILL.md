---
name: neet-jee-sdlc
description: "Use when taking a NEET/JEE requirement from branch creation through local build and tests, commit, push, pull request, merge to main, and post-merge Render verification."
argument-hint: "Describe the requirement or delivery stage"
---

# NEET/JEE Software Delivery Lifecycle

Follow the references in order for application, question-bank, and documentation changes. Do not merge a change without local validation and a reviewable pull request.

## Index

- [Requirements](./requirements.md)
- [Development](./development.md)
- [Local validation](./local-validation.md)
- [Pull request and merge](./pull-request-and-merge.md)
- [Render verification](./render-verification.md)

## Lifecycle

1. Write the requirement and acceptance criteria.
2. Create a branch from an up-to-date `main`.
3. Implement the smallest complete change and update relevant Knowledge documentation.
4. Build and test locally.
5. Review `git diff` and `git status`.
6. Commit and push the branch.
7. Open a pull request against `main`, address review, and merge it.
8. Verify the deployed Render application after the merge.

## Completion Rule

A change is complete only when its acceptance criteria pass locally, the pull request is merged, and the relevant deployed flow is checked on Render.