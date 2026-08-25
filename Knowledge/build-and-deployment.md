# Build And Deployment

## Local Build

From the repository root:

```bash
npm install
npm run build
```

`build.js` deletes and recreates `dist/`, then copies `app.js`, `package.json`, `package-lock.json`, every root `.docx`, and the complete `static/` directory. The `postbuild` script installs production dependencies inside `dist/`.

## Local Runtime

```bash
npm start
```

The server listens on `process.env.PORT` or port `5000`. Open `http://127.0.0.1:5000/` and use [SDLC/local-validation.md](../SDLC/local-validation.md).

## Render

The deployed application is available at [neet-jee-scfr.onrender.com](https://neet-jee-scfr.onrender.com/). Render deployment details are not configured in this repository, so the service build and start settings must remain aligned with the repository scripts.

**Expected contract:** A deployment must include the Node runtime, all matching root DOCX banks, and `static/` media. Verify the deployed portal and both stream flows after a merged change.

**Known limitation:** The generated `dist/index.html` contains Catalyst SDK references, but this repository does not define Catalyst configuration. Do not describe Catalyst services as configured until deployment configuration is added and verified.