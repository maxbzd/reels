import React from "react";
import { AbsoluteFill } from "remotion";
import { Icon } from "./icons";
import { useTheme } from "./theme";
import { clamp01, ease, eo, lin, pop } from "./util";

/* ------------------------------------------------------------------ frame, background, header, card */

const Background: React.FC<{ t: number }> = ({ t }) => {
  const { S, c } = useTheme();
  if (S.scene.bg === "dark") {
    return (
      <AbsoluteFill style={{ background: c("bg") }}>
        <AbsoluteFill style={{ background: `radial-gradient(circle at 18% 14%, rgba(${S.scene.glowA || "196,23,127"},0.30) 0%, rgba(0,0,0,0) 40%)` }} />
        <AbsoluteFill style={{ background: `radial-gradient(circle at 88% 30%, rgba(${S.scene.glowB || "122,43,209"},0.24) 0%, rgba(0,0,0,0) 38%)` }} />
        <AbsoluteFill style={{ background: "radial-gradient(ellipse 90% 70% at 50% 45%, rgba(0,0,0,0) 55%, rgba(0,0,0,0.45) 100%)" }} />
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill style={{ background: c("bgLight") }}>
      <div
        style={{
          position: "absolute",
          left: -300,
          top: -300,
          width: 1700,
          height: 2500,
          transform: `rotate(24deg) translateX(${Math.sin(t * 0.5) * 30}px)`,
          background: "linear-gradient(90deg, rgba(255,255,255,0) 20%, rgba(255,255,255,.75) 32%, rgba(255,255,255,0) 44%, rgba(255,255,255,0) 58%, rgba(255,255,255,.5) 68%, rgba(255,255,255,0) 78%)",
        }}
      />
      <AbsoluteFill style={{ background: "radial-gradient(ellipse 90% 70% at 50% 45%, rgba(0,0,0,0) 55%, rgba(120,108,88,.10) 100%)" }} />
    </AbsoluteFill>
  );
};

export const Header: React.FC<{ t: number; t0: number; sans: string; accent: string; y?: number; big?: boolean }> = ({ t, t0, sans, accent, y, big }) => {
  const { S, F, c } = useTheme();
  const h = S.scene.header;
  const dark = S.scene.bg === "dark";
  const a = ease(t, t0, 0.35);
  const b = ease(t, t0 + 0.12, 0.6);
  return (
    <div style={{ position: "absolute", left: 60, right: 60, top: y ?? h.y, textAlign: "center" }}>
      <div style={{ fontFamily: F.sans, fontWeight: 500, fontSize: h.sansSize, color: dark ? c("white") : c("ink"), opacity: a, transform: `translateY(${(1 - a) * 18}px)`, filter: `blur(${(1 - a) * 8}px)` }}>{sans}</div>
      <div
        style={{
          fontFamily: F.accent,
          fontStyle: S.fontStyle?.accent === "italic" ? "italic" : "normal",
          fontWeight: h.accentWeight,
          fontSize: big ? h.accentSize * 1.3 : h.accentSize,
          lineHeight: 1.08,
          marginTop: 6,
          color: dark ? c("accentOnDark") : c("accent"),
          opacity: b,
          transform: `translateY(${(1 - b) * 26}px)`,
          filter: `blur(${(1 - b) * 10}px)`,
          clipPath: `inset(-20% ${100 - b * 100}% -20% 0)`,
        }}
      >
        {accent}
      </div>
    </div>
  );
};

export const Card: React.FC<{ x: number; y: number; w: number; h: number; p?: number; r?: number; style?: React.CSSProperties; children?: React.ReactNode }> = ({ x, y, w, h, p = 1, r, style, children }) => {
  const { S } = useTheme();
  const k = S.scene.card;
  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        width: w,
        height: h,
        borderRadius: r ?? k.radius,
        background: k.bg,
        boxShadow: k.shadow,
        border: k.border,
        backdropFilter: k.blur ? `blur(${k.blur}px) saturate(1.25)` : undefined,
        color: k.text,
        opacity: clamp01(p * 1.6),
        transform: `translateY(${(1 - p) * 50}px) scale(${0.9 + 0.1 * p})`,
        ...style,
      }}
    >
      {children}
    </div>
  );
};

