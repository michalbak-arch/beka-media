"""Rolka Founders: Ferenc — Chiny i AI. Animacje + gadająca głowa + lektor.
Użycie: python3 build.py [--preview] [--seg N]"""
import sys, os, json, math, re, difflib, subprocess, unicodedata, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from functools import lru_cache

W, H, FPS = 1080, 1920, 30
D = "/home/claude/ferenc/"
FONTS = "/home/claude/beka-media/silnik/fonts/"

@lru_cache(maxsize=None)
def font(name, size): return ImageFont.truetype(FONTS + name + ".ttf", size)

# paleta Founders
BG = (13, 20, 17); BG2 = (20, 31, 26)
GREEN = (190, 228, 186); GREEN_D = (90, 150, 100)
CORAL = (240, 96, 78); CREAM = (245, 240, 229); GREY = (150, 160, 155)
GOLD = (232, 190, 92)

def ease_out(x): x = min(max(x, 0), 1); return 1 - (1 - x) ** 3
def ease_back(x, s=1.5):
    x = min(max(x, 0), 1) - 1; return x * x * ((s + 1) * x + s) + 1
def clamp(x, a=0, b=1): return min(max(x, a), b)

# ---------- helpers ----------
def norm(w):
    w = unicodedata.normalize("NFKD", w.lower().replace("ł", "l")); w = "".join(c for c in w if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", w)

def align(text, asr, t0=0.0, t1=None):
    """Słowa skryptu -> czasy z ASR (lista [słowo, start, koniec]) w oknie [t0,t1]."""
    asr = [a for a in asr if a[1] >= t0 - 0.05 and (t1 is None or a[1] < t1)]
    words = text.split()
    A = [norm(w) for w in words]; B = [norm(a[0]) for a in asr]
    sm = difflib.SequenceMatcher(None, A, B, autojunk=False)
    times = [None] * len(A)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1): times[i1 + k] = (asr[j1 + k][1], asr[j1 + k][2])
        elif tag == "replace" and j2 > j1:
            a0, a1 = asr[j1][1], asr[j2 - 1][2]; L = [len(A[i]) + 1 for i in range(i1, i2)]; tot = sum(L); t = a0
            for k, i in enumerate(range(i1, i2)):
                d = (a1 - a0) * L[k] / tot; times[i] = (t, t + d); t += d
    for i in range(len(times)):
        if times[i] is None:
            p = next((times[j][1] for j in range(i - 1, -1, -1) if times[j]), t0)
            times[i] = (p, p + 0.25)
    return [[w, s - t0, e - t0] for w, (s, e) in zip(words, times)]

def chunks(words, maxw=3, maxc=18):
    out, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= maxw or w[0][-1] in ".,?!:" or sum(len(x[0]) for x in cur) > maxc:
            out.append(cur); cur = []
    if cur: out.append(cur)
    return out

def draw_caption(fr, t, chs, y=1690):
    for ch in chs:
        if ch[0][1] - 0.05 <= t < ch[-1][2] + 0.12:
            words = [c[0] for c in ch]; sz = 76
            f = font("Inter-900", sz)
            while sum(f.getlength(w + " ") for w in words) > 960 and sz > 44:
                sz -= 4; f = font("Inter-900", sz)
            total = sum(f.getlength(w + " ") for w in words) - f.getlength(" ")
            x = W / 2 - total / 2; d = ImageDraw.Draw(fr)
            for w, c in zip(words, ch):
                on = c[1] <= t < c[2] + 0.08
                col = GREEN if on else CREAM
                d.text((x + 4, y + 6), w, font=f, fill=(0, 0, 0), stroke_width=8, stroke_fill=(0, 0, 0))
                d.text((x, y), w, font=f, fill=col, stroke_width=8, stroke_fill=(10, 14, 12))
                x += f.getlength(w + " ")
            return

