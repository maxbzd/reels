import React from "react";
import { Icon } from "./icons";
import { useTheme } from "./theme";
import { clamp01, ease, eo, lin, pop } from "./util";

/* Panels that sit on the speaker (the lower third of the frame). Time window: o.ta .. o.tb. */

const Win: React.FC<{ o: any; t: number; enter?: number; exit?: number; children: (v: { in: number; out: number; vis: number }) => React.ReactNode }> = ({ o, t, enter = 0.5, exit = 0.28, children }) => {
  if (t < o.ta || t > o.tb + exit) return null;
  const vin = eo(clamp01((t - o.ta) / enter));
  const vout = clamp01((t - o.tb) / exit);
  return <>{children({ in: vin, out: vout, vis: vin * (1 - vout) })}</>;
};

const Glass: React.FC<{ h: number; v: { in: number; out: number; vis: number }; children?: React.ReactNode }> = ({ h, v, children }) => {
  const { S } = useTheme();
  const p = S.overlay.panel;
  return (
    <div
      style={{
        position: "absolute",
        left: p.x,
        top: p.bottom - h,
        width: p.w,
        height: h,
        borderRadius: p.radius,
        background: p.bg,
        backdropFilter: `blur(${p.blur}px) saturate(1.25)`,
        border: p.border,
        boxShadow: p.shadow,
        color: p.text,
        opacity: v.vis,
        transform: `translateY(${(1 - v.in) * 56 + v.out * 36}px) scale(${0.95 + 0.05 * v.in})`,
        transformOrigin: "50% 100%",
        overflow: "hidden",
      }}
    >
      {children}
    </div>
  );
};

const Label: React.FC<{ children: React.ReactNode; top?: number }> = ({ children, top = 26 }) => {
  const { S, F } = useTheme();
  return <div style={{ position: "absolute", left: 36, top, fontFamily: F.mono, fontWeight: 600, fontSize: 22, letterSpacing: ".16em", textTransform: "uppercase", color: S.overlay.panel.dim }}>{children}</div>;
};

const Mark: React.FC<{ mark: string; t: number; at: number }> = ({ mark, t, at }) => {
  const { c } = useTheme();
  const ok = mark !== "cross";
  const col = ok ? c("accent") : c("bad");
  return (
    <div style={{ width: 52, height: 52, borderRadius: 26, display: "flex", alignItems: "center", justifyContent: "center", background: col + "30", color: col }}>
      <Icon name={ok ? "check" : "cross"} size={32} p={lin(t, at + 0.05, at + 0.4)} />
    </div>
  );
};

/** Rows with check or cross. props: {label, rows:[{text, mark?, at}]} */
export const PanelRows: React.FC<{ o: any; t: number }> = ({ o, t }) => {
  const { S, F } = useTheme();
  const rows = o.props.rows as any[];
  const h = 86 + rows.reduce((n, r) => n + 70 * ease(t, r.at ?? o.ta, 0.35), 0) + 14;
  return (
    <Win o={o} t={t}>
      {(v) => (
        <Glass h={h} v={v}>
          {o.props.label && <Label>{o.props.label}</Label>}
          {rows.map((r, i) => {
            const k = ease(t, r.at ?? o.ta, 0.4);
            if (k <= 0) return null;
            return (
              <div key={i} style={{ position: "absolute", left: 36, top: 70 + i * 70, display: "flex", alignItems: "center", gap: 20, opacity: k, transform: `translateX(${(1 - k) * -28}px)` }}>
                <Mark mark={r.mark || "check"} t={t} at={r.at ?? o.ta} />
                <div style={{ fontFamily: F.sans, fontWeight: 700, fontSize: 42, color: S.overlay.panel.text }}>{r.text}</div>
              </div>
            );
          })}
        </Glass>
      )}
    </Win>
  );
};

/** One strong word with a line under it. props: {label, title, sub?, icon?, icon_at?} */
export const PanelStatus: React.FC<{ o: any; t: number }> = ({ o, t }) => {
  const { S, F, c } = useTheme();
  const p = o.props;
  const k = pop(t, p.icon_at ?? o.ta + 0.2, 14);
  return (
    <Win o={o} t={t}>
      {(v) => (
        <Glass h={222} v={v}>
          {p.label && <Label>{p.label}</Label>}
          {p.icon && <div style={{ position: "absolute", left: 44, top: 74, color: c("accent"), transform: `scale(${0.4 + 0.6 * k})`, opacity: clamp01(k * 2) }}><Icon name={p.icon} size={110} /></div>}
          <div style={{ position: "absolute", left: p.icon ? 200 : 44, top: 80, fontFamily: F.accent, fontWeight: 800, fontSize: 60, letterSpacing: "-0.03em", color: S.overlay.panel.text }}>{p.title}</div>
          {p.sub && <div style={{ position: "absolute", left: p.icon ? 200 : 44, top: 152, fontFamily: F.sans, fontWeight: 600, fontSize: 36, color: S.overlay.panel.dim }}>{p.sub}</div>}
        </Glass>
      )}
    </Win>
  );
};

