// node stills.mjs <resolved.json> <outDir> <seconds,seconds,...> [scale]
// Renders still frames of the reel (the bundle is built once). Used to LOOK at the edit before the full render.
import { bundle } from "@remotion/bundler";
import { renderStill, selectComposition } from "@remotion/renderer";
import fs from "node:fs";
import path from "node:path";

const [propsFile, outDir, secs, scaleArg] = process.argv.slice(2);
const props = JSON.parse(fs.readFileSync(propsFile, "utf-8"));
const scale = Number(scaleArg || 0.5);
fs.mkdirSync(outDir, { recursive: true });
const serveUrl = await bundle({ entryPoint: path.resolve("src/index.ts") });
const comp = await selectComposition({ serveUrl, id: "Reel", inputProps: props, browserExecutable: process.env.REMOTION_BROWSER || undefined });
for (const s of secs.split(",").map(Number)) {
  const frame = Math.min(comp.durationInFrames - 1, Math.max(0, Math.round(s * 30)));
  const output = path.join(outDir, `still_${String(s).replace(".", "_")}.png`);
  await renderStill({ composition: comp, serveUrl, frame, output, scale, inputProps: props, browserExecutable: process.env.REMOTION_BROWSER || undefined });
  console.log("still", s, "->", output);
}
