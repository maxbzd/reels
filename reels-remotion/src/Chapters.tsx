import React from "react";
import { OffthreadVideo, Sequence, staticFile } from "remotion";
import { Cam, CamLayer } from "./Head";
import { useTheme } from "./theme";
import { clamp01, ease, FPS, lin } from "./util";

/* Chapters: a progress bar with numbered segments, big numerals BEHIND the speaker (needs a cut-out of her:
   scripts/matte_cut.py), and a black-and-white moment for the picture while a numeral is on screen. */

export type Matte = { n: string; from: number; dur: number; file: string };

/** 0..1 while the picture should be black and white (only inside matte windows, with short fades) */
export const bwAt = (t: number, R: any) => {
  if (!R.style.chapters?.bw) return 0;
  return ((R.mattes || []) as Matte[]).reduce((m, w) => Math.max(m, clamp01((t - w.from) / 0.12) * clamp01((w.from + w.dur - t) / 0.2)), 0);
};

export const Progress: React.FC<{ t: number; R: any }> = ({ t, R }) => {
  const { S, F, c } = useTheme();
  const ch = R.chapters as { n: string; label: string; t: number }[];
  if (!S.chapters?.enabled || !ch.length) return null;
  const a = ch[0].t - 0.25;
  const vis = ease(t, a, 0.5);
  if (vis <= 0) return null;
  const W = 952, gap = 12;
  const segW = (W - gap * (ch.length - 1)) / ch.length;
  return (
    <div style={{ position: "absolute", left: 0, top: S.chapters.barY, width: 1080, opacity: vis, transform: `translateY(${(1 - vis) * -16}px)` }}>
      {ch.map((x, i) => {
        const s = i === 0 ? a : x.t;
        const e = i + 1 < ch.length ? ch[i + 1].t : R.chapters_end ?? R.meta.duration;
        const cur = t >= s && t < e;
        const done = t >= e;
        return (
          <div key={x.n} style={{ position: "absolute", left: 64 + i * (segW + gap), width: segW }}>
            <div style={{ height: 7, borderRadius: 4, background: "rgba(255,255,255,0.22)", overflow: "hidden" }}>
              <div style={{ width: `${(done ? 1 : lin(t, s, e)) * 100}%`, height: "100%", background: c("accent"), borderRadius: 4 }} />
            </div>
            <div style={{ marginTop: 12, width: segW, overflow: "hidden", textOverflow: "ellipsis", fontFamily: F.sans, fontWeight: 800, fontSize: Math.min(23, Math.max(15, segW / ((x.n.length + 1 + x.label.length) * 0.66))), letterSpacing: "0.04em", color: cur ? c("white") : done ? c("accent") : "rgba(255,255,255,0.45)", whiteSpace: "nowrap" }}>
              {x.n}
              {cur || done ? ` ${x.label}` : " …"}
            </div>
          </div>
        );
      })}
    </div>
  );
};

export const Numeral: React.FC<{ t: number; w: Matte; fallback?: boolean }> = ({ t, w, fallback }) => {
  const { S, F, c } = useTheme();
  const a = w.from + 0.03;
  const l = t - a;
  if (l < 0 || l > 1.75) return null;
  const vin = ease(t, a, 0.45);
  const vout = clamp01((l - 1.3) / 0.4);
  const n = fallback ? { ...S.chapters.numeral, size: S.chapters.numeral.size * 0.5, top: 330 } : S.chapters.numeral;
  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        width: 1080,
        top: n.top,
        textAlign: "center",
        fontFamily: F[n.font as "sans"],
        fontWeight: 900,
        fontSize: n.size,
        lineHeight: 1,
        letterSpacing: "-0.04em",
        color: c(n.color) + "17",
        WebkitTextStroke: `${n.stroke}px ${c(n.color)}`,
        opacity: vin * (1 - vout),
        transform: `scale(${1.1 - 0.1 * vin + vout * 0.04}) translateY(${vout * -24}px)`,
        transformOrigin: "50% 55%",
        filter: `drop-shadow(0 0 50px ${c(n.color)}4d)`,
        whiteSpace: "nowrap",
      }}
    >
      {w.n}
    </div>
  );
};

/** numerals behind + the cut-out person in front of them. Without cut-outs the numerals sit small in the headroom instead. */
export const NumeralsBehind: React.FC<{ t: number; R: any; cam: Cam; bw: number }> = ({ t, R, cam, bw }) => {
  const mattes = (R.mattes || []) as Matte[];
  if (!R.style.chapters?.enabled || R.style.chapters.numerals === false) return null;
  if (!mattes.length) {
    return (
      <>
        {(R.chapters as any[]).map((c) => <Numeral key={c.n} t={t} w={{ n: c.n, from: Math.max(0, c.t - 0.06), dur: 1.8, file: "" }} fallback />)}
      </>
    );
  }
  return (
    <>
      {mattes.map((w) => <Numeral key={w.n} t={t} w={w} />)}
      {mattes.map((w) => (
        <Sequence key={w.file} from={Math.round(w.from * FPS)} durationInFrames={Math.round(w.dur * FPS) + 1}>
          <CamLayer cam={cam} bw={bw}>
            <OffthreadVideo transparent muted src={staticFile(w.file)} style={{ width: 1080, height: 1920 }} />
          </CamLayer>
        </Sequence>
      ))}
    </>
  );
};
