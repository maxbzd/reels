import React, { createContext, useContext, useMemo } from "react";
import { delayRender, continueRender, staticFile } from "remotion";
import { loadFont as inter } from "@remotion/google-fonts/InterTight";
import { loadFont as playfair } from "@remotion/google-fonts/PlayfairDisplay";
import { loadFont as cormorant } from "@remotion/google-fonts/CormorantGaramond";
import { loadFont as plex } from "@remotion/google-fonts/IBMPlexMono";
import { loadFont as onest } from "@remotion/google-fonts/Onest";
import { loadFont as manrope } from "@remotion/google-fonts/Manrope";
import { loadFont as unbounded } from "@remotion/google-fonts/Unbounded";
import { loadFont as russo } from "@remotion/google-fonts/RussoOne";
import { loadFont as oswald } from "@remotion/google-fonts/Oswald";
import { loadFont as rubikMono } from "@remotion/google-fonts/RubikMonoOne";
import { loadFont as caveat } from "@remotion/google-fonts/Caveat";
import { loadFont as lora } from "@remotion/google-fonts/Lora";

/** Montserrat is served from public/fonts (variable woff2): the sandbox's Chrome cannot reach fonts.gstatic.com. */
const montserrat = (_style: string, _o: any) => {
  const family = "Montserrat Local";
  if (typeof document !== "undefined" && !(window as any).__montLoaded) {
    (window as any).__montLoaded = true;
    const h = delayRender("montserrat");
    const range = { cyrillic: "U+0301,U+0400-045F,U+0490-0491,U+04B0-04B1,U+2116", latin: "U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD" };
    Promise.all((["cyrillic", "latin"] as const).map((k) => {
      const f = new FontFace(family, `url(${staticFile(`fonts/montserrat-${k}.woff2`)}) format("woff2")`, { weight: "500 900", style: "normal", unicodeRange: range[k] });
      return f.load().then((l) => document.fonts.add(l));
    })).then(() => continueRender(h)).catch((e) => { console.error(e); continueRender(h); });
  }
  return { fontFamily: family };
};

/** Fonts a style can name. All of them have Cyrillic. To add one: import its loader and add a line (weights it really has). */
type Loader = (italic: boolean) => string;
const L = (fn: any, normal: string[], italic: string[] = []): Loader => (it) => {
  const weights = it ? italic : normal;
  const style = it && italic.length ? "italic" : "normal";
  try {
    return fn(style, { weights: weights.length ? weights : normal, subsets: ["cyrillic", "latin"] }).fontFamily;
  } catch (e) {
    return fn("normal", { weights: [normal[0]], subsets: ["cyrillic", "latin"] }).fontFamily;
  }
};
export const FONT_REGISTRY: Record<string, Loader> = {
  InterTight: L(inter, ["400", "500", "600", "700", "800"]),
  Montserrat: L(montserrat, ["500", "600", "700", "800", "900"], ["700", "800", "900"]),
  PlayfairDisplay: L(playfair, ["500", "600", "700", "800"], ["500", "600", "700", "800"]),
  CormorantGaramond: L(cormorant, ["400", "500", "600", "700"], ["400", "500", "600"]),
  IBMPlexMono: L(plex, ["400", "500", "600"], ["400", "500"]),
  Onest: L(onest, ["400", "500", "600", "700", "800", "900"]),
  Manrope: L(manrope, ["400", "500", "600", "700", "800"]),
  Unbounded: L(unbounded, ["500", "700", "900"]),
  RussoOne: L(russo, ["400"]),
  Oswald: L(oswald, ["500", "600", "700"]),
  RubikMonoOne: L(rubikMono, ["400"]),
  Caveat: L(caveat, ["500", "700"]),
  Lora: L(lora, ["400", "500", "600", "700"], ["400", "500", "600", "700"]),
};

export type Theme = {
  S: any; // the merged style.json
  F: { sans: string; accent: string; mono: string };
  C: Record<string, string>;
  layout: any;
  c: (x: string) => string;
};
const Ctx = createContext<Theme | null>(null);
export const useTheme = (): Theme => {
  const t = useContext(Ctx);
  if (!t) throw new Error("no theme");
  return t;
};

export const ThemeProvider: React.FC<{ style: any; layout: any; children: React.ReactNode }> = ({ style, layout, children }) => {
  const theme = useMemo<Theme>(() => {
    const pick = (name: string, italic: boolean) => (FONT_REGISTRY[name] || FONT_REGISTRY.InterTight)(italic);
    const F = {
      sans: pick(style.fonts.sans, false),
      accent: pick(style.fonts.accent, style.fontStyle?.accent === "italic"),
      mono: pick(style.fonts.mono, false),
    };
    const C = style.colors as Record<string, string>;
    return { S: style, F, C, layout, c: (x: string) => C[x] ?? x };
  }, [style, layout]);
  return <Ctx.Provider value={theme}>{children}</Ctx.Provider>;
};