def text_img(txt, fnt, size, fill, maxw=980, stroke=0, sfill=(0, 0, 0), align_="center", lh=1.12):
    f = font(fnt, size); lines = []
    for raw in txt.split("\n"):
        cur = ""
        for w in raw.split(" "):
            tst = (cur + " " + w).strip()
            if f.getlength(tst) > maxw and cur: lines.append(cur); cur = w
            else: cur = tst
        lines.append(cur)
    wmax = int(max(f.getlength(l) for l in lines)) + stroke * 2 + 10
    hh = int(size * lh * len(lines)) + stroke * 2 + int(size * 0.35)
    im = Image.new("RGBA", (wmax, hh), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for i, l in enumerate(lines):
        x = {"center": wmax / 2, "left": stroke + 2}[align_]
        d.text((x, stroke + i * size * lh), l, font=f, fill=fill, anchor="ma" if align_ == "center" else "la",
               stroke_width=stroke, stroke_fill=sfill)
    return im

_cache = {}
def C(key, fn):
    if key not in _cache: _cache[key] = fn()
    return _cache[key]

def put(fr, im, cx, cy, sc=1.0, rot=0, alpha=1.0):
    if sc <= 0.01 or alpha <= 0.01: return
    if sc != 1: im = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.BILINEAR)
    if rot: im = im.rotate(rot, expand=True, resample=Image.BILINEAR)
    if alpha < 1:
        im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    fr.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))

def pop(fr, key, mk, cx, cy, t, t0, dur=0.35, rot=0):
    if t < t0: return
    put(fr, C(key, mk), cx, cy, ease_back((t - t0) / dur), rot)

def fade_in(fr, key, mk, cx, cy, t, t0, dur=0.4, dy=40):
    if t < t0: return
    k = ease_out((t - t0) / dur)
    put(fr, C(key, mk), cx, cy + (1 - k) * dy, 1.0, 0, k)

def pill(txt, size, bg, fg, fnt="Inter-900", pad=(30, 16), radius=None):
    f = font(fnt, size); w = int(f.getlength(txt)) + pad[0] * 2; h = int(size * 1.2) + pad[1] * 2
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius or h // 2, fill=bg)
    d.text((w / 2, h / 2), txt, font=f, fill=fg, anchor="mm")
    return im

def card(lines, w=460, bg=(28, 42, 36), accent=GREEN):
    # lines: [(text, font, size, color)]
    h = 40 + sum(int(s * 1.25) for _, _, s, _ in lines) + 10
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], 26, fill=bg + (240,), outline=accent, width=4)
    y = 24
    for txt, fn, s, col in lines:
        d.text((w / 2, y), txt, font=font(fn, s), fill=col, anchor="ma"); y += int(s * 1.25)
    return im

_bg = None
def background(fr, t):
    global _bg
    if _bg is None:
        yy, xx = np.mgrid[0:H, 0:W]
        r = np.sqrt(((xx - W / 2) / W) ** 2 + ((yy - H * 0.42) / H) ** 2)
        g = np.clip(1 - r * 1.4, 0, 1)[..., None]
        arr = (np.array(BG) * (1 - g) + np.array(BG2) * g * 1.25).clip(0, 255).astype("uint8")
        im = Image.fromarray(arr).convert("RGBA"); d = ImageDraw.Draw(im)
        for x in range(0, W, 90): d.line([(x, 0), (x, H)], fill=(255, 255, 255, 10))
        for y in range(0, H, 90): d.line([(0, y), (W, y)], fill=(255, 255, 255, 10))
        _bg = im
    fr.alpha_composite(_bg)
    # dryfujące punkty
    d = ImageDraw.Draw(fr); rnd = random.Random(9)
    for i in range(26):
        x = (rnd.uniform(0, W) + t * rnd.uniform(-12, 12)) % W; y = (rnd.uniform(0, H) - t * rnd.uniform(8, 22)) % H
        r = rnd.uniform(1.5, 3.5); d.ellipse([x - r, y - r, x + r, y + r], fill=GREEN + (60,))

