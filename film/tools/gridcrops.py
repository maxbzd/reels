import sys, subprocess, numpy as np, cv2
clip, tag, x0, y0, x1, y1, scale = sys.argv[1], sys.argv[2], *map(int, sys.argv[3:7]), float(sys.argv[7])
times = [float(t) for t in sys.argv[8:]]
OUT = "/tmp/claude-0/-home-user-reels/6bcf1910-c2b5-5875-a0ad-c792921ff660/scratchpad/kf"
tiles = []
for t in times:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", clip, "-frames:v", "1", "-vf", "scale=1280:720", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(720, 1280, 3)
    c = fr[y0:y1, x0:x1].copy()
    c = cv2.resize(c, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    step = 20
    for gx in range((x0 // step + 1) * step, x1, step):
        X = int((gx - x0) * scale); major = gx % 100 == 0
        cv2.line(c, (X, 0), (X, c.shape[0]), (0, 255, 255) if major else (90, 90, 90), 1)
        if major: cv2.putText(c, str(gx), (X + 2, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
    for gy in range((y0 // step + 1) * step, y1, step):
        Y = int((gy - y0) * scale); major = gy % 100 == 0
        cv2.line(c, (0, Y), (c.shape[1], Y), (0, 255, 255) if major else (90, 90, 90), 1)
        if major: cv2.putText(c, str(gy), (2, Y - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
    cv2.putText(c, f"t={t}", (c.shape[1] - 90, c.shape[0] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    tiles.append(c)
for i in range(0, len(tiles), 2):
    row = np.hstack(tiles[i:i + 2])
    cv2.imwrite(f"{OUT}/{tag}_{i // 2}.jpg", row)
print("ok", len(tiles))
