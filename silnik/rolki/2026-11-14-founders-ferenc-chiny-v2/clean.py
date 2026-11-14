"""Wycina 'eee' i za długie pauzy z wypowiedzi Bartka. Wynik: cNx.mov (1080x1920 ramka nie tu — tylko 1280x720 + audio), cNx.json (słowa)."""
import json, subprocess, numpy as np
CL = {"c2": 2314.55, "c3": 1541.68, "c4": 3385.45, "c5": 3598.35}
END = {"c2": 11.95, "c3": 12.15, "c4": 4.76, "c5": 3.36}
# fragmenty do wycięcia (sekundy względem początku klipu)
CUT = {
    "c2": [(0.36, 0.93), (8.03, 8.40)],
    "c3": [(-0.10, 0.30), (4.52, 5.25), (7.18, 8.10), (9.10, 9.36), (10.74, 10.88)],
    "c4": [(1.48, 2.22), (2.90, 3.32)],
    "c5": [(1.62, 2.16)],
}
A = np.memmap("audio.f32", dtype=np.float32, mode="r")
def refine(t, base, side):
    # przesuń granicę do najcichszego miejsca w ±50 ms
    s = int((base + t - 0.05) * 16000); seg = np.array(A[s:s + 1600]) ** 2
    e = np.convolve(seg, np.ones(160) / 160, "same"); return t - 0.05 + int(np.argmin(e)) / 16000
out = {}
for k, base in CL.items():
    cuts = sorted(CUT[k]); keep = []; cur = 0.0
    for a, b in cuts:
        a, b = refine(a, base, 0), refine(b, base, 1)
        if a > cur: keep.append((cur, a))
        cur = max(cur, b)
    keep.append((cur, END[k]))
    keep = [(max(0, a), b) for a, b in keep if b - a > 0.05]
    out[k] = keep
    # ffmpeg: osobne kawałki ze źródła, crossfade audio 12 ms
    parts = []
    for i, (a, b) in enumerate(keep):
        p = f"tmp_{k}_{i}.mov"; parts.append(p)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{base + a:.3f}", "-i", "src.mp4", "-t", f"{b - a:.3f}",
                        "-vf", "fps=30", "-af", f"aresample=48000,afade=t=in:d=0.012,afade=t=out:st={b - a - 0.012:.3f}:d=0.012",
                        "-c:v", "libx264", "-crf", "12", "-preset", "veryfast", "-c:a", "pcm_s16le", p], check=True)
    open(f"tmp_{k}.txt", "w").write("".join(f"file '{p}'\n" for p in parts))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-i", f"tmp_{k}.txt", "-c", "copy", f"{k}x.mov"], check=True)
    print(k, [(round(a, 2), round(b, 2)) for a, b in keep], "->", round(sum(b - a for a, b in keep), 2), "s")
json.dump(out, open("keep.json", "w"))