def brand(fr):
    put(fr, C("brand", lambda: pill("founders.pl", 30, (0, 0, 0, 120), CREAM, fnt="Fraunces-700", pad=(22, 10))), 140, 80)

# ---------- rysunki ----------
def tbm(cutter_angle=0.0, w=820):
    """Maszyna do drążenia tuneli (TBM) — widok z boku."""
    h = int(w * 0.42); im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    body = (196, 206, 200); dark = (70, 82, 76)
    d.rounded_rectangle([int(w * 0.18), int(h * 0.22), w - 20, int(h * 0.78)], 30, fill=body, outline=dark, width=6)
    for i in range(6):
        x = int(w * 0.25) + i * int(w * 0.12)
        d.line([(x, int(h * 0.24)), (x, int(h * 0.76))], fill=(160, 170, 165), width=4)
    d.rectangle([int(w * 0.55), int(h * 0.10), int(w * 0.72), int(h * 0.24)], fill=GOLD, outline=dark, width=4)
    # głowica tnąca
    cx, cy, R = int(w * 0.14), h // 2, int(h * 0.46)
    d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=(120, 130, 125), outline=dark, width=6)
    for k in range(8):
        a = cutter_angle + k * math.pi / 4
        d.line([(cx, cy), (cx + R * 0.95 * math.cos(a), cy + R * 0.95 * math.sin(a))], fill=(60, 66, 63), width=10)
        bx, by = cx + R * 0.7 * math.cos(a + 0.2), cy + R * 0.7 * math.sin(a + 0.2)
        d.ellipse([bx - 9, by - 9, bx + 9, by + 9], fill=GOLD)
    d.ellipse([cx - 22, cy - 22, cx + 22, cy + 22], fill=dark)
    return im

def price_tag(txt, color=CORAL, strike=0.0):
    f = font("Fraunces-900", 120); w = int(f.getlength(txt)) + 120; h = 190
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.polygon([(0, h / 2), (50, 0), (w, 0), (w, h), (50, h)], fill=color)
    d.ellipse([30, h / 2 - 14, 58, h / 2 + 14], fill=BG)
    d.text((w / 2 + 25, h / 2), txt, font=f, fill=BG, anchor="mm")
    if strike > 0:
        d.line([(60, h * 0.75), (60 + (w - 80) * strike, h * 0.25)], fill=CREAM, width=16)
    return im

def factory(gear_a=0.0, w=360):
    h = int(w * 0.8); im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    col = (60, 92, 76); line = GREEN
    d.polygon([(10, h - 10), (10, h * 0.45), (w * 0.3, h * 0.25), (w * 0.3, h * 0.45), (w * 0.6, h * 0.25),
               (w * 0.6, h * 0.45), (w - 10, h * 0.25), (w - 10, h - 10)], fill=col, outline=line)
    d.rectangle([w * 0.72, h * 0.05, w * 0.82, h * 0.3], fill=col, outline=line, width=3)
    for i in range(4):
        d.rectangle([30 + i * 80, h * 0.62, 80 + i * 80, h * 0.78], fill=GOLD)
    # zębatka
    gx, gy, r = w * 0.5, h * 0.88, 0
    return im

def gear(a, r=70, col=GREEN):
    s = int(r * 2.6); im = Image.new("RGBA", (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im); c = s / 2
    for k in range(10):
        ang = a + k * math.pi / 5
        pts = []
        for da, rr in ((-0.12, r), (-0.08, r * 1.25), (0.08, r * 1.25), (0.12, r)):
            pts.append((c + rr * math.cos(ang + da), c + rr * math.sin(ang + da)))
        d.polygon(pts, fill=col)
    d.ellipse([c - r, c - r, c + r, c + r], fill=col); d.ellipse([c - r * 0.4, c - r * 0.4, c + r * 0.4, c + r * 0.4], fill=BG)
    return im

def skyline(w=1000):
    h = 420; im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im); rnd = random.Random(4)
    x = 0
    while x < w:
        bw = rnd.randint(50, 110); bh = rnd.randint(120, 400)
        d.rectangle([x, h - bh, x + bw - 6, h], fill=(34, 52, 44))
        for yy in range(h - bh + 16, h - 10, 26):
            for xx in range(x + 10, x + bw - 16, 22):
                if rnd.random() < 0.55: d.rectangle([xx, yy, xx + 9, yy + 12], fill=GOLD + (180,))
        x += bw
    return im