const Mono: React.FC<{ children: React.ReactNode; style?: React.CSSProperties }> = ({ children, style }) => {
  const { S, F } = useTheme();
  return <div style={{ fontFamily: F.mono, fontWeight: 500, fontSize: 24, letterSpacing: ".2em", color: S.scene.card.dim, textTransform: "uppercase", ...style }}>{children}</div>;
};

const Frame: React.FC<{ s: any; t: number; big?: boolean; children: React.ReactNode }> = ({ s, t, big, children }) => {
  const { S } = useTheme();
  if (t < s.ta - 0.4 || t >= s.tb + 0.6) return null;
  const p = ease(t, s.ta, 0.35);
  return (
    <AbsoluteFill>
      <Background t={t} />
      {s.header && <Header t={t} t0={s.ta} sans={s.header.sans || ""} accent={s.header.accent || ""} y={big ? 640 : undefined} big={big} />}
      <div style={{ position: "absolute", inset: 0, transform: `translateY(${S.scene.shiftY}px) scale(${1 + (S.scene.zoomIn - 1) * (1 - p)})`, transformOrigin: "50% 45%" }}>{children}</div>
    </AbsoluteFill>
  );
};

const tone = (name: string | undefined, c: (x: string) => string, d = "accent") => c(name || d);

/* ------------------------------------------------------------------ archetypes */

/** Big two-voice title, nothing else. props: {note?} */
export const Title: React.FC<{ s: any; t: number }> = ({ s, t }) => {
  const { S, F } = useTheme();
  const note = ease(t, s.ta + 0.5, 0.5);
  return (
    <Frame s={s} t={t} big>
      {s.props.note && (
        <div style={{ position: "absolute", left: 0, right: 0, top: 1000, textAlign: "center", opacity: note }}>
          <Mono style={{ fontFamily: F.mono, color: S.scene.card.dim }}>{s.props.note}</Mono>
        </div>
      )}
    </Frame>
  );
};

/** A number that counts up. props: {value, suffix?, decimals?, label, sub?, at, tone?} */
export const Stat: React.FC<{ s: any; t: number }> = ({ s, t }) => {
  const { S, F, c } = useTheme();
  const p = s.props;
  const k = pop(t, p.at ?? s.ta, 14);
  const v = (p.value ?? 0) * eo(lin(t, p.at ?? s.ta, (p.at ?? s.ta) + 0.9));
  const txt = v.toFixed(p.decimals ?? 0);
  return (
    <Frame s={s} t={t}>
      <Card x={120} y={690} w={840} h={640} p={k}>
        <div style={{ position: "absolute", left: 0, right: 0, top: 110, textAlign: "center", fontFamily: F.sans, fontWeight: 800, fontSize: 280, letterSpacing: "-0.05em", lineHeight: 1, color: tone(p.tone, c) }}>
          {txt}
          <span style={{ fontSize: 150, marginLeft: 8 }}>{p.suffix || ""}</span>
        </div>
        <div style={{ position: "absolute", left: 40, right: 40, bottom: 120, textAlign: "center", fontFamily: F.sans, fontWeight: 600, fontSize: 48, color: S.scene.card.text }}>{p.label}</div>
        {p.sub && <div style={{ position: "absolute", left: 0, right: 0, bottom: 56, textAlign: "center" }}><Mono>{p.sub}</Mono></div>}
      </Card>
    </Frame>
  );
};

