import React from "react";
import { AbsoluteFill, OffthreadVideo, staticFile } from "remotion";
import { useTheme } from "./theme";
import { clamp01 } from "./util";

export type Cam = { z: number; cx: number; cy: number };

/** camera zoom -> the point that sits at the screen centre. The chin keeps its height, so captions never have to move. */
export const camFor = (zoom: number, layout: any): Cam => {
  const faceX = layout.face.x + layout.face.w / 2;
  const chin = layout.chin;
  if (zoom <= 1.001) return { z: 1, cx: 540, cy: 960 };
  const cx = Math.min(1080 - 540 / zoom, Math.max(540 / zoom, faceX));
  const cy = Math.min(1920 - 960 / zoom, Math.max(960 / zoom, chin - (Math.min(chin, 1140) - 960) / zoom));
  return { z: zoom, cx, cy };
};

export const camAt = (t: number, shots: { t: number; preset: string }[], presets: Record<string, number>, layout: any, duration: number, drift = 0.03): Cam => {
  let i = 0;
  for (let k = 0; k < shots.length; k++) if (t >= shots[k].t) i = k;
  const s = shots[i];
  const end = i + 1 < shots.length ? shots[i + 1].t : duration;
  const p = clamp01((t - s.t) / Math.max(0.1, end - s.t));
  const z = (presets[s.preset] ?? 1) * (1 + drift * p);
  return camFor(z, layout);
};

/** the speaker: video + grade filter. bw (0..1) turns the picture black and white for a moment (colored graphics stay colored). */
export const Head: React.FC<{ cam: Cam; bw?: number; children?: React.ReactNode }> = ({ cam, bw = 0, children }) => {
  const { S, c } = useTheme();
  return (
    <AbsoluteFill style={{ background: c("bg") }}>
      <AbsoluteFill
        style={{
          transform: `translate(${540 - cam.cx * cam.z}px, ${960 - cam.cy * cam.z}px) scale(${cam.z})`,
          transformOrigin: "0 0",
          width: 1080,
          height: 1920,
          filter: `${S.head.filter} grayscale(${bw})`,
        }}
      >
        <OffthreadVideo src={staticFile("video.mp4")} style={{ width: 1080, height: 1920 }} />
      </AbsoluteFill>
      {children}
    </AbsoluteFill>
  );
};

/** the same camera applied to a layer that sits on the speaker (the cut-out person for numerals behind her) */
export const CamLayer: React.FC<{ cam: Cam; bw?: number; children: React.ReactNode }> = ({ cam, bw = 0, children }) => {
  const { S } = useTheme();
  return (
    <AbsoluteFill
      style={{
        transform: `translate(${540 - cam.cx * cam.z}px, ${960 - cam.cy * cam.z}px) scale(${cam.z})`,
        transformOrigin: "0 0",
        width: 1080,
        height: 1920,
        filter: `${S.head.filter} grayscale(${bw})`,
      }}
    >
      {children}
    </AbsoluteFill>
  );
};

/** grade layers over the picture (and over the cut-out person, so both share one look) */
export const Grade: React.FC<{ bw?: number }> = ({ bw = 0 }) => {
  const { S } = useTheme();
  const h = S.head;
  const sh = (a: number) => `rgba(${h.shadeColor},${a})`;
  return (
    <>
      {h.tint && <AbsoluteFill style={{ background: h.tint, mixBlendMode: "multiply", opacity: 1 - bw }} />}
      {h.topShade > 0 && (
        <AbsoluteFill style={{ background: `linear-gradient(180deg, ${sh(h.topShade)} 0%, ${sh(h.topShade * 0.75)} 15%, ${sh(h.topShade * 0.5)} 25%, ${sh(h.topShade * 0.2)} 33%, ${sh(0)} 39%)` }} />
      )}
      {h.vignette > 0 && (
        <AbsoluteFill style={{ background: `radial-gradient(ellipse 62% 48% at 55% 52%, rgba(0,0,0,0) 40%, ${sh(h.vignette * 0.7)} 78%, ${sh(Math.min(0.92, h.vignette * 1.4))} 100%)` }} />
      )}
      {h.bottomShade > 0 && <AbsoluteFill style={{ background: `linear-gradient(0deg, ${sh(h.bottomShade)} 0%, ${sh(0)} 32%)` }} />}
      {(h.glows || []).map((g: any, i: number) => (
        <AbsoluteFill key={i} style={{ background: `radial-gradient(circle at ${g.x}% ${g.y}%, rgba(${g.rgb},${g.a}) 0%, rgba(${g.rgb},0) ${g.r}%)`, mixBlendMode: "screen", opacity: 1 - bw }} />
      ))}
    </>
  );
};

export const clampCam = clamp01;
