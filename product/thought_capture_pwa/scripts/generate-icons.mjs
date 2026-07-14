import { mkdir, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import sharp from "sharp";

const __dirname = dirname(fileURLToPath(import.meta.url));
const iconsDir = join(__dirname, "..", "public", "icons");

const BG = "#0a0a0c";
const ACCENT = "#c4b5a8";

async function drawIcon(size, maskable = false) {
  const inset = maskable ? Math.round(size * 0.1) : 0;
  const inner = size - inset * 2;
  const dotRadius = Math.round(inner * 0.09);
  const cx = inset + inner / 2;
  const cy = inset + inner * 0.42;

  const svg = `
    <svg width="${size}" height="${size}" xmlns="http://www.w3.org/2000/svg">
      <rect width="${size}" height="${size}" fill="${BG}" />
      <circle cx="${cx}" cy="${cy}" r="${dotRadius}" fill="${ACCENT}" opacity="0.92" />
      <circle cx="${cx}" cy="${cy + dotRadius * 2.2}" r="${dotRadius * 0.55}" fill="${ACCENT}" opacity="0.35" />
    </svg>
  `;

  return sharp(Buffer.from(svg)).png().toBuffer();
}

await mkdir(iconsDir, { recursive: true });

const outputs = [
  ["icon-192.png", 192, false],
  ["icon-512.png", 512, false],
  ["icon-maskable-512.png", 512, true],
  ["apple-touch-icon-180.png", 180, false],
];

for (const [name, size, maskable] of outputs) {
  const buffer = await drawIcon(size, maskable);
  await writeFile(join(iconsDir, name), buffer);
  console.log(`wrote public/icons/${name}`);
}