/** Two cards side by side. props: {left:{title,sub?,icon?,at}, right:{...}, between?:"≈"|"vs"|"→", between_at?} */
export const Compare: React.FC<{ s: any; t: number }> = ({ s, t }) => {
  const { S, F, c } = useTheme();
  const { left, right } = s.props;
  const between = s.props.between ?? "vs";
  const eq = ease(t, s.props.between_at ?? (right.at ?? s.ta) + 0.1, 0.4);
  const side = (d: any, x: number) => {
    const k = pop(t, (d.at ?? s.ta) - 0.1, 14);
    const long = (d.title || "").length > 6;
    return (
      <Card x={x} y={740} w={410} h={540} p={k}>
        {d.icon && <div style={{ position: "absolute", left: 0, right: 0, top: 70, display: "flex", justifyContent: "center", color: tone(d.tone, c) }}><Icon name={d.icon} size={104} /></div>}
        <div style={{ position: "absolute", left: 20, right: 20, top: d.icon ? 220 : 140, textAlign: "center", fontFamily: F.sans, fontWeight: 800, fontSize: long ? 64 : 150, letterSpacing: "-0.04em", lineHeight: 1.05, color: S.scene.card.text }}>{d.title}</div>
        {d.sub && <div style={{ position: "absolute", left: 0, right: 0, bottom: 44, textAlign: "center" }}><Mono>{d.sub}</Mono></div>}
      </Card>
    );
  };
  return (
    <Frame s={s} t={t}>
      {side(left, 90)}
      <div style={{ position: "absolute", left: 500, top: 960, width: 80, textAlign: "center", fontFamily: F.accent, fontWeight: 700, fontSize: 80, color: c("accent"), opacity: eq, transform: `scale(${0.6 + 0.4 * eq})` }}>{between}</div>
      {side(right, 580)}
    </Frame>
  );
};

/** Rows with a mark. props: {items:[{text, mark?:"check"|"cross"|"dot", at}]} */
export const List: React.FC<{ s: any; t: number }> = ({ s, t }) => {
  const { S, F, c } = useTheme();
  const items = s.props.items as any[];
  const h = 90 + items.length * 120;
  const p = ease(t, s.ta, 0.4);
  return (
    <Frame s={s} t={t}>
      <Card x={70} y={1010 - h / 2} w={940} h={h} p={p}>
        {items.map((it, i) => {
          const k = ease(t, it.at ?? s.ta + i * 0.3, 0.4);
          const mark = it.mark || "check";
          const col = mark === "cross" ? c("bad") : mark === "check" ? c("good") : c("accent");
          return (
            <div key={i} style={{ position: "absolute", left: 54, top: 60 + i * 120, display: "flex", alignItems: "center", gap: 28, opacity: k, transform: `translateX(${(1 - k) * -40}px)` }}>
              <div style={{ width: 72, height: 72, borderRadius: 36, background: col + "26", color: col, display: "flex", alignItems: "center", justifyContent: "center" }}>
                {mark === "dot" ? <div style={{ width: 22, height: 22, borderRadius: 11, background: col }} /> : <Icon name={mark} size={42} p={lin(t, (it.at ?? s.ta) + 0.05, (it.at ?? s.ta) + 0.4)} />}
              </div>
              <div style={{ fontFamily: F.sans, fontWeight: 600, fontSize: 52, color: S.scene.card.text }}>{it.text}</div>
            </div>
          );
        })}
      </Card>
    </Frame>
  );
};