/** A bar that fills. props: {label, caption, value 0..1, at, settle_at, unit?, bad?} */
export const PanelMeter: React.FC<{ o: any; t: number }> = ({ o, t }) => {
  const { S, F, c } = useTheme();
  const p = o.props;
  const m = lin(t, p.at ?? o.ta, p.settle_at ?? o.tb) * (p.value ?? 1);
  return (
    <Win o={o} t={t}>
      {(v) => (
        <Glass h={252} v={v}>
          {p.label && <Label top={28}>{p.label}</Label>}
          <div style={{ position: "absolute", left: 44, right: 44, top: 84 }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontFamily: F.mono, fontWeight: 600, fontSize: 26, letterSpacing: ".12em", textTransform: "uppercase", color: S.overlay.panel.dim }}>
              <span>{p.caption}</span>
              <span style={{ color: m > 0.02 ? c(p.bad === false ? "accent" : "bad") : S.overlay.panel.dim }}>{Math.round(m * 100)}{p.unit ?? "%"}</span>
            </div>
            <div style={{ marginTop: 18, height: 30, borderRadius: 15, background: "rgba(255,255,255,0.12)", overflow: "hidden" }}>
              <div style={{ width: `${Math.max(0.04, m) * 100}%`, height: "100%", borderRadius: 15, background: `linear-gradient(90deg, ${c("accent")}, ${c(p.bad === false ? "accent" : "bad")})` }} />
            </div>
            {p.note && <div style={{ marginTop: 14, fontFamily: F.sans, fontWeight: 700, fontSize: 38, color: S.overlay.panel.text }}>{p.note}</div>}
          </div>
        </Glass>
      )}
    </Win>
  );
};

/** Three nodes joined by a line that fills. props: {label, nodes:[{text, at}] x3, through_at?} */
export const PanelFlow: React.FC<{ o: any; t: number }> = ({ o, t }) => {
  const { S, F, c } = useTheme();
  const nodes = o.props.nodes as any[];
  const line = lin(t, o.props.through_at ?? (nodes[1]?.at ?? o.ta + 1), (o.props.through_at ?? (nodes[1]?.at ?? o.ta + 1)) + 0.8);
  const k = nodes.map((n, i) => pop(t, n.at ?? o.ta + i * 0.4, 13));
  return (
    <Win o={o} t={t}>
      {(v) => (
        <Glass h={222} v={v}>
          {o.props.label && <Label>{o.props.label}</Label>}
          <div style={{ position: "absolute", left: 178, top: 138, width: 596, height: 6, borderRadius: 3, background: "rgba(255,255,255,0.16)" }} />
          <div style={{ position: "absolute", left: 178, top: 138, width: 596 * line, height: 6, borderRadius: 3, background: c("accent") }} />
          {nodes[0] && <div style={{ position: "absolute", left: 54, top: 84, width: 112, height: 112, borderRadius: 56, background: c("accent"), color: c("ink"), display: "flex", alignItems: "center", justifyContent: "center", fontFamily: F.sans, fontWeight: 900, fontSize: String(nodes[0].text).length > 3 ? 31 : 40, transform: `scale(${0.4 + 0.6 * k[0]})`, opacity: clamp01(k[0] * 2) }}>{nodes[0].text}</div>}
          {nodes[1] && <div style={{ position: "absolute", left: 384, top: 98, padding: "0 28px", height: 84, borderRadius: 20, background: `linear-gradient(180deg, ${c("accent2")}, ${c("accent2")}bb)`, color: "#fff", display: "flex", alignItems: "center", fontFamily: F.sans, fontWeight: 800, fontSize: 36, opacity: ease(t, nodes[1].at ?? o.ta, 0.4), transform: `scale(${1 - 0.06 * Math.sin(line * Math.PI)})` }}>{nodes[1].text}</div>}
          {nodes[2] && <div style={{ position: "absolute", right: 54, top: 84, width: 112, height: 112, borderRadius: 56, border: `4px solid ${c("accent")}`, color: c("accent"), display: "flex", alignItems: "center", justifyContent: "center", transform: `scale(${0.4 + 0.6 * k[2]})`, opacity: clamp01(k[2] * 2) }}><Icon name="check" size={64} p={clamp01(k[2])} /></div>}
        </Glass>
      )}
    </Win>
  );
};