def pendulum_scene(t, w=900, h=560):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], 30, fill=(30, 36, 34, 235), outline=GREY, width=3)
    px, py = w / 2, 60; L = 360; a = math.sin(t * 2.2) * 0.6
    bx, by = px + L * math.sin(a), py + L * math.cos(a)
    d.line([(px - 160, py), (px + 160, py)], fill=GREY, width=10)
    d.line([(px, py), (bx, by)], fill=CREAM, width=5)
    d.ellipse([bx - 40, by - 40, bx + 40, by + 40], fill=GOLD)
    return im

def pingpong_scene(t, w=900, h=560):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], 30, fill=(24, 44, 38, 235), outline=GREEN, width=3)
    # stół
    d.polygon([(120, 420), (780, 420), (720, 330), (180, 330)], fill=(40, 110, 90))
    d.line([(450, 330), (450, 420)], fill=CREAM, width=4)
    d.line([(150, 375), (750, 375)], fill=CREAM, width=2)
    # ramię robota (po prawej)
    ph = t * 2.4; bx_t = (math.sin(ph) + 1) / 2   # 0..1
    base = (800, 480); j1 = (760, 300); hand = (700 + 30 * math.cos(ph), 250 + 40 * math.sin(ph))
    d.line([base, j1], fill=(210, 215, 212), width=34); d.line([j1, hand], fill=(210, 215, 212), width=26)
    for p in (base, j1): d.ellipse([p[0] - 26, p[1] - 26, p[0] + 26, p[1] + 26], fill=CORAL)
    d.ellipse([hand[0] - 40, hand[1] - 40, hand[0] + 40, hand[1] + 40], fill=(200, 40, 40), outline=(60, 20, 20), width=5)
    # piłeczka
    bx = 200 + 480 * bx_t; by = 330 - 160 * abs(math.sin(ph * 2))
    d.ellipse([bx - 16, by - 16, bx + 16, by + 16], fill=(255, 250, 240))
    # gracz (prosta sylwetka po lewej)
    d.ellipse([60, 150, 140, 230], fill=(200, 170, 140)); d.rounded_rectangle([55, 230, 145, 420], 30, fill=(70, 90, 140))
    d.line([(140, 280), (200, 250)], fill=(70, 90, 140), width=22)
    d.ellipse([190, 225, 240, 275], fill=(200, 40, 40))
    return im

def chip_icon(label, col, w=300):
    h = w; im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    m = 40
    for i in range(6):
        y = m + 20 + i * (h - 2 * m - 40) / 5
        d.rectangle([4, y, m, y + 12], fill=GOLD); d.rectangle([w - m, y, w - 4, y + 12], fill=GOLD)
    d.rounded_rectangle([m, m, w - m, h - m], 24, fill=(36, 48, 44), outline=col, width=6)
    d.text((w / 2, h / 2), label, font=font("Inter-900", 54), fill=col, anchor="mm")
    return im

# ---------- sceny animowane ----------
def a_hook(fr, t, dur, words):
    background(fr, t)
    fade_in(fr, "h_t", lambda: text_img("TA SAMA MASZYNA", "Inter-900", 64, GREEN, stroke=0), W / 2, 300, t, 0.0)
    m = tbm(t * 3.0)
    put(fr, m, W / 2, 820 + math.sin(t * 8) * 3)
    t30 = next(w[1] for w in words if w[0].startswith("30") or w[0].startswith("trzydzie"))
    t3 = next(w[1] for w in words if w[0].startswith("trzy."))
    if t >= t30:
        strike = clamp((t - (t3 - 0.15)) / 0.25) if t >= t3 - 0.15 else 0
        put(fr, price_tag("30 MLN $", CORAL, strike), W / 2 - 40, 1180, ease_back((t - t30) / 0.35), -4)
    if t >= t3:
        put(fr, price_tag("3 MLN $", GREEN), W / 2 + 60, 1410, ease_back((t - t3) / 0.35), 3)
    brand(fr)

