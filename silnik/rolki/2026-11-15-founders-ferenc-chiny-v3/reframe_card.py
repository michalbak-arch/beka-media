"""Kadr 9:16 z wypowiedzi Bartka: śledzenie twarzy (haar), wygładzenie, punch-in na każdym cięciu."""
import cv2, json, subprocess, numpy as np, sys
W, H = 1000, 1250
keep = json.load(open("keep.json"))
casc = cv2.CascadeClassifier("/home/claude/haar/haarcascade_frontalface_default.xml")
prof = cv2.CascadeClassifier("/home/claude/haar/haarcascade_profileface.xml")
def frames(path):
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", path, "-vf", "fps=30", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
    while True:
        b = p.stdout.read(1280 * 720 * 3)
        if len(b) < 1280 * 720 * 3: break
        yield np.frombuffer(b, np.uint8).reshape(720, 1280, 3)
for k in sys.argv[1:]:
    fr = list(frames(f"{k}x.mov")); n = len(fr)
    cx = np.full(n, np.nan); cy = np.full(n, np.nan)
    for i in range(0, n, 3):
        g = cv2.cvtColor(fr[i], cv2.COLOR_BGR2GRAY)
        g2 = g.copy(); g2[:, 1000:] = 0  # bez znaku wodnego
        f = list(casc.detectMultiScale(g2, 1.1, 6, minSize=(80, 80))) + list(prof.detectMultiScale(g2, 1.1, 6, minSize=(80, 80)))
        if f:
            x, y, w, h = max(f, key=lambda r: r[2] * r[3]); cx[i] = x + w / 2; cy[i] = y + h / 2
    # cięcia kamery: osobne wygładzanie w każdym ujęciu
    cuts = [0]
    for i in range(1, n):
        if np.abs(fr[i].astype(int)[::8, ::8] - fr[i - 1].astype(int)[::8, ::8]).mean() > 25: cuts.append(i)
    cuts.append(n)
    sx = np.zeros(n); sy = np.zeros(n)
    for a, b in zip(cuts[:-1], cuts[1:]):
        seg = cx[a:b]; segy = cy[a:b]; ok = ~np.isnan(seg)
        if ok.sum() == 0: sx[a:b] = 640; sy[a:b] = 300; continue
        idx = np.arange(b - a)
        mx = np.median(seg[ok]); my = np.median(segy[ok])
        # odrzuć skoki, interpoluj, mocno wygładź (kamera prawie statyczna)
        good = ok & (np.abs(seg - mx) < 120)
        xs = np.interp(idx, idx[good], seg[good]) if good.any() else np.full(b - a, mx)
        ys = np.interp(idx, idx[good], segy[good]) if good.any() else np.full(b - a, my)
        kern = np.ones(31) / 31
        sx[a:b] = np.convolve(np.pad(xs, 15, mode="edge"), kern, "valid"); sy[a:b] = np.convolve(np.pad(ys, 15, mode="edge"), kern, "valid")
    # granice wyciętych fragmentów (jump cuty) -> naprzemienny zoom
    jc = [0]; acc = 0
    for a, b in keep[k][:-1]: acc += b - a; jc.append(int(round(acc * 30)))
    jc = sorted(set(jc + cuts[:-1]))
    zoom = np.ones(n)
    for j, a in enumerate(jc):
        b = jc[j + 1] if j + 1 < len(jc) else n
        z0 = 1.0 if j % 2 == 0 else 1.12
        for i in range(a, b): zoom[i] = z0 * (1 + 0.025 * (i - a) / max(1, b - a))  # powolny dojazd
    out = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", "30", "-i", "-",
                            "-c:v", "libx264", "-crf", "14", "-preset", "medium", "-pix_fmt", "yuv420p", f"{k}_card.mp4"], stdin=subprocess.PIPE)
    for i in range(n):
        ch = 720 / zoom[i]; cw = ch * 4 / 5
        x0 = np.clip(sx[i] - cw / 2, 0, 1280 - cw); y0 = np.clip(sy[i] - ch * 0.40, 0, 720 - ch)
        crop = fr[i][int(y0):int(y0 + ch), int(x0):int(x0 + cw)]
        img = cv2.resize(crop, (W, H), interpolation=cv2.INTER_LANCZOS4)
        bl = cv2.GaussianBlur(img, (0, 0), 2.2); img = cv2.addWeighted(img, 1.55, bl, -0.55, 0)  # wyostrzenie
        out.stdin.write(img.tobytes())
    out.stdin.close(); out.wait()
    print(k, n, "frames, cuts", cuts[1:-1], "jumps", jc, flush=True)
