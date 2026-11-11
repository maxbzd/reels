"""'The breakup' as a film: real footage of a man scrolling Reels on his phone, the camera flies into the
screen when the message arrives, and the chat (breakup/) plays on the full-screen phone UI.

    python3 film.py                 full render -> ../out/breakup_film.mp4 (+ _no_music)
    python3 film.py --stills 2,5,8  stills
"""
import math
import os
import subprocess
import sys
from multiprocessing import Pool

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "breakup"))
import comp                     # noqa: E402
from comp import W, H, CH, PAD  # noqa: E402
import render as chat           # noqa: E402  (the phone UI of the chat reel)
import script as CS             # noqa: E402

OUT = os.path.join(HERE, "..", "out")
FPS = 30

# ------------------------------------------------------------------ timeline (film seconds)
A_END = 4.4          # wide shot -> match cut to the close-up
NOTIF_T = 7.25       # the message arrives (banner slides in)
PUSH0, PUSH1 = 7.95, 9.25     # camera flies into the screen
TAP_T = 9.50         # finger taps the banner
OPEN_T = 9.55        # chat opens
CHAT_SHIFT = 0.8     # chat starts at its t=0.8 (first bubble already on screen)
TOTAL = OPEN_T + (CS.DURATION - CHAT_SHIFT)


def chat_t(t):
    return t - OPEN_T + CHAT_SHIFT


# the first message is the one in the notification -> already on screen when the chat opens
CS.MSGS[1].update(type_start=-6.0, show=-5.0)

# ------------------------------------------------------------------ tracked screen quads (footage coords)
Q164 = {0: [(684, 46), (830, 92), (766, 387), (632, 337)], 2: [(682, 40), (824, 84), (763, 384), (625, 337)],
        8: [(674, 41), (817, 84), (758, 387), (635, 342)], 10: [(680, 40), (820, 84), (758, 385), (632, 342)]}
Q62 = {3.0: [(557, 212), (637, 232), (624, 392), (551, 367)], 4.5: [(565, 212), (641, 228), (628, 388), (551, 364)],
       6.0: [(558, 212), (635, 230), (621, 390), (548, 367)], 7.5: [(563, 211), (640, 226), (625, 388), (552, 363)]}
KEYS_B = [(t, np.array(q, np.float32)) for t, q in sorted(Q164.items())]
KEYS_A = [(t, np.array(q, np.float32)) for t, q in sorted(Q62.items())]
A_CLIP0, B_CLIP0 = 3.0, 0.5            # where in the footage each shot starts

G = {}


def init():
    G["A"] = comp.Footage(os.path.join(HERE, "assets/footage/wide_62.mp4"), A_CLIP0, A_CLIP0 + A_END + 0.4)
    G["B"] = comp.Footage(os.path.join(HERE, "assets/footage/close_164.mp4"), B_CLIP0, B_CLIP0 + (A_END and (OPEN_T - A_END)) + 0.4)
    G["ov"] = np.asarray(Image.open(os.path.join(HERE, "assets/ui/reels_overlay.png")).convert("RGBA"), np.float32)
    G["banner"] = make_banner()


# ------------------------------------------------------------------ phone UI canvas
def make_banner():
    SS = 3
    w, h = 960, 168
    img = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, w * SS - 1, h * SS - 1), radius=44 * SS, fill=(34, 34, 40, 232), outline=(255, 255, 255, 40), width=2 * SS)
    av = chat.avatar_layer(104)
    avi = Image.fromarray(np.dstack([av[0], av[1] * 255]).astype(np.uint8), "RGBA").resize((104 * SS, 104 * SS), Image.LANCZOS)
    img.alpha_composite(avi, (30 * SS, 32 * SS))
    f1 = ImageFont.truetype(chat.INTER_SB, 40 * SS)
    f2 = ImageFont.truetype(chat.INTER_M, 38 * SS)
    f3 = ImageFont.truetype(chat.INTER_M, 30 * SS)
    d.text((158 * SS, 62 * SS), "Instagram", font=f1, fill=(255, 255, 255, 255), anchor="lm")
    d.text((158 * SS, 112 * SS), "hey. you up?", font=f2, fill=(225, 225, 232, 255), anchor="lm")
    d.text(((w - 36) * SS, 62 * SS), "now", font=f3, fill=(170, 170, 178, 255), anchor="rm")
    img = img.resize((w, h), Image.LANCZOS)
    return np.asarray(img, np.float32)