def a_story(fr, t, dur, words):
    background(fr, t)
    def wt(prefix):
        return next((w[1] for w in words if norm(w[0]).startswith(prefix)), 0)
    t_ceny, t_sami, t_bartek = wt("trzymaly"), wt("nauczyli"), wt("bartek")
    if t < t_bartek - 0.2:
        # Niemcy -> Chiny
        put(fr, C("de", lambda: card([("NIEMCY", "Inter-900", 60, CREAM), ("sprzedają maszyny", "Inter-700", 36, GREY)], 420, accent=GREY)), 260, 560, ease_back(t / 0.35))
        put(fr, C("cn", lambda: card([("CHINY", "Inter-900", 60, CREAM), ("kupują drogo", "Inter-700", 36, GREY)], 420, accent=CORAL)), 820, 560, ease_back((t - 0.4) / 0.35))
        # strzałka z maszyną
        k = ((t * 0.5) % 1.0)
        d = ImageDraw.Draw(fr); d.line([(300, 800), (780, 800)], fill=GREY, width=6); d.polygon([(780, 780), (820, 800), (780, 820)], fill=GREY)
        put(fr, C("tbm_s", lambda: tbm(0, 220)), 300 + 480 * k, 760)
        if t >= t_ceny:
            # cena rośnie / kłódka
            kk = ease_out((t - t_ceny) / 0.6)
            bar_h = 380 * kk
            d.rounded_rectangle([200, 1380 - bar_h, 320, 1380], 18, fill=CORAL)
            pop(fr, "cena", lambda: text_img("CENA\nW GÓRĘ", "Inter-900", 60, CORAL), 470, 1250, t, t_ceny + 0.2)
        if t >= t_sami:
            put(fr, C("fac", lambda: factory(0, 380)), 820, 1220, ease_back((t - t_sami) / 0.4))
            put(fr, gear(t * 2.0, 50, GOLD), 960, 1050)
            pop(fr, "sami", lambda: pill("BUDUJĄ SAMI", 48, GREEN, BG), 820, 1450, t, t_sami + 0.3)
            pop(fr, "x10", lambda: text_img("10× TANIEJ", "Fraunces-900", 120, GREEN), W / 2, 1560, t, t_sami + 0.9)
    else:
        lt = t - (t_bartek - 0.2)
        put(fr, C("sky", lambda: skyline(1080)), W / 2, 1300, 1.0, 0, ease_out(lt / 0.6))
        fade_in(fr, "bf1", lambda: text_img("Bartek Ferenc", "Fraunces-900", 110, CREAM), W / 2, 560, lt, 0.0)
        fade_in(fr, "bf2", lambda: text_img("właściciel Sembot", "Inter-700", 50, GREEN), W / 2, 700, lt, 0.2)
        fade_in(fr, "bf3", lambda: pill("WŁAŚNIE WRÓCIŁ Z SHENZHEN", 44, CORAL, BG), W / 2, 830, lt, 0.5)
    brand(fr)

def a_ai(fr, t, dur, words):
    background(fr, t)
    fade_in(fr, "ai_t", lambda: text_img("TO SAMO W AI", "Inter-900", 90, CREAM), W / 2, 560, t, 0.0)
    pop(fr, "chip_us", lambda: chip_icon("USA", GREY), 330, 1050, t, 0.3)
    pop(fr, "chip_cn", lambda: chip_icon("CHINY", CORAL), 750, 1050, t, 0.7)
    pop(fr, "vs", lambda: text_img("vs", "Fraunces-900", 90, GREEN), W / 2, 1050, t, 0.5)
    brand(fr)

