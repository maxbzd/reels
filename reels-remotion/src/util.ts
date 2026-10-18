import { Easing, spring } from "remotion";

export const FPS = 30;
export const clamp01 = (x: number) => Math.min(1, Math.max(0, x));
export const eo = Easing.bezier(0.16, 1, 0.3, 1);
export const easeIO = (x: number) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
/** progress 0..1 of an ease-out starting at t0 lasting d seconds */
export const ease = (t: number, t0: number, d = 0.45) => eo(clamp01((t - t0) / d));
export const lin = (t: number, t0: number, t1: number) => clamp01((t - t0) / (t1 - t0));
/** soft spring pop starting at t0 (seconds) */
export const pop = (t: number, t0: number, damping = 15) =>
  spring({ frame: Math.round((t - t0) * FPS), fps: FPS, config: { damping, stiffness: 180, mass: 0.7 } });
export const norm = (s: string) => s.toLowerCase().replace(/^[^\p{L}\p{N}]+|[^\p{L}\p{N}]+$/gu, "");
