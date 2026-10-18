import React from "react";
import { useTheme } from "./theme";
import { clamp01, ease } from "./util";

/** Opening headline over the speaker. plan.hook = {lines:["ЗНАЕШЬ АНГЛИЙСКИЙ,","НО МОЛЧИШЬ"], plate:"ВОТ ПОЧЕМУ", from, to} */
export const Hook: React.FC<{ t: number; R: any }> = ({ t, R }) => {
  const { S, F, c } = useTheme();
  const h = R.hook;
  if (!h || t < h.ta || t > h.tb + 0.3) return null;
  const k = S.hook;
  const out = clamp01((t - h.tb) / 0.3);
  const lines: string[] = h.lines || [];
  const plate = ease(t, h.ta + 0.35, 0.5);
  return (
    <div style={{ position: "absolute", left: 64, top: k.y, right: 64, opacity: 1 - out, transform: `translateY(${-out * 40}px)` }}>
      {lines.map((line, i) => {
        const p = ease(t, h.ta + 0.05 + i * 0.25, 0.6);
        return (
          <div key={i} style={{ overflow: "hidden", height: k.lineHeight, marginTop: i ? -2 : 0 }}>
            <div style={{ fontFamily: F[k.font as "sans"], fontWeight: k.weight, fontSize: k.size, lineHeight: `${k.lineHeight}px`, letterSpacing: k.letterSpacing, color: c("white"), transform: `translateY(${(1 - p) * 110}px)`, whiteSpace: "nowrap" }}>{line}</div>
          </div>
        );
      })}
      {h.plate && (
        <div style={{ display: "inline-block", marginTop: 6, padding: "8px 26px 10px", borderRadius: 14, background: c("accent"), color: c("ink"), fontFamily: F.sans, fontWeight: 800, fontSize: k.plateSize, letterSpacing: "-0.02em", transformOrigin: "0 50%", transform: `scaleX(${plate})`, opacity: plate }}>{h.plate}</div>
      )}
    </div>
  );
};
