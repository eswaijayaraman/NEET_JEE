# Pull Request And Merge

## Commit And Push

After local validation:

```bash
git status
git add <intended-files>
git commit -m "Add <short description>"
git push -u origin <short-requirement-name>
```

Use a message that describes the delivered behavior. Review the staged diff before committing. Do not use `git add .` blindly when generated or unrelated files are present.

## Pull Request

Open a pull request from the feature branch into `main`. Include the requirement and acceptance criteria, implementation and documentation changes, local commands and results, known limitations, and Render verification steps.

Wait for required review and checks. Address review comments on the branch, rerun focused validation, and push the updates.

## Merge And Cleanup

Merge only after approval and passing checks. Then update local `main`:

```bash
git switch main
git pull origin main
git branch -d <short-requirement-name>
```

The merge is not the end of validation; complete the deployed Render checklist next.