/** Steps in a row, optionally breaking one link. props: {nodes:[{label, icon?, at}], break?:{after:1, at}} */
export const Chain: React.FC<{ s: any; t: number }> = ({ s, t }) => {
  const { S, F, c } = useTheme();
  const nodes = s.props.nodes as any[];
  const n = nodes.length;
  const brk = s.props.break;
  const bp = brk ? eo(lin(t, brk.at, brk.at + 0.5)) : 0;
  const xs = nodes.map((_, i) => (n === 1 ? 540 : 150 + (i * 780) / (n - 1)));
  return (
    <Frame s={s} t={t}>
      <Card x={40} y={760} w={1000} h={520} p={ease(t, s.ta, 0.4)}>
        {nodes.map((nd, i) => {
          const k = pop(t, nd.at ?? s.ta + i * 0.3, 14);
          const left = brk && i <= brk.after;
          const dx = brk ? (left ? -1 : 1) * 34 * bp : 0;
          const link = i < n - 1 && !(brk && i === brk.after);
          return (
            <React.Fragment key={i}>
              {link && <div style={{ position: "absolute", left: xs[i] - 20 + 70 + dx, top: 200, width: Math.max(10, xs[i + 1] - xs[i] - 140), height: 18, borderRadius: 9, background: c("accent") + "55", opacity: k }} />}
              <div style={{ position: "absolute", left: xs[i] - 70 + 10 + dx, top: 130, width: 140, height: 140, borderRadius: 70, background: i % 2 ? c("accent") : "transparent", border: i % 2 ? "none" : `5px solid ${c("accent")}`, color: i % 2 ? "#fff" : c("accent"), display: "flex", alignItems: "center", justifyContent: "center", transform: `scale(${0.4 + 0.6 * k})`, opacity: clamp01(k * 2), boxShadow: i % 2 ? "0 18px 40px rgba(0,0,0,.25)" : "none" }}>
                <Icon name={nd.icon || "star"} size={64} />
              </div>
              <div style={{ position: "absolute", left: xs[i] - 120 + 10 + dx, top: 300, width: 240, textAlign: "center", fontFamily: F.sans, fontWeight: 600, fontSize: 36, color: S.scene.card.text, opacity: clamp01(k * 2) }}>{nd.label}</div>
            </React.Fragment>
          );
        })}
        {brk && bp > 0.05 && Array.from({ length: 6 }).map((_, i) => (
          <div key={i} style={{ position: "absolute", left: (xs[brk.after] + xs[brk.after + 1]) / 2 + 10 + Math.cos(i * 1.1) * 70 * bp, top: 209 + Math.sin(i * 1.7) * 70 * bp, width: 10, height: 10, borderRadius: 5, background: c("bad"), opacity: 1 - bp }} />
        ))}
      </Card>
    </Frame>
  );
};

/** A marker that slides along a scale. props: {left, right, from:0..1, to:0..1, at, settle_at, note?} */
export const Gauge: React.FC<{ s: any; t: number }> = ({ s, t }) => {
  const { S, F, c } = useTheme();
  const p = s.props;
  const k = eo(lin(t, p.at ?? s.ta + 0.2, p.settle_at ?? s.ta + 1));
  const pos = (p.from ?? 1) + ((p.to ?? 0) - (p.from ?? 1)) * k;
  const done = t > (p.settle_at ?? s.ta + 1);
  return (
    <Frame s={s} t={t}>
      <Card x={70} y={850} w={940} h={340} p={ease(t, s.ta, 0.4)}>
        <div style={{ position: "absolute", left: 60, top: 50 }}><Mono style={{ color: done && (p.to ?? 0) < 0.5 ? c("accent") : undefined }}>{p.left}</Mono></div>
        <div style={{ position: "absolute", right: 60, top: 50 }}><Mono style={{ color: done && (p.to ?? 0) >= 0.5 ? c("accent") : undefined }}>{p.right}</Mono></div>
        <div style={{ position: "absolute", left: 60, right: 60, top: 170, height: 18, borderRadius: 9, background: `linear-gradient(90deg, ${c("accent")}55, ${c("accent")})` }} />
        {Array.from({ length: 11 }).map((_, i) => <div key={i} style={{ position: "absolute", left: 60 + (i * 820) / 10, top: 212, width: 2, height: 18, background: S.scene.card.dim, opacity: 0.6 }} />)}
        <div style={{ position: "absolute", left: 60 + pos * 820 - 42, top: 136, width: 84, height: 84, borderRadius: 42, background: "#fff", boxShadow: `0 14px 34px rgba(0,0,0,.28), 0 0 0 4px ${c("accent")}33`, transform: `scale(${done ? 1 + 0.08 * Math.sin(clamp01((t - (p.settle_at ?? 0)) / 0.3) * Math.PI) : 1})` }} />
        {p.note && <div style={{ position: "absolute", left: 0, right: 0, bottom: 28, textAlign: "center", fontFamily: F.sans, fontWeight: 600, fontSize: 34, color: S.scene.card.text, opacity: ease(t, p.settle_at ?? s.ta + 1, 0.4) }}>{p.note}</div>}
      </Card>
    </Frame>
  );
};

