"""Track the phone screen (4 corners) through a clip: bright screen vs dark bezel, per-frame contour -> quad,
then temporal smoothing.  Usage: track.py clip.mp4 out.npy x0 y0 x1 y1 [debug_dir]"""
import sys, subprocess, numpy as np, cv2, os
clip, out = sys.argv[1], sys.argv[2]
x0, y0, x1, y1 = map(int, sys.argv[3:7])
dbg = sys.argv[7] if len(sys.argv) > 7 else None
w, h = 1280, 720
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", clip, "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                     capture_output=True).stdout
frames = np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3)
print("frames", len(frames))

def order(pts):
    pts = np.array(pts, np.float32)
    s = pts.sum(1); d = np.diff(pts, axis=1)[:, 0]
    return np.array([pts[np.argmin(s)], pts[np.argmin(d)], pts[np.argmax(s)], pts[np.argmax(d)]], np.float32)  # tl, tr, br, bl

quads, ok = [], []
prev = None
for i, fr in enumerate(frames):
    roi = fr[y0:y1, x0:x1]
    g = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    g = cv2.GaussianBlur(g, (5, 5), 0)
    # the phone body is the darkest big blob in the ROI; the screen is inside it.  Find the body first.
    _, body = cv2.threshold(g, 55, 255, cv2.THRESH_BINARY_INV)
    body = cv2.morphologyEx(body, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    cnts, _ = cv2.findContours(body, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = [c for c in cnts if cv2.contourArea(c) > 2500]
    best = None
    for c in cnts:
        r = cv2.minAreaRect(c)
        (cx, cy), (rw, rh), ang = r
        ar = max(rw, rh) / max(1, min(rw, rh))
        if 1.6 < ar < 3.2:
            sc = cv2.contourArea(c)
            if prev is not None:
                sc -= 4 * np.linalg.norm(np.array([cx + x0, cy + y0]) - prev)
            if best is None or sc > best[0]:
                best = (sc, r)
    if best is None:
        quads.append(quads[-1] if quads else np.zeros((4, 2), np.float32)); ok.append(False); continue
    box = cv2.boxPoints(best[1]) + np.array([x0, y0], np.float32)
    q = order(box)
    prev = q.mean(0)
    quads.append(q); ok.append(True)
quads = np.array(quads)
print("detected", int(np.sum(ok)), "/", len(ok))
# temporal smoothing (median then gaussian) per coordinate
from scipy.ndimage import median_filter, gaussian_filter1d
sm = median_filter(quads, size=(7, 1, 1), mode="nearest")
sm = gaussian_filter1d(sm, 2.0, axis=0, mode="nearest")
np.save(out, sm)
if dbg:
    os.makedirs(dbg, exist_ok=True)
    for i in range(0, len(frames), max(1, len(frames) // 8)):
        im = frames[i].copy()
        cv2.polylines(im, [sm[i].astype(np.int32)], True, (0, 255, 0), 3)
        for k, p in enumerate(sm[i]):
            cv2.putText(im, str(k), tuple(p.astype(int)), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
        cv2.rectangle(im, (x0, y0), (x1, y1), (255, 0, 0), 1)
        cv2.imwrite(os.path.join(dbg, f"{i:04d}.jpg"), cv2.resize(im, (640, 360)))
