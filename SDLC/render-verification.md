# Render Verification

After the pull request is merged into `main`, wait for Render to finish deploying, then open [Render - Application loading](https://neet-jee-scfr.onrender.com/).

## Smoke Checklist

1. Confirm the landing page loads successfully.
2. Submit a NEET candidate and verify Physics, Chemistry, and Biology sections and their question content.
3. Submit a JEE candidate and verify Physics and Mathematics visibility; confirm the expected behavior for any missing Chemistry bank.
4. Open a question containing an image and confirm its `/static/` asset loads.
5. Submit representative correct, wrong, unanswered, and numeric answers when applicable.
6. Confirm the results page, `/dashboard`, and `/download-excel` respond as expected.
7. Check the Render deploy log for build or runtime errors.

## Failure Handling

If the deployed result differs from local behavior, record the URL, stream, subject, input bank, and response. Check whether the merged commit and all required DOCX/static assets reached the deployment. Reproduce locally from the merged `main` before opening a follow-up fix or rollback request.

**Known limitation:** Render configuration is not stored in this repository. Verify the service’s configured build/start commands against `npm run build` and `npm start` rather than assuming configuration changes are versioned here.