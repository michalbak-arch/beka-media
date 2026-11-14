"""Rolka: afera NVIDII — render klatek PIL -> ffmpeg. Użycie: python3 render.py [timing.json] [out.mp4] [--preview SEK]"""
import sys, json, math, random, subprocess, os
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, os.path.dirname(__file__))
from chars import *

W, H, FPS = 1080, 1920, 30
VO_LEN = 79.68

PARAS = [
    "Szef NVIDII przez lata zaczynał prezentacje od zdania: „Jesteśmy trzydzieści dni od bankructwa”. Okazało się, że żeby stracić czterysta trzydzieści miliardów dolarów, wystarczą dwa.",
    "Co się stało? Amerykańskie media piszą, że wywiad USA podejrzewa Alice Huang, menedżerkę Megaspeed, jednego z największych klientów NVIDII w Azji, o pracę dla chińskich służb. I że łączył ją romans z prezesem.",
    "Jensen przeprasza rodzinę i pracowników za niewierność. Szpiegostwa nie przyznaje, Chiny wszystkiemu zaprzeczają, a zarząd zleca niezależne śledztwo.",
    "Giełda? Poniedziałek: minus cztery procent. Wtorek: minus pięć i pół. Do tego pozew akcjonariuszy i Kongres, który chce go przepytać dzień po wynikach kwartalnych.",
    "A teraz biznes. NVIDIA latami przekonywała Waszyngton, że może sprzedawać chipy do Chin, bo wie, gdzie one trafiają. Jedna prywatna relacja i ten argument właśnie stracił gwarancję.",
    "I nie, to nie jest odcinek o złym prezesie. Każdy z nas ma swoje słabości. Tylko nie każdy nosi pod skórzaną kurtką spółkę za cztery biliony dolarów.",
    "O człowieku za firmą gadamy na Founders Mind. Z kodem beka20 bilet taniej. Link w bio.",
]

# ---------- timing ----------
def default_timing():
    lens = [len(p) for p in PARAS]
    pause = 0.9
    speak = VO_LEN - pause * 6 - 0.4
    t = 0.2; out = []
    for L in lens:
        d = speak * L / sum(lens); out.append([t, t + d]); t += d + pause
    return out

timing_file = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].endswith(".json") else None
SEG = json.load(open(timing_file))["paras"] if timing_file else default_timing()
WORDS = json.load(open(timing_file)).get("words") if timing_file else None
VO_LEN = json.load(open(timing_file)).get('vo_len', VO_LEN) if timing_file else VO_LEN
TOTAL = max(SEG[-1][1] + 1.6, VO_LEN + 0.8)

# ---------- helpers ----------
def ease_out_back(x, s=1.70158):
    x = min(max(x, 0), 1) - 1
    return x * x * ((s + 1) * x + s) + 1
def ease_out(x):
    x = min(max(x, 0), 1); return 1 - (1 - x) ** 3
def clamp(x, a=0, b=1): return min(max(x, a), b)

_ray_cache = {}
def rays(c1, c2, n=18):
    key = (c1, c2)
    if key not in _ray_cache:
        S = 2300
        im = Image.new("RGB", (S, S), c1); d = ImageDraw.Draw(im)
        for i in range(n):
            a0 = 2 * math.pi * i / n; a1 = a0 + math.pi / n
            d.polygon([(S/2, S/2), (S/2 + S*math.cos(a0), S/2 + S*math.sin(a0)), (S/2 + S*math.cos(a1), S/2 + S*math.sin(a1))], fill=c2)
        _ray_cache[key] = im
    return _ray_cache[key]

def bg_rays(frame, c1, c2, t, speed=8):
    r = rays(c1, c2).rotate(t * speed, resample=Image.BILINEAR)
    S = r.width
    frame.paste(r.crop(((S - W)//2, (S - H)//2, (S + W)//2, (S + H)//2)), (0, 0))
    # vignette
    frame.paste((0, 0, 0), (0, 0, W, H), _vig())

_vig_img = None
def _vig():
    global _vig_img
    if _vig_img is None:
        m = Image.new("L", (W, H), 0); d = ImageDraw.Draw(m)
        # radial
        import numpy as np
        yy, xx = np.mgrid[0:H, 0:W]
        r = np.sqrt(((xx - W/2) / (W*0.75))**2 + ((yy - H/2) / (H*0.7))**2)
        m = Image.fromarray((np.clip(r - 0.45, 0, 1) * 220).astype("uint8"))
        _vig_img = m
    return _vig_img

def solid(frame, c): frame.paste(c, (0, 0, W, H))

_sprite_cache = {}
def sprite(key, fn):
    if key not in _sprite_cache: _sprite_cache[key] = fn()
    return _sprite_cache[key]

def put(frame, im, cx, cy, scale=1.0, rot=0.0, alpha=1.0):
    if scale <= 0.01 or alpha <= 0: return
    if scale != 1.0:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BILINEAR)
    if rot: im = im.rotate(rot, expand=True, resample=Image.BILINEAR)
    if alpha < 1:
        a = im.getchannel("A").point(lambda v: int(v * alpha)); im = im.copy(); im.putalpha(a)
    frame.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))