const Chip: React.FC<{ t: number; at: number; end: number; text: string; mark: string }> = ({ t, at, end, text, mark }) => {
  const { S, F, c } = useTheme();
  const p = pop(t, at, 16);
  const out = clamp01((t - end) / 0.28);
  if (t < at || out >= 1) return null;
  const col = mark === "check" ? c("accent") : c("bad");
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 14, padding: "0 26px 0 16px", height: 88, borderRadius: 44, background: S.overlay.panel.bg, backdropFilter: "blur(22px)", border: S.overlay.panel.border, boxShadow: S.overlay.panel.shadow, transform: `scale(${0.6 + 0.4 * p}) translateY(${out * 24}px)`, opacity: clamp01(p * 2) * (1 - out), whiteSpace: "nowrap" }}>
      <div style={{ width: 54, height: 54, borderRadius: 27, background: col + "38", color: col, display: "flex", alignItems: "center", justifyContent: "center" }}><Icon name={mark === "check" ? "check" : "cross"} size={32} p={lin(t, at + 0.1, at + 0.45)} /></div>
      <div style={{ fontFamily: F.sans, fontWeight: 700, fontSize: 42, color: S.overlay.panel.text }}>{text}</div>
    </div>
  );
};

/** Stacked chips that pop on words. props: {items:[{text, at, mark?:"cross"|"check", row?:0|1|2}]} */
export const Chips: React.FC<{ o: any; t: number }> = ({ o, t }) => {
  if (t < o.ta || t > o.tb + 0.3) return null;
  const items = o.props.items as any[];
  const rows: any[][] = [];
  items.forEach((it, i) => {
    const r = it.row ?? i;
    (rows[r] = rows[r] || []).push(it);
  });
  return (
    <div style={{ position: "absolute", left: 0, right: 0, top: 1296, display: "flex", flexDirection: "column", alignItems: "center", gap: 18 }}>
      {rows.map((row, ri) => (
        <div key={ri} style={{ display: "flex", gap: 18, minHeight: 88 }}>
          {(row || []).map((it, k) => <Chip key={k} t={t} at={it.at ?? o.ta} end={o.tb} text={it.text} mark={it.mark || "cross"} />)}
        </div>
      ))}
    </div>
  );
};

/** Pills on top of the frame, one may count up. props: {items:[{icon?, text, at, count?:{to, dur?}}]}  "{n}" in text = the counter */
export const Pills: React.FC<{ o: any; t: number }> = ({ o, t }) => {
  const { S, F, c } = useTheme();
  return (
    <Win o={o} t={t} enter={0.45}>
      {(v) => (
        <div style={{ position: "absolute", left: 0, right: 0, top: 320, display: "flex", justifyContent: "center", gap: 18, opacity: v.vis, transform: `translateY(${(1 - v.in) * -30}px)` }}>
          {(o.props.items as any[]).map((it, i) => {
            const k = pop(t, (it.at ?? o.ta) - 0.05, 15);
            if (t < (it.at ?? o.ta) - 0.05) return null;
            const n = it.count ? Math.round((it.count.from ?? 0) + (it.count.to - (it.count.from ?? 0)) * eo(lin(t, it.at ?? o.ta, (it.at ?? o.ta) + (it.count.dur ?? 0.55)))) : 0;
            const text = String(it.text).replace("{n}", String(n));
            return (
              <div key={i} style={{ display: "flex", alignItems: "center", gap: 14, height: 84, padding: "0 30px 0 24px", borderRadius: 42, background: S.overlay.panel.bg, backdropFilter: "blur(22px)", border: S.overlay.panel.border, boxShadow: S.overlay.panel.shadow, transform: `scale(${0.5 + 0.5 * k})`, opacity: clamp01(k * 2) }}>
                {it.icon && <span style={{ color: c("accent"), display: "flex" }}><Icon name={it.icon} size={44} /></span>}
                <span style={{ fontFamily: F.sans, fontWeight: 700, fontSize: 38, color: S.overlay.panel.text }}>{text}</span>
              </div>
            );
          })}
        </div>
      )}
    </Win>
  );
};

export const OVERLAY_COMPONENTS: Record<string, React.FC<{ o: any; t: number }>> = {
  panel_rows: PanelRows,
  panel_status: PanelStatus,
  panel_meter: PanelMeter,
  panel_flow: PanelFlow,
  chips: Chips,
  pills: Pills,
};
