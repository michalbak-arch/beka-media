"""Baza dla wersji animowanej: wypowiedzi Bartka w karcie 4:5 na rozmytym tle; sceny animowane z HTML (nieprzezroczyste)."""
import json, sys, subprocess, numpy as np, cv2
W, H, FPS = 1080, 1920, 30
TL = json.load(open("timeline3.json"))
CX, CY, CW, CHh = 40, 200, 1000, 1250
mask = np.zeros((CHh, CW), np.float32); cv2.rectangle(mask, (0, 0), (CW - 1, CHh - 1), 1, -1)
r = 40; mask[:] = 0; cv2.rectangle(mask, (r, 0), (CW - r, CHh), 1, -1); cv2.rectangle(mask, (0, r), (CW, CHh - r), 1, -1)
for (x, y) in [(r, r), (CW - r, r), (r, CHh - r), (CW - r, CHh - r)]: cv2.circle(mask, (x, y), r, 1, -1)
mask = cv2.GaussianBlur(mask, (3, 3), 0)[:, :, None]
def reader(src):
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", src, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    last = None
    while True:
        b = p.stdout.read(CW * CHh * 3)
        if len(b) == CW * CHh * 3: last = np.frombuffer(b, np.uint8).reshape(CHh, CW, 3)
        yield last
def clip_frame(card, lf):
    small = cv2.resize(card, (200, 250)); bg = cv2.resize(cv2.GaussianBlur(small, (0, 0), 6), (W, H)).astype(np.float32) * 0.38
    bg += np.array([16, 20, 11], np.float32) * 0.6
    k = 1 - (1 - min(1, lf / 10)) ** 3  # wejście karty
    s = 0.9 + 0.1 * k; cw, ch = int(CW * s), int(CHh * s)
    c = cv2.resize(card, (cw, ch)).astype(np.float32); m = cv2.resize(mask, (cw, ch))[:, :, None]
    x0 = (W - cw) // 2; y0 = CY + (CHh - ch) // 2 + int(80 * (1 - k))
    roi = bg[y0:y0 + ch, x0:x0 + cw]; bg[y0:y0 + ch, x0:x0 + cw] = roi * (1 - m) + c * m
    cv2.rectangle(bg, (x0 - 1, y0 - 1), (x0 + cw, y0 + ch), (166, 240, 138), 0)  # bez obrysu
    if lf < 10: bg *= (0.5 + 0.5 * k)
    return bg
def base_frames():
    last = np.zeros((H, W, 3), np.float32)
    for s in TL["segs"]:
        if s["kind"] == "vo":
            for f in range(s["frames"]): yield (last * 0.7).astype(np.uint8)
        else:
            rd = reader(f"{s['key']}_card.mp4")
            for f in range(s["frames"]):
                fr = next(rd); last = clip_frame(fr, f); yield np.clip(last, 0, 255).astype(np.uint8)
def comp(base, f, ovdir):
    ov = cv2.imread(f"{ovdir}/{f:05d}.png", cv2.IMREAD_UNCHANGED)
    if ov is None: return base
    if ov.shape[2] == 3: return ov
    a = ov[:, :, 3:4].astype(np.float32) / 255
    return (base * (1 - a) + ov[:, :, :3] * a).astype(np.uint8)
if __name__ == "__main__":
    ovdir = sys.argv[2] if len(sys.argv) > 2 else "ov3"
    if sys.argv[1] == "--frames":
        want = sorted(map(int, sys.argv[3].split(","))); got = []
        for f, b in enumerate(base_frames()):
            if f in want: got.append(comp(b, f, ovdir))
            if f >= want[-1]: break
        th = [cv2.resize(g, (240, 427)) for g in got]; cols = 11
        rows = [np.hstack(th[i:i + cols] + [np.zeros_like(th[0])] * (cols - len(th[i:i + cols]))) for i in range(0, len(th), cols)]
        cv2.imwrite(sys.argv[4], np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 88]); sys.exit()
    out = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", "30", "-i", "-",
                            "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", sys.argv[1]], stdin=subprocess.PIPE)
    for f, b in enumerate(base_frames()):
        if f >= TL["frames"]: break
        out.stdin.write(comp(b, f, ovdir).tobytes())
    out.stdin.close(); out.wait()