_feed_cache = {}


def feed_canvas(t):
    """Reels feed (clips + UI overlay + status bar) at film time t -> float32 1080x2200"""
    n = int(min(max(round(t * 30) + 1, 1), 300))
    if n not in _feed_cache:
        im = cv2.imread(os.path.join(HERE, "assets/ui/feed", f"{n:04d}.jpg"))
        _feed_cache.clear()
        _feed_cache[n] = cv2.cvtColor(im, cv2.COLOR_BGR2RGB).astype(np.float32)
    f = _feed_cache[n].copy()
    ov = G["ov"]
    a = ov[..., 3:4] / 255.0
    f = f * (1 - a) + ov[..., :3] * a
    view = f[PAD:PAD + H]                      # status bar, same as the chat's
    chat.blit(view, chat.text_arr("12:25", chat.INTER_SB, 42, (255, 255, 255)), 96, 108, 1.0, "l")
    chat.blit(view, chat._static.get("sig") or chat.signal_layer(), W - 270, 108, 1.0, "r")
    chat.blit(view, chat.text_arr("5G", chat.INTER_SB, 34, (255, 255, 255)), W - 258, 108, 1.0, "l")
    chat.blit(view, chat._static.get("bat") or chat.battery_layer(41), W - 80, 108, 1.0, "r")
    return f


