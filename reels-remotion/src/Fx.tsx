import React from "react";
import { AbsoluteFill } from "remotion";
import { clamp01, easeIO, FPS } from "./util";

export type Block = { kind: "head" | "scene"; id?: string; b: number };
type Tr = { kind: string; frames: number; blur: number };

/** vertical offset (px) and blur (px) of block j at time t during the push + vertical-blur transition */
export const layerFx = (blocks: Block[], j: number, t: number, D: number, tr: Tr) => {
  if (tr.kind !== "push-blur") return { y: 0, blur: 0 };
  const half = tr.frames / 2 / FPS;
  const start = blocks[j].b;
  const end = j + 1 < blocks.length ? blocks[j + 1].b : D + 1;
  let y = 0;
  let blur = 0;
  if (j > 0 && t < start + half) {
    const p = clamp01((t - (start - half)) / (2 * half));
    const up = blocks[j].kind === "scene"; // scenes arrive from the bottom, the speaker comes back from the top
    y = (1 - easeIO(p)) * (up ? 1 : -1) * 1920;
    blur = Math.sin(Math.PI * p) * tr.blur;
  }
  if (j + 1 < blocks.length && t > end - half) {
    const p = clamp01((t - (end - half)) / (2 * half));
    const nextUp = blocks[j + 1].kind === "scene";
    y = easeIO(p) * (nextUp ? -1 : 1) * 1920;
    blur = Math.sin(Math.PI * p) * tr.blur;
  }
  return { y, blur };
};

export const inWindow = (blocks: Block[], j: number, t: number, D: number, tr: Tr) => {
  const half = (tr.kind === "push-blur" ? tr.frames : 0) / 2 / FPS;
  const start = blocks[j].b;
  const end = j + 1 < blocks.length ? blocks[j + 1].b : D + 1;
  return t >= start - half && t < end + half + (tr.kind === "push-blur" ? 0 : 0.001);
};

/** a layer that can be pushed and motion-blurred vertically (CSS + SVG: no shaders, so it renders fast) */
export const FxLayer: React.FC<{ y: number; blur: number; id: string; children: React.ReactNode }> = ({ y, blur, id, children }) => (
  <AbsoluteFill style={{ transform: y ? `translateY(${y}px)` : undefined, filter: blur > 1 ? `url(#${id})` : undefined }}>
    {blur > 1 && (
      <svg width="0" height="0" style={{ position: "absolute" }}>
        <filter id={id} x="-5%" y="-30%" width="110%" height="160%" colorInterpolationFilters="sRGB">
          <feGaussianBlur stdDeviation={`0 ${blur}`} />
        </filter>
      </svg>
    )}
    {children}
  </AbsoluteFill>
);
