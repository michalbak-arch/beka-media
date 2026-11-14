"""Wyrównanie słów scenariusza do znaczników czasu z Whispera. Użycie: python3 align_asr.py asr.json vo.mp3 timing.json"""
import sys, json, re, difflib, subprocess, unicodedata
asr = json.load(open(sys.argv[1])); vo = sys.argv[2]; out = sys.argv[3]
src = open("/home/claude/reel/render.py").read()
PARAS = eval(src.split("PARAS = ")[1].split("]\n")[0] + "]")

def norm(w):
    w = unicodedata.normalize("NFKD", w.lower())
    w = "".join(c for c in w if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", w)

script = []  # (word, para_idx)
for i, p in enumerate(PARAS):
    for w in p.split():
        script.append((w, i))
A = [norm(w) for w, _ in script]
B = [norm(w[0]) for w in asr]
sm = difflib.SequenceMatcher(None, A, B, autojunk=False)
times = [None] * len(A)
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == "equal":
        for k in range(i2 - i1):
            times[i1 + k] = (asr[j1 + k][1], asr[j1 + k][2])
    elif tag == "replace":
        # rozłóż zakres czasu ASR proporcjonalnie po długości słów skryptu
        t0, t1 = asr[j1][1], asr[j2 - 1][2]
        L = [len(A[i]) + 1 for i in range(i1, i2)]; tot = sum(L); t = t0
        for k, i in enumerate(range(i1, i2)):
            d = (t1 - t0) * L[k] / tot; times[i] = (t, t + d); t += d
# uzupełnij brakujące interpolacją
for i in range(len(times)):
    if times[i] is None:
        prev = next((times[j][1] for j in range(i - 1, -1, -1) if times[j]), 0.0)
        nxt = next((times[j][0] for j in range(i + 1, len(times)) if times[j]), prev + 0.3)
        times[i] = (prev, max(prev + 0.1, min(nxt, prev + 0.4)))
words = [[w, round(t[0], 3), round(t[1], 3)] for (w, _), t in zip(script, times)]
paras = []
for i in range(len(PARAS)):
    ws = [t for (w, p), t in zip(script, times) if p == i]
    paras.append([round(ws[0][0], 3), round(ws[-1][1], 3)])
dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", vo]))
json.dump({"paras": paras, "words": words, "vo_len": dur}, open(out, "w"), ensure_ascii=False, indent=0)
for p in paras: print(p)
unmatched = sum(1 for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag != "equal" for _ in range(i1, i2))
print("words", len(words), "non-exact", unmatched)