def a_museum(fr, t, dur, words):
    background(fr, t)
    def wt(prefix, after=0):
        return next((w[1] for w in words if norm(w[0]).startswith(prefix) and w[1] >= after), 0)
    t_eu = wt("naszym"); t_cn = wt("chinskim")
    fade_in(fr, "m_t", lambda: text_img("ZACZYNA SIĘ W SZKOLE", "Inter-900", 66, GREEN), W / 2, 230, t, 0.0)
    if t >= t_eu - 0.2:
        k = ease_out((t - t_eu + 0.2) / 0.4)
        put(fr, pendulum_scene(t), W / 2, 700, 1.0, 0, k)
        put(fr, C("eu_l", lambda: pill("MUZEUM NAUKI · EUROPA", 38, GREY, BG)), W / 2, 440, 1.0, 0, k)
    if t >= t_cn - 0.2:
        k = ease_out((t - t_cn + 0.2) / 0.4)
        put(fr, pingpong_scene(t), W / 2, 1320, 1.0, 0, k)
        put(fr, C("cn_l", lambda: pill("MUZEUM NAUKI · CHINY", 38, CORAL, BG)), W / 2, 1060, 1.0, 0, k)
    brand(fr)

def a_cta(fr, t, dur, words):
    background(fr, t)
    def wt(prefix):
        return next((w[1] for w in words if norm(w[0]).startswith(prefix)), 0)
    t_a = wt("a"); t_mind = wt("mind")
    t_a = next((w[1] for w in words if w[0] == "A"), 3.0)
    if t < t_a - 0.1:
        fade_in(fr, "c1", lambda: text_img("Cała rozmowa", "Fraunces-900", 110, CREAM), W / 2, 700, t, 0.0)
        fade_in(fr, "c2", lambda: pill("YOUTUBE · FOUNDERS.PL", 50, CORAL, BG), W / 2, 880, t, 0.3)
        fade_in(fr, "c3", lambda: text_img("Bartek Ferenc o Chinach,\nrobotach i AI", "Inter-700", 50, GREY), W / 2, 1040, t, 0.6)
    else:
        lt = t - t_a
        fade_in(fr, "c4", lambda: text_img("Co z tym zrobić\njako polski founder?", "Fraunces-900", 86, CREAM), W / 2, 500, lt, 0.0)
        logo = C("logo", lambda: Image.open("/home/claude/beka-media/silnik/assets/logo_color.png").convert("RGBA"))
        if t >= t_mind - 0.6:
            put(fr, logo, W / 2, 900, ease_back((t - t_mind + 0.6) / 0.45) * 0.6)
        fade_in(fr, "c5", lambda: pill("24–25.11 · WARSZAWA", 54, GREEN, BG), W / 2, 1180, lt, 1.6)
        fade_in(fr, "c6", lambda: text_img("foundersmind.pl", "Fraunces-700", 64, CREAM), W / 2, 1320, lt, 2.2)
    brand(fr)

# ---------- klipy z wywiadu ----------
LOWER = lambda: card([("Bartek Ferenc", "Fraunces-900", 54, CREAM), ("właściciel Sembot", "Inter-700", 34, GREEN)], 520, bg=(13, 20, 17), accent=CORAL)

def clip_frames(path, n, cx=620):
    """Generator klatek klipu: tło rozmyte + kadr 4:5 z mówcą."""
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", path, "-vf", "fps=30", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         stdout=subprocess.PIPE)
    sz = 1280 * 720 * 3; last = None
    for i in range(n):
        buf = p.stdout.read(sz)
        if len(buf) == sz: last = Image.frombytes("RGB", (1280, 720), buf)
        src = last
        # tło
        bgc = src.crop((640 - 203, 0, 640 + 203, 720)).resize((270, 480)).filter(ImageFilter.GaussianBlur(10)).resize((W, H))
        bgc = Image.blend(bgc, Image.new("RGB", (W, H), BG), 0.55).convert("RGBA")
        # kadr 4:5
        cw = 576; x0 = int(clamp(cx - cw / 2, 0, 1280 - cw))
        fg = src.crop((x0, 0, x0 + cw, 720)).resize((1000, 1250), Image.LANCZOS).convert("RGBA")
        m = Image.new("L", fg.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, fg.width - 1, fg.height - 1], 36, fill=255)
        bgc.paste(fg, (40, 250), m)
        ImageDraw.Draw(bgc).rounded_rectangle([40, 250, 1040, 1500], 36, outline=GREEN + (160,), width=4)
        yield bgc
    p.stdout.close(); p.wait()