def spring(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - math.exp(-7 * x) * math.cos(9 * x)


def ui_canvas(t):
    f = feed_canvas(t)
    if t >= NOTIF_T:
        b = G["banner"]
        k = (t - NOTIF_T) / 0.55
        y = PAD + 150 - (1 - spring(k)) * 260
        if t > TAP_T - 0.05:
            y -= 0
        x0, y0 = 60, int(y)
        h, w = b.shape[:2]
        reg = f[y0:y0 + h, x0:x0 + w]
        if reg.shape[0] == h:
            blur = cv2.GaussianBlur(reg, (0, 0), 22) * 0.55
            al = b[..., 3:4] / 255.0
            f[y0:y0 + h, x0:x0 + w] = blur * (1 - al * 0.0) * (1 - al) + b[..., :3] * al + reg * 0.0
            f[y0:y0 + h, x0:x0 + w] = np.where(al > 0.02, blur * (1 - al) + b[..., :3] * al, reg)
        # finger taps the banner
        if TAP_T - 0.22 < t < TAP_T + 0.2:
            p = (t - (TAP_T - 0.22)) / 0.22
            r = int(46 * (1 - 0.2 * comp.ease_io(min(p, 1)))) 
            cv2.circle(f, (520, PAD + 232), r, (255, 255, 255), -1, cv2.LINE_AA)
            f[PAD + 232 - r - 2:PAD + 232 + r + 2, 520 - r - 2:520 + r + 2] *= 1.0
    if t >= OPEN_T - 0.02:
        c = np.zeros((CH, W, 3), np.float32)
        fr = chat.render(int(round(chat_t(t) * FPS)))
        c[PAD:PAD + H] = fr
        u = comp.ease_io((t - (OPEN_T - 0.02)) / 0.22)
        f = f * (1 - u) + c * u
    return f


# ------------------------------------------------------------------ camera
def ease(u):
    return comp.ease_io(u)


def render_film_frame(fi):
    t = fi / FPS
    if t >= PUSH1 + 0.02:                       # the phone UI fills the frame: no footage left
        f = ui_canvas(t)[PAD:PAD + H]
        if t < OPEN_T + 0.4:                    # keep a hint of the finished push (soft vignette fade)
            pass
        return np.clip(f, 0, 255).astype(np.uint8)

    canvas = ui_canvas(t)
    if t < A_END:
        u = t / A_END
        foot, keys = G["A"], KEYS_A
        ct = A_CLIP0 + t
        cx = 300 + (597 - 300) * ease(u)
        cy = 340 + (300 - 340) * ease(u)
        zoom = 1.0 + 0.85 * ease(u)
        e = 0.0
        night = 0.45
    else:
        foot, keys = G["B"], KEYS_B
        ct = B_CLIP0 + (t - A_END)
        u = (t - A_END) / (PUSH1 - A_END)
        cx = 731 + 4 * math.sin(t * 1.3)
        cy = 214 + 3 * math.cos(t * 1.1)
        zoom = 1.02 + 0.10 * u
        e = comp.ease_io((t - PUSH0) / (PUSH1 - PUSH0)) if t > PUSH0 else 0.0
        night = 0.45
    frame = foot.at(ct)
    q = comp.grow_quad(comp.interp_quad(keys, ct), 1.045)
    S = comp.frame_map(cx, cy, zoom, roll=0.5 * math.sin(t * 0.9))
    moving = 0.0 < e < 1.0
    e_next = comp.ease_io((t + 1 / 60 - PUSH0) / (PUSH1 - PUSH0)) if moving else e
    img = comp.render_shot(frame, q, canvas, S, e, bg_grade=lambda b: comp.grade(b, night=night),
                           glow=0.32, samples=3 if moving else 1, e_next=e_next)
    # finishing (fades out as the UI takes over)
    k = 1 - e
    img = comp.sharpen(img, 0.45 * k)
    img = comp.vignette(img, 0.55 * k)
    img = comp.grain(img, 3.4 * k)
    if t < 0.5:
        img = img * comp.ease_io(t / 0.5)
    return np.clip(img, 0, 255).astype(np.uint8)


# ------------------------------------------------------------------ main
def mux(video, wav, out):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-af", "loudnorm=I=-14:TP=-2:LRA=9,alimiter=limit=0.89:level=disabled", "-c:a", "aac", "-b:a", "192k",
                    "-t", f"{TOTAL:.3f}", "-movflags", "+faststart", out], check=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    init()
    nframes = int(round(TOTAL * FPS))
    if len(sys.argv) > 2 and sys.argv[1] == "--stills":
        d = os.path.join(OUT, "stills_f")
        os.makedirs(d, exist_ok=True)
        for tt in sys.argv[2].split(","):
            Image.fromarray(render_film_frame(int(round(float(tt) * FPS)))).save(os.path.join(d, f"f_{float(tt):05.2f}.png"))
            print("saved", tt, flush=True)
        return
    video = os.path.join(OUT, "_film_video.mp4")
    if "--audio-only" not in sys.argv:
        enc = subprocess.Popen(
            ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
             "-i", "-", "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p", "-c:v", "libx264", "-preset", "medium",
             "-crf", "18", "-maxrate", "16M", "-bufsize", "32M", "-colorspace", "bt709", "-color_primaries", "bt709",
             "-color_trc", "bt709", "-an", video], stdin=subprocess.PIPE)
        with Pool(4) as pool:
            for i, fr in enumerate(pool.imap(render_film_frame, range(nframes), chunksize=2)):
                enc.stdin.write(fr.tobytes())
                if i % 60 == 0:
                    print("frame", i, "/", nframes, flush=True)
        enc.stdin.close()
        enc.wait()
    import audio_film
    wav = os.path.join(OUT, "_film_mix.wav")
    audio_film.build_mix(wav, True)
    mux(video, wav, os.path.join(OUT, "breakup_film.mp4"))
    wav2 = os.path.join(OUT, "_film_mix_nomusic.wav")
    audio_film.build_mix(wav2, False)
    mux(video, wav2, os.path.join(OUT, "breakup_film_no_music.mp4"))
    print("done")


if __name__ == "__main__":
    main()