def text_img(txt, size, fill=WHITE, stroke=BLACK, sw=None, fnt="Anton", shadow=True, maxw=1000):
    f = font(fnt, size)
    lines = []
    for raw in txt.split("\n"):
        words = raw.split(" "); cur = ""
        for w_ in words:
            test = (cur + " " + w_).strip()
            if f.getlength(test) > maxw and cur: lines.append(cur); cur = w_
            else: cur = test
        lines.append(cur)
    sw = sw if sw is not None else max(4, size // 11)
    lh = int(size * 1.08)
    wmax = int(max(f.getlength(l) for l in lines)) + sw * 2 + 20
    im = Image.new("RGBA", (wmax, lh * len(lines) + sw * 2 + 24), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i, l in enumerate(lines):
        y = sw + 6 + i * lh
        if shadow:
            d.text((wmax / 2 + 8, y + 10), l, font=f, fill=(0, 0, 0, 150), anchor="ma", stroke_width=sw, stroke_fill=(0, 0, 0, 150))
        d.text((wmax / 2, y), l, font=f, fill=fill, anchor="ma", stroke_width=sw, stroke_fill=stroke)
    return im

def pop_text(frame, txt, size, cx, cy, t, delay=0.0, fill=WHITE, stroke=BLACK, rot=0, fnt="Anton", maxw=1000, dur=0.35):
    if t < delay: return
    k = ease_out_back((t - delay) / dur)
    im = sprite(("T", txt, size, fill, stroke, fnt, maxw), lambda: text_img(txt, size, fill, stroke, fnt=fnt, maxw=maxw))
    put(frame, im, cx, cy, k, rot)

def label_box(txt, size, bg, fg=WHITE, pad=26, fnt="Anton"):
    f = font(fnt, size)
    w = int(f.getlength(txt)) + pad * 2; h = int(size * 1.25) + pad
    im = Image.new("RGBA", (w + 12, h + 12), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([12, 12, w + 12, h + 12], 18, fill=(0, 0, 0, 160))
    d.rounded_rectangle([0, 0, w, h], 18, fill=bg, outline=BLACK, width=6)
    d.text((w / 2, h / 2), txt, font=f, fill=fg, anchor="mm")
    return im

def pop_box(frame, txt, size, bg, cx, cy, t, delay=0, fg=WHITE, rot=0):
    if t < delay: return
    im = sprite(("B", txt, size, bg, fg), lambda: label_box(txt, size, bg, fg))
    put(frame, im, cx, cy, ease_out_back((t - delay) / 0.3), rot)

def stamp(frame, txt, cx, cy, t, delay=0, color=RED, size=110, rot=-12):
    if t < delay: return
    def mk():
        f = font("Anton", size); w = int(f.getlength(txt)) + 80; h = int(size * 1.35) + 40
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.rounded_rectangle([8, 8, w - 8, h - 8], 20, outline=color, width=14)
        d.text((w / 2, h / 2), txt, font=f, fill=color, anchor="mm")
        return im
    im = sprite(("S", txt, color, size), mk)
    k = (t - delay) / 0.18
    sc = 2.4 - 1.4 * ease_out(k) if k < 1 else 1.0
    put(frame, im, cx, cy, sc, rot, alpha=clamp(k * 1.5))

def shake(t, t0, amp=28, dur=0.35):
    if t < t0 or t > t0 + dur: return 0, 0
    k = 1 - (t - t0) / dur
    return int(math.sin(t * 90) * amp * k), int(math.cos(t * 77) * amp * k)

def bounce(t, f=2.2, a=14): return math.sin(t * f * math.pi) * a

# ---------- chart ----------
def chart(frame, t, crash_at, x0=80, y0=1350, w=920, h=650):
    d = ImageDraw.Draw(frame)
    for i in range(6):
        y = y0 - i * h / 5
        d.line([(x0, y), (x0 + w, y)], fill=(255, 255, 255, 50), width=2)
    pts = []
    n = 60
    rnd = random.Random(3)
    for i in range(n):
        x = x0 + w * i / (n - 1)
        base = y0 - h * 0.15 - h * 0.75 * (i / (n - 1)) ** 1.4 + rnd.uniform(-18, 18)
        pts.append([x, base])
    prog = clamp(t / max(crash_at, 0.01))
    k = int(2 + prog * (n - 3))
    show = pts[:k]
    if t > crash_at:
        c = ease_out((t - crash_at) / 0.6)
        last = pts[k - 1]
        show = show + [[last[0] + 40, last[1] + (y0 - last[1]) * c * 0.95]]
        col = RED
    else:
        col = (60, 230, 110)
    if len(show) > 1:
        d.line([tuple(p) for p in show], fill=col, width=16, joint="curve")
    return show[-1]

# ---------- scenes ----------
# każda scena: f(frame, t, dur) ; t = czas lokalny

def s_teaser(fr, t, dur):
    bg_rays(fr, (90, 6, 10), (130, 14, 18), t, 30)
    sx, sy = shake(t, 0.0, 30, dur)
    pop_text(fr, "-430 MLD $", 220, W/2 + sx, 760 + sy, t, 0.0, fill=RED, stroke=WHITE, dur=0.2)
    stamp(fr, "W 2 DNI?!", W/2 + 120, 1050, t, 0.25, YELLOW, 110, -8)
    put(fr, sprite("ch_shock_up", lambda: chipek("shock", "up")), W/2, 1420 + sy, 0.5, rot=math.sin(t * 20) * 8)

def s_hook_stage(fr, t, dur):
    bg_rays(fr, (10, 40, 22), (16, 62, 34), t)
    d = ImageDraw.Draw(fr)
    # spotlight
    sp = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ds = ImageDraw.Draw(sp)
    ds.polygon([(W/2 - 80, 0), (W/2 + 80, 0), (W/2 + 480, 1500), (W/2 - 480, 1500)], fill=(255, 255, 200, 45))
    fr.alpha_composite(sp)
    put(fr, sprite("ch_proud_up", lambda: chipek("proud", "up")), W/2, 1050 + bounce(t, 1.5, 12), 0.95)
    pop_box(fr, "„JESTEŚMY 30 DNI", 78, (250, 250, 250), W/2, 330, t, 0.15, fg=BLACK, rot=-3)
    pop_box(fr, "OD BANKRUCTWA”", 78, (250, 250, 250), W/2, 450, t, 0.45, fg=BLACK, rot=2)
    if t > dur * 0.55:
        pop_box(fr, "PREZES, OD LAT", 54, YELLOW, W/2, 190, t, dur * 0.55, fg=BLACK)

def s_hook_crash(fr, t, dur):
    sx, sy = shake(t, 0.6, 34, 0.6)
    bg_rays(fr, (60, 8, 10), (90, 14, 16), t, 14)
    end = chart(fr, t, 0.5, x0=70, y0=1500, w=800, h=900)
    ch = sprite("ch_shock_shrug", lambda: chipek("shock", "shrug"))
    if t < 0.5:
        put(fr, ch, end[0] - 40, end[1] - 210, 0.42)
    else:
        k = ease_out((t - 0.5) / 0.7)
        put(fr, ch, end[0] - 90 + sx, end[1] - 180 + sy, 0.42, rot=-35 * k)
    pop_text(fr, "-430 MLD $", 200, W/2 + sx, 380 + sy, t, 0.6, fill=RED, stroke=WHITE)
    stamp(fr, "W 2 DNI", W/2 + 170, 600, t, 1.2, YELLOW, 100, -10)

def s_what(fr, t, dur):
    bg_rays(fr, (20, 30, 60), (28, 42, 82), t)
    pop_text(fr, "CO SIĘ STAŁO?", 150, W/2, 330, t, 0.0, fill=YELLOW)
    papers = [("BIZNES NEWS", "WYWIAD USA\nPODEJRZEWA...", -14, 760), ("TECH DAILY", "PREZES, ROMANS\nI CHIPY", 9, 1180)]
    for i, (a, b, r, y) in enumerate(papers):
        k = ease_out_back((t - 0.25 - i * 0.35) / 0.45)
        if t > 0.25 + i * 0.35:
            im = sprite(("np", a), lambda a=a, b=b: newspaper(a, b, 800))
            put(fr, im, W/2 + (1 - k) * (900 if i else -900), y, 1.0, r + (1 - k) * 40)
    pop_box(fr, "Źródło: NYT, FT, Bloomberg", 34, (30, 30, 30), W/2, 1560, t, 0.9, fg=WHITE, fnt="Anton") if False else None
    if t > 0.9:
        im = sprite("srcbox", lambda: label_box("ŹRÓDŁA: NYT, FINANCIAL TIMES, BLOOMBERG", 36, (25, 25, 30)))
        put(fr, im, W/2, 1560, ease_out_back((t - 0.9) / 0.3))

def s_spy(fr, t, dur):
    bg_rays(fr, (70, 110, 150), (90, 135, 178), t, 5)
    put(fr, sprite("spy", spy), W/2 + 170, 1100 + bounce(t, 0.8, 8), 0.95)
    put(fr, sprite("ch_worried", lambda: chipek("worried", "down")), W/2 - 260, 1220, 0.6)
    pop_box(fr, "MENEDŻERKA MEGASPEED", 60, (240, 240, 240), W/2, 300, t, 0.1, fg=BLACK)
    pop_box(fr, "JEDEN Z NAJWIĘKSZYCH KLIENTÓW W AZJI", 38, (60, 60, 80), W/2, 410, t, 0.45)
    stamp(fr, "PODEJRZENIE WYWIADU USA", W/2, 560, t, dur * 0.45, RED, 62, -4)
    # magnifier
    if t > dur * 0.3:
        k = (t - dur * 0.3)
        mx, my = W/2 + 170 + math.sin(k * 2.2) * 120, 900 + math.cos(k * 1.7) * 100
        d = ImageDraw.Draw(fr)
        d.ellipse([mx - 110, my - 110, mx + 110, my + 110], outline=(200, 200, 210), width=22)
        d.line([(mx + 80, my + 80), (mx + 200, my + 200)], fill=(120, 80, 40), width=36)

def s_romance(fr, t, dur):
    bg_rays(fr, (120, 20, 60), (150, 34, 80), t, 10)
    put(fr, sprite("ch_happy_hold", lambda: chipek("happy", "hold")), W/2 - 230, 1180, 0.62)
    put(fr, sprite("spy", spy), W/2 + 250, 1150, 0.72)
    if t > 0.3:
        k = ease_out_back((t - 0.3) / 0.4)
        put(fr, sprite("heart", lambda: heart(False, 380)), W/2, 760 + bounce(t, 3, 14), k * (1 + 0.06 * math.sin(t * 12)))
    pop_text(fr, "ROMANS", 190, W/2, 330, t, 0.15, fill=(255, 120, 170))
    pop_text(fr, "Z PREZESEM", 110, W/2, 500, t, 0.45)
    # floating little hearts
    rnd = random.Random(5)
    for i in range(10):
        ph = rnd.uniform(0, 3); x = rnd.uniform(80, W - 80)
        y = 1650 - ((t * 260 + ph * 300) % 1500)
        put(fr, sprite("hs", lambda: heart(False, 90)), x, y, 0.7)

def s_sorry(fr, t, dur):
    bg_rays(fr, (40, 40, 48), (56, 56, 66), t, 4)
    # flashes
    rnd = random.Random(int(t * 6))
    if int(t * 10) % 3 == 0:
        d = ImageDraw.Draw(fr)
        for i in range(3):
            x, y = rnd.uniform(60, W - 60), rnd.uniform(1450, 1800)
            d.ellipse([x - 70, y - 70, x + 70, y + 70], fill=(255, 255, 255, 230))
    bowk = 0.5 + 0.5 * math.sin(t * 2.4)
    put(fr, sprite("ch_sorry", lambda: chipek("sorry", "apology")), W/2, 980 + bowk * 30, 0.75, rot=-6 * bowk)
    put(fr, sprite("podium", podium), W/2, 1400, 1.1)
    pop_box(fr, "PRZEPRASZAM", 110, (250, 250, 250), W/2, 330, t, 0.15, fg=BLACK, rot=-2)
    pop_box(fr, "RODZINĘ I PRACOWNIKÓW", 52, (90, 90, 100), W/2, 470, t, 0.5)

def s_deny(fr, t, dur):
    bg_rays(fr, (130, 10, 15), (160, 25, 30), t, 6)
    put(fr, sprite("ch_shrug_s", lambda: chipek("worried", "shrug")), W/2, 1350, 0.75)
    stamp(fr, "SZPIEGOSTWO? NIE PRZYZNAJE", W/2, 380, t, 0.1, WHITE, 70, -5)
    stamp(fr, "CHINY: ZAPRZECZAMY", W/2, 620, t, dur * 0.45, YELLOW, 84, 6)

def s_board(fr, t, dur):
    bg_rays(fr, (30, 50, 80), (42, 66, 102), t, 4)
    d = ImageDraw.Draw(fr)
    for i in range(5):
        x = 140 + i * 200
        put(fr, sprite(("bm", i), lambda i=i: board_member(i)), x, 1180 + bounce(t + i * .3, 1.8, 6), 0.8)
    d.rounded_rectangle([30, 1280, W - 30, 1460], 30, fill=(110, 70, 40), outline=BLACK, width=8)
    # folder
    k = ease_out_back((t - 0.3) / 0.4)
    if t > 0.3:
        fo = sprite("folder", lambda: label_box("NIEZALEŻNE ŚLEDZTWO", 66, (220, 180, 90), BLACK))
        put(fr, fo, W/2, 760, k, -3)
    pop_text(fr, "ZARZĄD:", 140, W/2, 360, t, 0.0, fill=YELLOW)

def s_market_title(fr, t, dur):
    bg_rays(fr, (8, 8, 12), (22, 22, 30), t, 20)
    pop_text(fr, "GIEŁDA?", 260, W/2, H/2 - 120, t, 0.0, fill=WHITE)
    # ticker
    d = ImageDraw.Draw(fr)
    d.rectangle([0, 1500, W, 1600], fill=(20, 20, 20))
    f = font("Anton", 70)
    s = "NVDA -9,5%   NASDAQ   NVDA -9,5%   AI   " * 4
    off = -int(t * 600) % 900
    d.text((off - 900, 1515), s, font=f, fill=RED)

def big_drop(fr, t, dur, day, pct, sz):
    bg_rays(fr, (70, 6, 10), (100, 12, 18), t, 16)
    sx, sy = shake(t, 0.35, 30, 0.4)
    # falling arrows
    rnd = random.Random(day)
    d = ImageDraw.Draw(fr)
    for i in range(7):
        x = rnd.uniform(80, W - 80); ph = rnd.uniform(0, 1)
        y = ((t * 900 + ph * 1900) % 2100) - 100
        d.polygon([(x - 40, y), (x + 40, y), (x + 40, y + 70), (x + 80, y + 70), (x, y + 160), (x - 80, y + 70), (x - 40, y + 70)], fill=(255, 90, 90))
    pop_text(fr, day, 120, W/2, 330, t, 0.0, fill=WHITE)
    pop_text(fr, pct, sz, W/2 + sx, 700 + sy, t, 0.3, fill=RED, stroke=WHITE)
    fall = ease_out(t / dur)
    put(fr, sprite("ch_shock_up", lambda: chipek("shock", "up")), W/2, 1200 + fall * 120, 0.7, rot=math.sin(t * 8) * 10)

def s_monday(fr, t, dur): big_drop(fr, t, dur, "PONIEDZIAŁEK", "-4,27%", 260)
def s_tuesday(fr, t, dur): big_drop(fr, t, dur, "WTOREK", "-5,47%", 330)

def s_lawsuit(fr, t, dur):
    bg_rays(fr, (60, 40, 20), (84, 56, 30), t, 6)
    hit = 0.45
    ang = 60 - 75 * ease_out(t / hit) if t < hit else -15
    sx, sy = shake(t, hit, 40, 0.4)
    put(fr, sprite("gavel", gavel), W/2 + 120 + sx, 900 + sy, 1.3, rot=ang)
    d = ImageDraw.Draw(fr)
    d.rounded_rectangle([W/2 - 260 + sx, 1250 + sy, W/2 + 260 + sx, 1340 + sy], 20, fill=(120, 70, 35), outline=BLACK, width=8)
    stamp(fr, "POZEW AKCJONARIUSZY", W/2, 420, t, hit, WHITE, 80, -4)

def s_congress(fr, t, dur):
    bg_rays(fr, (20, 40, 100), (30, 56, 130), t, 5)
    put(fr, sprite("capitol", lambda: capitol(820)), W/2, 1180, 1.0)
    pop_text(fr, "KONGRES", 190, W/2, 300, t, 0.0, fill=WHITE)
    pop_box(fr, "17.11 WYNIKI", 70, (40, 160, 80), W/2 - 230, 540, t, 0.35, rot=-4)
    pop_box(fr, "18.11 PRZESŁUCHANIE", 70, RED, W/2 + 120, 680, t, 0.7, rot=3)

def s_business(fr, t, dur):
    bg_rays(fr, (255, 200, 0), (255, 222, 60), t, 10)
    pop_text(fr, "A TERAZ", 150, W/2, 520, t, 0.0, fill=WHITE)
    pop_text(fr, "BIZNES", 300, W/2, 780, t, 0.25, fill=BLACK, stroke=WHITE)
    put(fr, sprite("ch_proud_hold", lambda: chipek("proud", "holdboth")), W/2, 1450, 0.6)

def s_pitch(fr, t, dur):
    bg_rays(fr, (30, 60, 110), (40, 78, 140), t, 4)
    put(fr, sprite("capitol_s", lambda: capitol(560)), 280, 650, 1.0)
    put(fr, sprite("ch_happy_wave", lambda: chipek("happy", "wave")), 780, 760, 0.6)
    pop_box(fr, "WASZYNGTON", 60, (240, 240, 240), 280, 330, t, 0.05, fg=BLACK)
    # truck drives to China gate
    k = clamp((t - 0.4) / (dur - 0.6))
    d = ImageDraw.Draw(fr)
    d.rectangle([0, 1600, W, 1620], fill=(40, 40, 40))
    d.rectangle([W - 210, 1150, W - 60, 1610], fill=(200, 40, 40), outline=BLACK, width=8)
    d.text((W - 135, 1240), "CHINY", font=font("Anton", 56), fill=YELLOW, anchor="mm")
    put(fr, sprite("truck", truck), -300 + k * 900, 1450, 0.85)
    if t > 0.6:
        im = sprite("warr", lambda: warranty_sticker(False))
        put(fr, im, W/2, 1080, ease_out_back((t - 0.6) / 0.35) * 1.15, -5)

def s_void(fr, t, dur):
    bg_rays(fr, (120, 10, 15), (150, 22, 28), t, 8)
    put(fr, sprite("ch_shock_sh", lambda: chipek("shock", "shrug")), W/2, 1380, 0.7)
    pop_box(fr, "JEDNA PRYWATNA RELACJA", 64, (250, 250, 250), W/2, 300, t, 0.0, fg=BLACK)
    sw_t = dur * 0.62
    if t < sw_t:
        put(fr, sprite("warr", lambda: warranty_sticker(False)), W/2, 760, 1.15, -5)
    else:
        sx, sy = shake(t, sw_t, 30, 0.4)
        put(fr, sprite("warrv", lambda: warranty_sticker(True)), W/2 + sx, 760 + sy, 1.15, 6)
        stamp(fr, "VOID", W/2 + 270, 1010, t, sw_t + 0.1, RED, 110, -18)

def s_bench(fr, t, dur):
    # sunset gradient
    import numpy as np
    g = sprite("sunset", lambda: Image.fromarray(np.dstack([
        np.linspace(255, 120, H)[:, None].repeat(W, 1), np.linspace(170, 60, H)[:, None].repeat(W, 1),
        np.linspace(90, 120, H)[:, None].repeat(W, 1)]).astype("uint8")).convert("RGBA"))
    fr.alpha_composite(g)
    d = ImageDraw.Draw(fr)
    d.ellipse([W/2 - 260, 520, W/2 + 260, 1040], fill=(255, 220, 120, 255))
    d.rectangle([0, 1450, W, H], fill=(60, 110, 60))
    d.rounded_rectangle([150, 1330, W - 150, 1390], 14, fill=(130, 80, 40), outline=BLACK, width=6)
    d.rectangle([200, 1390, 230, 1520], fill=(90, 55, 25)); d.rectangle([W - 230, 1390, W - 200, 1520], fill=(90, 55, 25))
    blink = (t % 3.2) < 0.15
    put(fr, chipek("sad", "down", blink=blink) if blink else sprite("ch_sad", lambda: chipek("sad", "down")), W/2, 1130, 0.65)
    pop_box(fr, "TO NIE ODCINEK", 80, (255, 255, 255), W/2, 260, t, 0.1, fg=BLACK)
    pop_box(fr, "O ZŁYM PREZESIE", 80, (255, 255, 255), W/2, 390, t, 0.35, fg=BLACK)

def s_weak(fr, t, dur):
    bg_rays(fr, (90, 60, 160), (110, 78, 190), t, 6)
    pop_text(fr, "KAŻDY Z NAS", 140, W/2, 330, t, 0.0, fill=WHITE)
    pop_text(fr, "MA SŁABOŚCI", 140, W/2, 500, t, 0.25, fill=YELLOW)
    items = ["PIZZA O 2:00", "SCROLL DO 3:00", "„JESZCZE 5 MINUT”", "KOLEJNY KURS ONLINE"]
    for i, it in enumerate(items):
        pop_box(fr, it, 52, [(255, 255, 255), (255, 214, 0), (120, 220, 255), (255, 140, 180)][i], 300 + (i % 2) * 480, 900 + (i // 2) * 220 + bounce(t + i, 1, 8), t, 0.5 + i * 0.25, fg=BLACK, rot=(-6, 5, 4, -5)[i])
    put(fr, sprite("ch_shrug_h", lambda: chipek("happy", "shrug")), W/2, 1530, 0.55)

def s_jacket(fr, t, dur):
    bg_rays(fr, (12, 12, 16), (30, 30, 38), t, 6)
    pop_text(fr, "NIE KAŻDY NOSI", 100, W/2, 200, t, 0.0, fill=WHITE)
    pop_text(fr, "POD SKÓRZANĄ KURTKĄ", 90, W/2, 320, t, 0.25, fill=WHITE)
    put(fr, sprite("sky", skyscraper), W/2, 1050 - ease_out((t - 0.6) / 0.6) * 120 if t > 0.6 else 1200, 1.0 if t > 0.6 else 0.01)
    put(fr, sprite("ch_proud_sh", lambda: chipek("proud", "shrug")), W/2, 1300, 0.85)
    if t > 1.0:
        pop_text(fr, "SPÓŁKĘ ZA 4 BLN $", 120, W/2, 480, t, 1.0, fill=YELLOW)

def s_end(fr, t, dur):
    bg_rays(fr, (14, 34, 24), (22, 50, 34), t, 12)
    pop_text(fr, "O CZŁOWIEKU ZA FIRMĄ", 92, W/2, 230, t, 0.0, fill=WHITE)
    pop_text(fr, "GADAMY NA", 80, W/2, 350, t, 0.15, fill=YELLOW)
    logo = sprite("logo", lambda: Image.open("/home/claude/reel/logo_color.png").convert("RGBA"))
    if t > 0.25:
        put(fr, logo, W/2, 570, ease_out_back((t - 0.25) / 0.4) * 0.62)
    if t > 0.8:
        put(fr, sprite("ticket", ticket), W/2, 1110 + bounce(t, 1.2, 10), ease_out_back((t - 0.8) / 0.4) * 1.1, -4)
    put(fr, sprite("ch_happy_wave2", lambda: chipek("happy", "wave")), W/2, 1530, 0.5)
    if t > 1.5:
        pop_box(fr, "LINK W BIO", 80, (230, 90, 70), W/2, 1800, t, 1.5)

# plan scen: (akapit, ułamek_start, ułamek_koniec, funkcja)
PLAN = [
    (0, 0.0, 0.12, s_teaser), (0, 0.12, 0.555, s_hook_stage), (0, 0.555, 1.0, s_hook_crash),
    (1, 0.0, 0.2, s_what), (1, 0.2, 0.81, s_spy), (1, 0.81, 1.0, s_romance),
    (2, 0.0, 0.40, s_sorry), (2, 0.40, 0.77, s_deny), (2, 0.77, 1.0, s_board),
    (3, 0.0, 0.07, s_market_title), (3, 0.07, 0.27, s_monday), (3, 0.27, 0.5, s_tuesday),
    (3, 0.5, 0.66, s_lawsuit), (3, 0.66, 1.0, s_congress),
    (4, 0.0, 0.12, s_business), (4, 0.12, 0.61, s_pitch), (4, 0.61, 1.0, s_void),
    (5, 0.0, 0.31, s_bench), (5, 0.31, 0.5, s_weak), (5, 0.5, 1.0, s_jacket),
    (6, 0.0, 1.0, s_end),
]

def build_timeline():
    tl = []
    for i, (p, a, b, fn) in enumerate(PLAN):
        s0, s1 = SEG[p]
        start = s0 + (s1 - s0) * a
        end = s0 + (s1 - s0) * b
        if a == 0.0:
            start = SEG[p - 1][1] if p > 0 else 0.0  # wypełnij pauzę przed akapitem
        if p == len(SEG) - 1 and b == 1.0: end = TOTAL
        tl.append((start, end, fn))
    for i in range(len(tl) - 1):  # bez dziur
        tl[i] = (tl[i][0], tl[i + 1][0], tl[i][2])
    return tl

TL = build_timeline()

# ---------- napisy ----------
def caption_words():
    out = []
    if WORDS:
        return WORDS
    for p, (s0, s1) in zip(PARAS, SEG):
        ws = p.split()
        tot = sum(len(w) + 1 for w in ws); t = s0
        for w_ in ws:
            d = (s1 - s0) * (len(w_) + 1) / tot
            out.append([w_, t, t + d]); t += d
    return out
CW = caption_words()
CHUNKS = []
cur = []
for w_ in CW:
    cur.append(w_)
    if len(cur) >= 3 or w_[0][-1] in ".,?!:”" or sum(len(x[0]) for x in cur) > 16:
        CHUNKS.append(cur); cur = []
if cur: CHUNKS.append(cur)

def draw_caption(fr, t):
    for ch in CHUNKS:
        if ch[0][1] - 0.05 <= t < ch[-1][2] + 0.05:
            words = [w_[0].upper() for w_ in ch]
            sz = 92
            f = font("Anton", sz)
            while sum(f.getlength(w_ + " ") for w_ in words) > 980 and sz > 50:
                sz -= 4; f = font("Anton", sz)
            total = sum(f.getlength(w_ + " ") for w_ in words)
            x = W / 2 - total / 2; y = 1640
            d = ImageDraw.Draw(fr)
            k = ease_out_back((t - ch[0][1]) / 0.15)
            for w_, wd in zip(words, ch):
                col = YELLOW if wd[1] <= t < wd[2] + 0.05 else WHITE
                d.text((x + 6, y + 8), w_, font=f, fill=(0, 0, 0, 160), stroke_width=10, stroke_fill=(0, 0, 0, 160))
                d.text((x, y - (8 if col == YELLOW else 0)), w_, font=f, fill=col, stroke_width=10, stroke_fill=BLACK)
                x += f.getlength(w_ + " ")
            return

BADGE = None
def draw_badge(fr):
    global BADGE
    if BADGE is None: BADGE = label_box("BEKA Z PRZEDSIĘBIORCZOŚCI", 34, (40, 160, 80))
    fr.alpha_composite(BADGE, (40, 60))

def render_frame(t):
    fr = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    for (a, b, fn) in TL:
        if a <= t < b:
            lt = t - a
            fn(fr, lt, b - a)
            # punch-in na cięciu
            if lt < 0.12:
                k = 1.06 - 0.06 * (lt / 0.12)
                big = fr.resize((int(W * k), int(H * k)), Image.BILINEAR)
                fr = big.crop(((big.width - W) // 2, (big.height - H) // 2, (big.width - W) // 2 + W, (big.height - H) // 2 + H))
            if lt < 0.05:
                fr.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, 120)))
            break
    if t < SEG[-1][0] - 0.2:
        draw_caption(fr, t)
    draw_badge(fr)
    return fr.convert("RGB")

if __name__ == "__main__":
    out = next((a for a in sys.argv[1:] if a.endswith(".mp4")), "video_noaudio.mp4")
    prev = None
    if "--preview" in sys.argv:
        prev = [float(x) for x in sys.argv[sys.argv.index("--preview") + 1].split(",")]
        for s in prev:
            render_frame(s).save(f"prev_{s:05.1f}.png")
        sys.exit()
    n = int(TOTAL * FPS)
    if "--part" in sys.argv:
        k, m = [int(x) for x in sys.argv[sys.argv.index("--part") + 1].split("/")]
        rng = range(n * k // m, n * (k + 1) // m)
    else:
        rng = range(n)
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                          "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for i in rng:
        p.stdin.write(render_frame(i / FPS).tobytes())
        if i % 300 == 0: print(f"{i}/{n}", flush=True)
    p.stdin.close(); p.wait()
    print("done", out, TOTAL)