def overlay_c2(fr, t, words):
    def wt(p): return next((w[1] for w in words if norm(w[0]).startswith(p) and w[1] > 5), 99)
    pop(fr, "z", lambda: card([("NIEMCY", "Inter-900", 38, GREY), ("max ZYSK", "Fraunces-900", 58, CREAM)], 400, accent=GREY), 250, 400, t, wt("zysku"))
    pop(fr, "dst", lambda: card([("CHINY", "Inter-900", 38, CORAL), ("max DOSTĘPNOŚĆ", "Fraunces-900", 50, CREAM)], 520, accent=CORAL), 780, 400, t, wt("dostepnosci"))

def overlay_c3(fr, t, words):
    def wt(p): return next((w[1] for w in words if norm(w[0]).startswith(p)), 99)
    t25 = next((w[1] for w in words if w[0].startswith("2,5")), 3.8)
    pop(fr, "ds", lambda: card([("DeepSeek (Chiny)", "Inter-900", 36, CORAL), ("2,5 $", "Fraunces-900", 84, CREAM), ("za 1000 zadań", "Inter-700", 30, GREY)], 400, accent=CORAL), 260, 420, t, t25)
    pop(fr, "op", lambda: card([("Opus (USA)", "Inter-900", 36, GREY), ("150 $", "Fraunces-900", 84, CREAM), ("za 1000 zadań", "Inter-700", 30, GREY)], 400, accent=GREY), 820, 420, t, wt("150"))
    pop(fr, "x60", lambda: text_img("×60", "Fraunces-900", 220, GREEN, stroke=8, sfill=BG), 800, 1150, t, wt("60"))

def overlay_c4(fr, t, words):
    def wt(p): return next((w[1] for w in words if norm(w[0]).startswith(p)), 99)
    pop(fr, "past", lambda: pill("PRZESZŁOŚĆ", 54, GREY, BG), 300, 380, t, wt("przeszlosc"))
    pop(fr, "fut", lambda: pill("PRZYSZŁOŚĆ", 54, GREEN, BG), 780, 380, t, wt("przyszlosc"))

# ---------- plan ----------
VO = json.load(open(D + "vo_asr.json"))
VO_TXT = {
    "v1": "Ta sama maszyna. Kiedyś kosztowała trzydzieści milionów dolarów. Dziś trzy.",
    "v2": "Chiny kupowały od Niemców maszyny do drążenia tuneli. Niemcy trzymały wysoką cenę, bo mogły. Aż Chińczycy nauczyli się budować je sami. Bartek Ferenc był niedawno w Shenzhen i mówi tak:",
    "v3": "W jego firmie widać to samo w AI.",
    "v4": "I zaczyna się to już w szkole. W naszym muzeum nauki bujasz wahadłem. W chińskim grasz w ping-ponga z robotem.",
    "v5": "Cała rozmowa z Bartkiem jest na kanale Founders. A o tym, co z tym zrobić jako polski founder, pogadamy na żywo na Founders Mind. 24–25 listopada, Warszawa.",
}
CLIP_TXT = {
    "c2": "I to pokazuje, że model chiński jest zupełnie inny, mentalny, niż model niemiecki. Bo model niemiecki dąży do maksymalizacji zysku, a model chiński dąży do maksymalizacji dostępności.",
    "c3": "W naszym produkcie pracujemy na DeepSeeku chińskim, który jest bardzo tani, bo kosztuje 2,5 dolara za tysiąc zadań w naszym marketerze AI, a w Opusie tysiąc zadań kosztuje 150 dolarów. Czyli różnica jest 60-krotna.",
    "c4": "Jedno muzeum ci pokazuje przeszłość, a drugie ci pokazuje przyszłość.",
    "c5": "Ich ludzie mają nadzieję. Nasi mogą nie wiedzieć, że nie mają.",
}
PLAN = [
    ("anim", "v1", (0.0, 6.1), a_hook),
    ("anim", "v2", (6.35, 18.85), a_story),
    ("clip", "c2", None, overlay_c2),
    ("anim", "v3", (18.95, 21.5), a_ai),
    ("clip", "c3", None, overlay_c3),
    ("anim", "v4", (21.65, 29.2), a_museum),
    ("clip", "c4", None, overlay_c4),
    ("clip", "c5", None, None),
    ("anim", "v5", (29.35, 41.3), a_cta),
]

