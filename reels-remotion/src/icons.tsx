import React from "react";
import { clamp01 } from "./util";

/** Stroke icons drawn in code (48x48). Use by name in plans: "mic", "bubble", "lock", ... */
const S: React.FC<{ size: number; children: React.ReactNode; fill?: string }> = ({ size, children, fill = "none" }) => (
  <svg width={size} height={size} viewBox="0 0 48 48" fill={fill} stroke="currentColor" strokeWidth={3.4} strokeLinecap="round" strokeLinejoin="round">
    {children}
  </svg>
);

type P = { size?: number; p?: number };
const ICONS: Record<string, React.FC<{ size: number; p: number }>> = {
  check: ({ size, p }) => (
    <S size={size}>
      <path d="M10 25 L21 35 L39 14" strokeDasharray={50} strokeDashoffset={50 * (1 - p)} />
    </S>
  ),
  cross: ({ size, p }) => (
    <S size={size}>
      <path d="M13 13 L35 35" strokeDasharray={32} strokeDashoffset={32 * (1 - clamp01(p * 2))} />
      <path d="M35 13 L13 35" strokeDasharray={32} strokeDashoffset={32 * (1 - clamp01(p * 2 - 0.6))} />
    </S>
  ),
  lock: ({ size }) => (
    <S size={size}>
      <rect x="10" y="21" width="28" height="19" rx="5" />
      <path d="M16 21 V15 a8 8 0 0 1 16 0 V21" />
      <circle cx="24" cy="30" r="2.2" fill="currentColor" />
    </S>
  ),
  mic: ({ size }) => (
    <S size={size}>
      <rect x="17" y="6" width="14" height="23" rx="7" />
      <path d="M10 22 a14 14 0 0 0 28 0 M24 36 V43 M17 43 H31" />
    </S>
  ),
  bubble: ({ size }) => (
    <S size={size}>
      <path d="M8 9 H40 a3 3 0 0 1 3 3 V30 a3 3 0 0 1 -3 3 H22 L13 41 V33 H8 a3 3 0 0 1 -3 -3 V12 a3 3 0 0 1 3 -3 Z" />
    </S>
  ),
  pin: ({ size }) => (
    <S size={size}>
      <path d="M24 43 C14 31 10 25 10 19 a14 14 0 0 1 28 0 C38 25 34 31 24 43 Z" />
      <circle cx="24" cy="19" r="5" />
    </S>
  ),
  clock: ({ size }) => (
    <S size={size}>
      <circle cx="24" cy="24" r="18" />
      <path d="M24 13 V24 L32 29" />
    </S>
  ),
  send: ({ size }) => (
    <S size={size}>
      <path d="M24 38 V12 M13 22 L24 11 L35 22" />
    </S>
  ),
  head: ({ size }) => (
    <S size={size}>
      <path d="M14 42 V35 C8 31 6 26 7 21 C8 11 15 5 24 5 C34 5 41 12 41 21 C41 25 39 27 38 30 L41 31 V35 H36 V42 Z" />
    </S>
  ),
  arrow: ({ size }) => (
    <S size={size}>
      <path d="M6 24 H40 M30 13 L41 24 L30 35" />
    </S>
  ),
  star: ({ size }) => (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="currentColor">
      <path d="M24 2 C26 17 31 22 46 24 C31 26 26 31 24 46 C22 31 17 26 2 24 C17 22 22 17 24 2 Z" />
    </svg>
  ),
  drop: ({ size }) => (
    <S size={size}>
      <path d="M24 5 C24 5 9 22 9 31 a15 15 0 0 0 30 0 C39 22 24 5 24 5Z" />
    </S>
  ),
  heart: ({ size }) => (
    <S size={size}>
      <path d="M24 41 s-16-9.5-18-20 A9.5 9.5 0 0 1 24 14 A9.5 9.5 0 0 1 42 21 C40 31.5 24 41 24 41z" />
    </S>
  ),
  bolt: ({ size }) => (
    <S size={size}>
      <path d="M27 4 L10 27 H23 L21 44 L38 20 H25 Z" />
    </S>
  ),
  globe: ({ size }) => (
    <S size={size}>
      <circle cx="24" cy="24" r="18" />
      <path d="M6 24 H42 M24 6 C16 14 16 34 24 42 C32 34 32 14 24 6" />
    </S>
  ),
  book: ({ size }) => (
    <S size={size}>
      <path d="M8 9 H21 a3 3 0 0 1 3 3 V41 a3 3 0 0 0 -3 -3 H8 Z M40 9 H27 a3 3 0 0 0 -3 3 V41 a3 3 0 0 1 3 -3 H40 Z" />
    </S>
  ),
  note: ({ size }) => (
    <S size={size}>
      <path d="M18 36 V10 L38 6 V32" />
      <circle cx="13" cy="37" r="6" />
      <circle cx="33" cy="33" r="6" />
    </S>
  ),
  user: ({ size }) => (
    <S size={size}>
      <circle cx="24" cy="16" r="8" />
      <path d="M8 42 C8 32 15 27 24 27 C33 27 40 32 40 42" />
    </S>
  ),
  play: ({ size }) => (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="currentColor">
      <path d="M16 9 L38 24 L16 39 Z" />
    </svg>
  ),
  eye: ({ size }) => (
    <S size={size}>
      <path d="M3 24 C9 13 17 9 24 9 C31 9 39 13 45 24 C39 35 31 39 24 39 C17 39 9 35 3 24Z" />
      <circle cx="24" cy="24" r="6" />
    </S>
  ),
  target: ({ size }) => (
    <S size={size}>
      <circle cx="24" cy="24" r="18" />
      <circle cx="24" cy="24" r="10" />
      <circle cx="24" cy="24" r="2.5" fill="currentColor" />
    </S>
  ),
  flask: ({ size }) => (
    <S size={size}>
      <path d="M18 5 H30 M20 5 V19 L7 40 a3 3 0 0 0 3 5 H38 a3 3 0 0 0 3 -5 L28 19 V5" />
    </S>
  ),
};

export const ICON_NAMES = Object.keys(ICONS);
export const Icon: React.FC<P & { name: string }> = ({ name, size = 48, p = 1 }) => {
  const I = ICONS[name] || ICONS.star;
  return <I size={size} p={p} />;
};
