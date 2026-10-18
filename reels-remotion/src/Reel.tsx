import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { Captions } from "./Captions";
import { bwAt, NumeralsBehind, Progress } from "./Chapters";
import { FxLayer, inWindow, layerFx } from "./Fx";
import { Grade, Head, camAt } from "./Head";
import { Hook } from "./Hook";
import { OVERLAY_COMPONENTS } from "./Overlays";
import { SCENE_COMPONENTS } from "./Scenes";
import { ThemeProvider } from "./theme";
import { FPS } from "./util";

/** The whole video from resolved.json (props). Nothing here is per-video: change plan.json, not this file. */
const Inner: React.FC<{ R: any }> = ({ R }) => {
  const frame = useCurrentFrame();
  const t = frame / FPS;
  const S = R.style;
  const D = R.meta.duration;
  const cam = camAt(t, R.shots, S.camera.presets, R.layout, D);
  const bw = bwAt(t, R);
  const tr = S.transition;
  const blocks = R.blocks;
  const headFx = blocks.reduce((acc: any, b: any, j: number) => (b.kind === "head" && inWindow(blocks, j, t, D, tr) ? layerFx(blocks, j, t, D, tr) : acc), { y: 0, blur: 0 });
  return (
    <AbsoluteFill style={{ background: S.colors.bg }}>
      <FxLayer y={headFx.y} blur={headFx.blur} id="hd">
        <Head cam={cam} bw={bw} />
        <NumeralsBehind t={t} R={R} cam={cam} bw={bw} />
        <Grade bw={bw} />
        <Progress t={t} R={R} />
        <Hook t={t} R={R} />
        {(R.overlays as any[]).map((o) => {
          const C = OVERLAY_COMPONENTS[o.archetype];
          return C ? <C key={o.id} o={o} t={t} /> : null;
        })}
        <Captions t={t} R={R} />
      </FxLayer>
      {blocks.map((b: any, j: number) => {
        if (b.kind !== "scene" || !inWindow(blocks, j, t, D, tr)) return null;
        const s = R.scenes.find((x: any) => x.id === b.id);
        const C = s && SCENE_COMPONENTS[s.archetype];
        if (!C) return null;
        const fx = layerFx(blocks, j, t, D, tr);
        return (
          <FxLayer key={j} y={fx.y} blur={fx.blur} id={`sc${j}`}>
            <C s={s} t={t} />
          </FxLayer>
        );
      })}
    </AbsoluteFill>
  );
};

export const Reel: React.FC<any> = (R) => (
  <ThemeProvider style={R.style} layout={R.layout}>
    <Inner R={R} />
  </ThemeProvider>
);
