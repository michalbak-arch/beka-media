"""Warstwa bazowa (b-roll / Bartek) + overlay PNG -> wideo. Użycie: compose.py --frames f1,f2,.. sheet.jpg | compose.py out.mp4"""
import json, re, sys, subprocess, unicodedata, numpy as np, cv2, os
W, H, FPS = 1080, 1920, 30
TL = json.load(open("timeline.json")); S = {s["key"]: s for s in TL["segs"]}
def norm(w):
    w = unicodedata.normalize("NFKD", w.lower().replace("ł", "l")); return re.sub(r"[^a-z0-9]", "", "".join(c for c in w if not unicodedata.combining(c)))
def wt(k, pre, nth=0):
    c = 0
    for w in S[k]["words"]:
        if norm(w[0]).startswith(pre):
            if c == nth: return w[1] - S[k]["start"]
            c += 1
    raise KeyError(pre)
# kawałki: (od, do) lokalnie w segmencie, źródło, start w źródle, prędkość, opcje
P = {
 "v1": [(0, 5.44, "broll/t_tbm_veo.mp4", 0, 1, {}), (5.44, 99, "broll/factory.mp4", 0, 1, {})],
 "v2": [(0, wt("v2", "chinczycy") - 0.05, None, 0, 1, {}), (wt("v2", "chinczycy") - 0.05, wt("v2", "bartek"), "broll/factory.mp4", 3.2, 1, {}),
        (wt("v2", "bartek"), 99, "broll/shenzhen.mp4", 0, 1, {})],
 "c2": [(0, 99, "c2_v.mp4", 0, 1, {"clip": 1})],
 "v3": [(0, 99, "broll/datacenter.mp4", 0, 4 / 4.25, {})],
 "c3": [(0, 99, "c3_v.mp4", 0, 1, {"clip": 1})],
 "v4": [(0, wt("v4", "w", 2) - 0.05, "broll/pendulum.mp4", 0, 1, {}), (wt("v4", "w", 2) - 0.05, 99, "broll/pingpong.mp4", 0, 1, {"zoom": 1.22})],
 "c4": [(0, 99, "c4_v.mp4", 0, 1, {"clip": 1})],
 "c5": [(0, 99, "c5_v.mp4", 0, 1, {"clip": 1})],
 "v5": [(0, wt("v5", "a") - 0.05, "c4_v.mp4", 0, 1, {"dim": 0.45, "blur": 1}), (wt("v5", "a") - 0.05, wt("v5", "mind") - 0.35, "broll/audience.mp4", 0, 1, {}),
        (wt("v5", "mind") - 0.35, 99, None, 0, 1, {})],
}
def reader(src, ss, n, speed):
    if src is None:
        while True: yield np.zeros((H, W, 3), np.uint8)
    vf = f"setpts=PTS/{speed},fps=30,scale={W}:{H}" if speed != 1 else f"fps=30,scale={W}:{H}"
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-ss", str(ss), "-i", src, "-an", "-vf", vf, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    last = np.zeros((H, W, 3), np.uint8)
    while True:
        b = p.stdout.read(W * H * 3)
        if len(b) == W * H * 3: last = np.frombuffer(b, np.uint8).reshape(H, W, 3)
        yield last
def zoomed(img, z, cy=0.5):
    if abs(z - 1) < 1e-3: return img
    ch, cw = H / z, W / z; x0 = (W - cw) / 2; y0 = (H - ch) * cy
    M = np.array([[z, 0, -x0 * z], [0, z, -y0 * z]], np.float32)
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
yy = np.linspace(0, 1, H)[:, None, None]
SHADE = (1 - 0.55 * np.clip((yy - 0.55) / 0.45, 0, 1) ** 1.5 - 0.25 * np.clip((0.18 - yy) / 0.18, 0, 1)).astype(np.float32)
def base_frames():
    for s in TL["segs"]:
        n = s["frames"]; pieces = P[s["key"]]
        for pi, (a, b, src, ss, sp, o) in enumerate(pieces):
            fa = round(a * FPS); fb = min(n, round(b * FPS)); rd = reader(src, ss, fb - fa, sp)
            for f in range(fa, fb):
                img = next(rd); lf = f - fa; pn = fb - fa
                z = o.get("zoom", 1.0)
                if not o.get("clip") and src: z *= 1.0 + 0.06 * lf / max(1, pn)  # powolny dojazd b-rollu
                z *= 1 + 0.10 * (1 - min(1, lf / 6)) ** 2  # punch-in na cięciu
                img = zoomed(img, z, 0.45)
                if o.get("blur"): img = cv2.GaussianBlur(img, (0, 0), 14)
                im = img.astype(np.float32) * SHADE * (o.get("dim", 1.0))
                if lf < 4 and f > 0 and s['key'] != 'v1' or (lf < 4 and pi > 0): im = im + (255 - im) * (0.45 if pi == 0 else 0.25) * (1 - lf / 4)  # błysk
                yield np.clip(im, 0, 255).astype(np.uint8)
def comp(base, f, ovdir):
    ov = cv2.imread(f"{ovdir}/{f:05d}.png", cv2.IMREAD_UNCHANGED)
    if ov is None: return base
    if ov.ndim == 2 or ov.shape[2] == 3: return ov if ov.ndim == 3 else base
    a = ov[:, :, 3:4].astype(np.float32) / 255
    return (base * (1 - a) + ov[:, :, :3] * a).astype(np.uint8)
if __name__ == "__main__":
    if sys.argv[1] == "--frames":
        want = sorted(map(int, sys.argv[2].split(","))); got = []
        for f, b in enumerate(base_frames()):
            if f in want: got.append(comp(b, f, "ovp"))
            if f >= want[-1]: break
        th = [cv2.resize(g, (270, 480)) for g in got]; cols = 8
        rows = [np.hstack(th[i:i + cols] + [np.zeros_like(th[0])] * (cols - len(th[i:i + cols]))) for i in range(0, len(th), cols)]
        cv2.imwrite(sys.argv[3], np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 88])
    else:
        out = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", "30", "-i", "-",
                                "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", sys.argv[1]], stdin=subprocess.PIPE)
        N = TL["frames"]
        for f, b in enumerate(base_frames()):
            if f >= N: break
            out.stdin.write(comp(b, f, "ov").tobytes())
            if f % 300 == 0: print(f, flush=True)
        out.stdin.close(); out.wait()
