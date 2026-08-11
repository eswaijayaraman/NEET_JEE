const fs = require('fs');
const path = require('path');

const rootDir = path.resolve(__dirname);
const distDir = path.join(rootDir, 'dist');

function ensureDir(dir) {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

if (fs.existsSync(distDir)) {
  fs.rmSync(distDir, { recursive: true, force: true });
}

ensureDir(distDir);

const filesToCopy = ['app.js', 'package.json', 'package-lock.json'];
for (const file of filesToCopy) {
  const src = path.join(rootDir, file);
  const dest = path.join(distDir, file);
  if (fs.existsSync(src)) {
    fs.copyFileSync(src, dest);
  }
}

const staticSrc = path.join(rootDir, 'static');
if (fs.existsSync(staticSrc)) {
  fs.cpSync(staticSrc, path.join(distDir, 'static'), { recursive: true });
}

const docxFiles = fs.readdirSync(rootDir).filter((file) => file.toLowerCase().endsWith('.docx'));
for (const file of docxFiles) {
  fs.copyFileSync(path.join(rootDir, file), path.join(distDir, file));
}

console.log(`Build complete. Copied ${filesToCopy.filter((file) => fs.existsSync(path.join(rootDir, file))).length} files, ${docxFiles.length} .docx files, and static assets to dist.`);
