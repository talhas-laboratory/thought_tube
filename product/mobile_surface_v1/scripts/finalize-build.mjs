import { copyFileSync, existsSync, mkdirSync, readdirSync, rmSync } from "node:fs";
import { join } from "node:path";

const root = new URL("..", import.meta.url);
const rootPath = root.pathname;
const distPath = join(rootPath, ".vite-dist", "assets");

if (!existsSync(distPath)) {
  throw new Error(`Missing Vite assets directory: ${distPath}`);
}

const files = readdirSync(distPath);
const jsFile = files.find((name) => name.endsWith(".js"));
const cssFile = files.find((name) => name.endsWith(".css"));

if (!jsFile || !cssFile) {
  throw new Error(`Expected built JS and CSS assets in ${distPath}`);
}

copyFileSync(join(distPath, jsFile), join(rootPath, "app.js"));
copyFileSync(join(distPath, cssFile), join(rootPath, "styles.css"));

rmSync(join(rootPath, ".vite-dist"), { recursive: true, force: true });

mkdirSync(join(rootPath, "src"), { recursive: true });
