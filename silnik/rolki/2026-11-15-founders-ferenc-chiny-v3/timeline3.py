import json, re, unicodedata, difflib
FPS = 30
def norm(w):
    w = unicodedata.normalize("NFKD", w.lower().replace("ł", "l")); w = "".join(c for c in w if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", w)
def align(text, asr, t0=0.0, t1=1e9):
    asr = [a for a in asr if t0 - 0.05 <= a[1] < t1]
    words = text.split(); A = [norm(w) for w in words]; B = [norm(a[0]) for a in asr]
    times = [None] * len(A)
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, A, B, autojunk=False).get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1): times[i1 + k] = (asr[j1 + k][1], asr[j1 + k][2])
        elif tag == "replace" and j2 > j1:
            a0, a1 = asr[j1][1], asr[j2 - 1][2]; L = [len(A[i]) + 1 for i in range(i1, i2)]; tot = sum(L); t = a0
            for k, i in enumerate(range(i1, i2)): d = (a1 - a0) * L[k] / tot; times[i] = (t, t + d); t += d
    for i in range(len(times)):
        if times[i] is None:
            p = next((times[j][1] for j in range(i - 1, -1, -1) if times[j]), t0); times[i] = (p, p + 0.2)
    return [[w, s - t0, e - t0] for w, (s, e) in zip(words, times)]

VO = json.load(open("vo_asr.json"))
VT = {
 "v1": ("Ta sama maszyna. Kiedyś kosztowała 30 milionów dolarów. Dziś trzy.", 0.0, 6.10),
 "v2": ("Chiny kupowały od Niemców maszyny do drążenia tuneli. Niemcy trzymały wysoką cenę, bo mogły. Aż Chińczycy nauczyli się budować je sami. Bartek Ferenc był niedawno w Shenzhen i mówi tak:", 6.35, 18.85),
 "v3": ("W jego firmie widać to samo w AI.", 18.95, 21.50),
 "v4": ("I zaczyna się to już w szkole. W naszym muzeum nauki bujasz wahadłem. W chińskim grasz w ping-ponga z robotem.", 21.65, 29.20),
 "v5": ("Cała rozmowa z Bartkiem jest na kanale Founders. A o tym, co z tym zrobić jako polski founder, pogadamy na żywo na Founders Mind. 24–25 listopada, Warszawa.", 29.35, 41.30),
}
CT = {
 "c2": "I to pokazuje, że model chiński jest zupełnie inny, mentalny, niż model niemiecki. Bo model niemiecki dąży do maksymalizacji zysku, a model chiński dąży do maksymalizacji dostępności.",
 "c3": "W naszym produkcie pracujemy na DeepSeeku chińskim, który jest bardzo tani, bo kosztuje 2,5 dolara za tysiąc zadań w naszym marketerze AI, a w Opusie tysiąc zadań kosztuje 150 dolarów. Czyli różnica jest 60-krotna.",
 "c4": "Jedno muzeum ci pokazuje przeszłość, a drugie ci pokazuje przyszłość.",
 "c5": "Ich ludzie mają nadzieję. Nasi mogą nie wiedzieć, że nie mają.",
}
NF = {"c2": 334, "c3": 297, "c4": 115, "c5": 86}
ORDER = ["v1", "v2", "c2", "v3", "c3", "v4", "c4", "c5", "v5"]
segs = []; t = 0.0
for k in ORDER:
    if k[0] == "v":
        txt, a, b = VT[k]; n = round((b - a) * FPS); words = align(txt, VO, a, b)
        seg = {"key": k, "kind": "vo", "vo_from": a}
    else:
        n = NF[k] + (9 if k == "c5" else 0); words = align(CT[k], json.load(open(k + "x.json")))
        seg = {"key": k, "kind": "clip"}
    seg.update(start=round(t, 4), frames=n, dur=n / FPS, words=[[w, round(s + t, 3), round(e + t, 3)] for w, s, e in words])
    segs.append(seg); t += n / FPS
json.dump({"fps": FPS, "total": t, "frames": sum(s["frames"] for s in segs), "segs": segs}, open("timeline3.json", "w"), ensure_ascii=False, indent=1)
for s in segs: print(s["key"], s["start"], round(s["dur"], 2), s["frames"])
print("total", round(t, 2))