def seg_info(seg):
    kind, key, rng, fn = seg
    if kind == "anim":
        a, b = rng; dur = b - a
        words = align(VO_TXT[key], VO, a, b)
    else:
        dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", D + key + ".mov"]))
        words = align(CLIP_TXT[key], json.load(open(D + key + ".json")), 0.0, None)
    return dur, words

def render_seg(i, out_mp4, preview_times=None):
    kind, key, rng, fn = PLAN[i]
    dur, words = seg_info(PLAN[i]); n = int(round(dur * FPS)); chs = chunks(words)
    if preview_times is not None:
        res = []
        frames = clip_frames(D + key + ".mov", n) if kind == "clip" else None
        want = {int(pt * FPS) for pt in preview_times}
        for f in range(n):
            base = next(frames) if frames else None
            if f in want:
                res.append(compose(kind, fn, base, f / FPS, dur, words, chs, key))
        return res
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p", out_mp4], stdin=subprocess.PIPE)
    frames = clip_frames(D + key + ".mov", n) if kind == "clip" else None
    for f in range(n):
        base = next(frames) if frames else None
        p.stdin.write(compose(kind, fn, base, f / FPS, dur, words, chs, key).tobytes())
    p.stdin.close(); p.wait()
    return n

HIDE = {"c3": (4.85, 7.75)}
def compose(kind, fn, base, t, dur, words, chs, key=None):
    if kind == "anim":
        fr = Image.new("RGBA", (W, H), BG + (255,)); fn(fr, t, dur, words)
    else:
        fr = base.copy()
        hd = HIDE.get(key)
        if not (hd and hd[0] <= t < hd[1]):
            put(fr, C("lower", LOWER), 330, 1440 - 40, 1.0, 0, ease_out(t / 0.4))
        if fn: fn(fr, t, words)
        brand(fr)
    draw_caption(fr, t, chs)
    # krótki błysk na cięciu
    if t < 0.06: fr.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, 70)))
    return fr.convert("RGB")

if __name__ == "__main__":
    if "--preview" in sys.argv:
        sheet = []
        for i, seg in enumerate(PLAN):
            dur, _ = seg_info(seg)
            ts = [min(dur - 0.05, x * dur) for x in (0.25, 0.6, 0.95)]
            sheet += render_seg(i, None, ts)
        th = [im.resize((216, 384)) for im in sheet]
        cols = 9; rows = math.ceil(len(th) / cols)
        S = Image.new("RGB", (216 * cols, 384 * rows))
        for k, im in enumerate(th): S.paste(im, ((k % cols) * 216, (k // cols) * 384))
        S.save(D + "preview.jpg"); print("preview", len(th)); sys.exit()
    idx = [int(sys.argv[sys.argv.index("--seg") + 1])] if "--seg" in sys.argv else range(len(PLAN))
    for i in idx:
        n = render_seg(i, D + f"seg{i:02d}.mp4"); print("seg", i, n, flush=True)
