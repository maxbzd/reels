import React from "react";
import { useTheme } from "./theme";
import { clamp01, ease } from "./util";

/** Captions in the style's voice. mode "chunk": block under the chin (sans + accent font). mode "top": one line above the head. */
export const Captions: React.FC<{ t: number; R: any }> = ({ t, R }) => {
  const { S, F, c, layout } = useTheme();
  const cp = S.captions;
  const words = R.words as { text: string; start: number; end: number; accent: boolean; hidden?: boolean }[];
  const chunks = R.chunks as { a: number; b: number; w: number[] }[];
  const scenes = R.scenes as { ta: number; tb: number }[];
  if (scenes.some((s) => t >= s.ta - 0.02 && t < s.tb + 0.02)) return null;
  const i = chunks.findIndex((ch, k) => t >= ch.a && (k + 1 >= chunks.length || t < chunks[k + 1].a));
  if (i < 0) return null;
  const ch = chunks[i];
  const holdEnd = Math.min(i + 1 < chunks.length ? chunks[i + 1].a : ch.b + 0.5, ch.b + 0.55);
  if (t > holdEnd) return null;
  const cover = scenes.find((s) => s.ta < ch.b && s.tb > ch.a);
  if (cover && cover.ta - ch.a < 0.25) return null;
  const out = clamp01((t - (holdEnd - 0.12)) / 0.12);
  const inn = ease(t, ch.a - 0.02, 0.28);
  const list = ch.w.map((k) => words[k]).filter((w) => !w.hidden && w.text.replace(/[,.:;]$/, "") !== "—");
  const inHook = !!R.hook && ch.a < R.hook.tb;
  if (!list.length) return null;

  if (cp.mode === "top") {
    const lowHook = inHook && cp.hookTop;
    return (
      <div
        style={{
          position: "absolute",
          left: 80,
          right: 80,
          top: lowHook ? cp.hookTop : cp.top,
          height: 150,
          display: "flex",
          alignItems: lowHook ? "flex-start" : "flex-end",
          justifyContent: "center",
          textAlign: "center",
          opacity: inn * (1 - out),
          transform: `translateY(${(1 - inn) * 18}px)`,
        }}
      >
        <div style={{ fontFamily: F[cp.font as "sans"], fontWeight: cp.weight, fontSize: lowHook ? cp.hookSize : cp.size, lineHeight: 1.12, letterSpacing: "-0.01em", textWrap: "balance" as any }}>
          {list.map((w, k) => (
            <span key={k} style={{ color: w.accent ? c(cp.accentColor) : c(cp.color), fontFamily: w.accent ? F[cp.accentFont as "sans"] : undefined }}>
              {w.text.replace(/[,.:;]$/, "")}
              {k < list.length - 1 ? " " : ""}
            </span>
          ))}
        </div>
      </div>
    );
  }
  const top = cp.top ?? layout.caption_top;
  return (
    <div style={{ position: "absolute", left: 60, right: 60, top, height: 200, textAlign: "center", opacity: 1 - out }}>
      <div style={{ display: "inline-block", maxWidth: cp.width, lineHeight: 1.16, opacity: inn, transform: `translateY(${(1 - inn) * 14}px)`, filter: `blur(${(1 - inn) * 6}px)` }}>
        {list.map((w, k) => {
          const wipe = w.accent ? ease(t, ch.a + 0.08, 0.45) : 1;
          return (
            <span
              key={k}
              style={{
                display: "inline-block",
                marginRight: 14,
                fontFamily: w.accent ? F[cp.accentFont as "sans"] : F[cp.font as "sans"],
                fontWeight: w.accent ? cp.accentWeight : cp.weight,
                fontSize: w.accent ? cp.accentSize : cp.size,
                color: w.accent ? c(cp.accentColor) : c(cp.color),
                clipPath: w.accent ? `inset(-20% ${100 - wipe * 100}% -20% 0)` : undefined,
              }}
            >
              {w.text.replace(/[,.:;]$/, "")}
            </span>
          );
        })}
      </div>
    </div>
  );
};
