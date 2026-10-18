import React from "react";
import { Composition } from "remotion";
import { Reel } from "./Reel";

const stub: any = {
  meta: { duration: 3, fps: 30 },
  style: { colors: { bg: "#000" }, fonts: { sans: "InterTight", accent: "InterTight", mono: "IBMPlexMono" }, head: {}, captions: {}, scene: { card: {} }, overlay: { panel: {} }, camera: { presets: { A: 1 }, cycle: ["A"], min_gap: 2 }, transition: { kind: "none", frames: 8, blur: 0 } },
  layout: { face: { x: 400, y: 560, w: 300, h: 340 }, chin: 914 },
  words: [], chunks: [], scenes: [], overlays: [], blocks: [{ kind: "head", b: 0 }], shots: [{ t: 0, preset: "A" }], chapters: [], mattes: [],
};

/** Render: npx remotion render Reel out/reel.mp4 --props=<workdir>/resolved.json   (render.py does it for you) */
export const RemotionRoot: React.FC = () => (
  <Composition
    id="Reel"
    component={Reel}
    width={1080}
    height={1920}
    fps={30}
    durationInFrames={90}
    defaultProps={stub}
    calculateMetadata={({ props }: { props: any }) => ({ durationInFrames: Math.max(1, Math.round(props.meta.duration * 30)), fps: 30 })}
  />
);