/** Bars growing. props: {bars:[{label, value (0..1), text?, at, hl?}]} */
export const Bars: React.FC<{ s: any; t: number }> = ({ s, t }) => {
  const { S, F, c } = useTheme();
  const bars = s.props.bars as any[];
  const n = bars.length;
  const bw = Math.min(220, (780 - (n - 1) * 40) / n);
  const total = n * bw + (n - 1) * 40;
  return (
    <Frame s={s} t={t}>
      <Card x={110} y={720} w={860} h={700} p={ease(t, s.ta, 0.4)} r={64}>
        <div style={{ position: "absolute", left: 80, right: 80, bottom: 120, height: 3, background: S.scene.card.dim, opacity: 0.4 }} />
        {bars.map((b, i) => {
          const k = eo(lin(t, (b.at ?? s.ta + i * 0.3) - 0.1, (b.at ?? s.ta + i * 0.3) + 0.6));
          const x = 430 - total / 2 + i * (bw + 40);
          const hh = 440 * (b.value ?? 0.5) * k;
          return (
            <React.Fragment key={i}>
              <div style={{ position: "absolute", left: x, bottom: 120, width: bw, height: hh, borderRadius: "22px 22px 0 0", background: b.hl ? `linear-gradient(180deg,${c("accent")},${c("accent")}99)` : c("soft"), boxShadow: b.hl ? `0 20px 50px ${c("accent")}59` : "none" }} />
              {b.text && <div style={{ position: "absolute", left: x, width: bw, bottom: 120 + hh + 12, textAlign: "center", fontFamily: F.sans, fontWeight: 700, fontSize: 40, color: S.scene.card.text, opacity: k }}>{b.text}</div>}
              <div style={{ position: "absolute", left: x - 20, width: bw + 40, bottom: 56, textAlign: "center" }}><Mono style={{ fontSize: 22, color: b.hl ? c("accent") : undefined }}>{b.label}</Mono></div>
            </React.Fragment>
          );
        })}
      </Card>
    </Frame>
  );
};

/** Icon cards. props: {items:[{icon, label, at}]} (2-4 items) */
export const Icons: React.FC<{ s: any; t: number }> = ({ s, t }) => {
  const { S, F, c } = useTheme();
  const items = s.props.items as any[];
  const n = items.length;
  const cols = n <= 3 ? n : 2;
  const rows = Math.ceil(n / cols);
  const cw = cols === 1 ? 560 : cols === 2 ? 440 : 300;
  const ch = rows === 1 ? 560 : 420;
  const gx = 40;
  const x0 = 540 - (cols * cw + (cols - 1) * gx) / 2;
  const y0 = 1010 - (rows * ch + (rows - 1) * gx) / 2;
  return (
    <Frame s={s} t={t}>
      {items.map((it, i) => {
        const k = pop(t, (it.at ?? s.ta + i * 0.3) - 0.1, 14);
        return (
          <Card key={i} x={x0 + (i % cols) * (cw + gx)} y={y0 + Math.floor(i / cols) * (ch + gx)} w={cw} h={ch} p={k}>
            <div style={{ position: "absolute", left: 0, right: 0, top: ch * 0.2, display: "flex", justifyContent: "center", color: tone(it.tone, c) }}><Icon name={it.icon} size={cw > 400 ? 150 : 110} /></div>
            <div style={{ position: "absolute", left: 16, right: 16, bottom: ch * 0.16, textAlign: "center", fontFamily: F.sans, fontWeight: 700, fontSize: cw > 400 ? 50 : 38, lineHeight: 1.1, color: S.scene.card.text }}>{it.label}</div>
          </Card>
        );
      })}
    </Frame>
  );
};

export const SCENE_COMPONENTS: Record<string, React.FC<{ s: any; t: number }>> = { title: Title, stat: Stat, compare: Compare, list: List, chain: Chain, gauge: Gauge, bars: Bars, icons: Icons };
