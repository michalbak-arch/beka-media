"""Postacie i rekwizyty rysowane w PIL (styl Beki z Przedsiębiorczości)."""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import math, random

F = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts") + "/"
from functools import lru_cache
@lru_cache(maxsize=None)
def font(name, size):
    return ImageFont.truetype(F + name + ".ttf", size)

GREEN = (22, 92, 52)
GREEN_D = (12, 58, 32)
GREEN_L = (60, 160, 90)
GOLD = (230, 182, 60)
GOLD_D = (170, 120, 30)
BLACK = (18, 18, 22)
WHITE = (255, 255, 255)
RED = (230, 40, 45)
YELLOW = (255, 214, 0)
SKIN = (240, 200, 160)


def _canvas(w, h):
    return Image.new("RGBA", (w, h), (0, 0, 0, 0))


def chipek(expr="happy", arms="down", jacket=True, scale=1.0, blink=False):
    """Chipek: zielony chip w skórzanej kurtce. Zwraca sprite RGBA ~ 600x900 * scale."""
    W, H = 700, 1000
    im = _canvas(W, H)
    d = ImageDraw.Draw(im)
    cx = W // 2
    bx0, by0, bx1, by1 = cx - 210, 120, cx + 210, 540  # body
    # legs
    for lx in (cx - 85, cx + 85):
        d.line([(lx, by1 - 10), (lx, by1 + 250)], fill=GOLD, width=26)
        d.line([(lx, by1 - 10), (lx, by1 + 250)], fill=GOLD_D, width=6)
        # sneaker
        sx = lx + (-20 if lx < cx else 20)
        d.rounded_rectangle([sx - 75, by1 + 235, sx + 75, by1 + 300], 30, fill=WHITE, outline=BLACK, width=8)
        d.rectangle([sx - 70, by1 + 285, sx + 70, by1 + 296], fill=(200, 200, 205))
    # arms (drawn behind jacket sleeves)
    def arm(side, pose):
        sx = bx0 - 10 if side < 0 else bx1 + 10
        sy = by0 + 310
        if pose == "down":
            ex, ey = sx + side * 70, sy + 230
        elif pose == "up":
            ex, ey = sx + side * 110, sy - 260
        elif pose == "apology":
            ex, ey = cx + side * 40, sy + 120
        elif pose == "shrug":
            ex, ey = sx + side * 170, sy - 60
        elif pose == "hold":
            ex, ey = sx + side * 120, sy + 40
        elif pose == "wave" and side > 0:
            ex, ey = sx + 150, sy - 230
        else:
            ex, ey = sx + side * 70, sy + 230
        mx, my = (sx + ex) / 2 + side * 40, (sy + ey) / 2
        d.line([(sx, sy), (mx, my), (ex, ey)], fill=BLACK, width=58, joint="curve")
        d.line([(sx, sy), (mx, my), (ex, ey)], fill=(40, 40, 46), width=40, joint="curve")
        d.ellipse([ex - 34, ey - 34, ex + 34, ey + 34], fill=GOLD, outline=GOLD_D, width=6)
        return ex, ey
    hands = {}
    poses = {"down": ("down", "down"), "up": ("up", "up"), "apology": ("apology", "apology"),
             "shrug": ("shrug", "shrug"), "hold": ("down", "hold"), "wave": ("down", "wave"),
             "holdboth": ("hold", "hold")}[arms]
    hands["l"] = arm(-1, poses[0])
    hands["r"] = arm(1, poses[1])
    # pins
    for i in range(9):
        y = by0 + 40 + i * 42
        d.rectangle([bx0 - 26, y, bx0, y + 18], fill=GOLD)
        d.rectangle([bx1, y, bx1 + 26, y + 18], fill=GOLD)
    for i in range(9):
        x = bx0 + 40 + i * 42
        d.rectangle([x, by0 - 26, x + 18, by0], fill=GOLD)
    # body
    d.rounded_rectangle([bx0, by0, bx1, by1], 34, fill=GREEN, outline=GREEN_D, width=10)
    # circuit traces
    rnd = random.Random(7)
    for i in range(14):
        x = rnd.randint(bx0 + 30, bx1 - 30)
        y = rnd.randint(by0 + 250, by1 - 40)
        l = rnd.randint(30, 90)
        d.line([(x, y), (x + l, y), (x + l + 20, y + 20)], fill=GREEN_L, width=5)
        d.ellipse([x - 7, y - 7, x + 7, y + 7], fill=GOLD)
    # heat spreader top
    d.rounded_rectangle([bx0 + 60, by0 - 50, bx1 - 60, by0 + 10], 14, fill=(30, 30, 34), outline=BLACK, width=6)
    # face
    ey = by0 + 150
    for ex in (cx - 85, cx + 85):
        if blink or expr == "sad_closed":
            d.arc([ex - 55, ey - 20, ex + 55, ey + 40], 200, 340, fill=BLACK, width=12)
        else:
            r = 62 if expr == "shock" else 52
            d.ellipse([ex - r, ey - r, ex + r, ey + r], fill=WHITE, outline=BLACK, width=8)
            pr = 18 if expr == "shock" else 24
            off = 8 if expr != "sad" else 0
            py = ey + (14 if expr == "sad" else 4)
            d.ellipse([ex - pr + off * (1 if ex > cx else -1) * 0, py - pr, ex + pr, py + pr], fill=BLACK)
            d.ellipse([ex - 6, py - 14, ex + 6, py - 2], fill=WHITE)
    # brows
    bw = 14
    if expr in ("happy", "proud"):
        d.line([(cx - 135, ey - 80), (cx - 40, ey - 92)], fill=BLACK, width=bw)
        d.line([(cx + 40, ey - 92), (cx + 135, ey - 80)], fill=BLACK, width=bw)
    elif expr == "shock":
        d.arc([cx - 150, ey - 140, cx - 30, ey - 60], 200, 340, fill=BLACK, width=bw)
        d.arc([cx + 30, ey - 140, cx + 150, ey - 60], 200, 340, fill=BLACK, width=bw)
    elif expr in ("sad", "sad_closed", "sorry"):
        d.line([(cx - 135, ey - 70), (cx - 40, ey - 95)], fill=BLACK, width=bw)
        d.line([(cx + 40, ey - 95), (cx + 135, ey - 70)], fill=BLACK, width=bw)
    elif expr == "worried":
        d.line([(cx - 135, ey - 75), (cx - 40, ey - 100)], fill=BLACK, width=bw)
        d.line([(cx + 40, ey - 100), (cx + 135, ey - 75)], fill=BLACK, width=bw)
    # mouth
    my = ey + 110
    if expr in ("happy", "proud"):
        d.chord([cx - 90, my - 50, cx + 90, my + 60], 0, 180, fill=BLACK)
        d.chord([cx - 60, my + 10, cx + 60, my + 58], 0, 180, fill=(220, 70, 80))
        d.rectangle([cx - 70, my + 5, cx + 70, my + 18], fill=WHITE)
    elif expr == "shock":
        d.ellipse([cx - 45, my - 30, cx + 45, my + 70], fill=BLACK)
        d.ellipse([cx - 28, my + 25, cx + 28, my + 62], fill=(220, 70, 80))
    elif expr in ("sad", "sad_closed"):
        d.arc([cx - 70, my, cx + 70, my + 80], 200, 340, fill=BLACK, width=12)
    elif expr == "sorry":
        d.line([(cx - 50, my + 20), (cx + 50, my + 20)], fill=BLACK, width=12)
        # sweat drop
        d.polygon([(bx1 - 40, ey - 90), (bx1 - 60, ey - 40), (bx1 - 20, ey - 40)], fill=(120, 190, 255))
        d.ellipse([bx1 - 62, ey - 60, bx1 - 18, ey - 18], fill=(120, 190, 255))
    elif expr == "worried":
        pts = [(cx - 70 + i * 20, my + 30 + (12 if i % 2 else -12)) for i in range(8)]
        d.line(pts, fill=BLACK, width=10)
    # jacket
    if jacket:
        jl = [(bx0 - 40, by0 + 285), (bx0 + 95, by0 + 330), (bx0 + 120, by1 + 40), (bx0 - 50, by1 + 40)]
        jr = [(bx1 + 40, by0 + 285), (bx1 - 95, by0 + 330), (bx1 - 120, by1 + 40), (bx1 + 50, by1 + 40)]
        for poly in (jl, jr):
            d.polygon(poly, fill=(28, 28, 32), outline=BLACK)
            d.line(poly + [poly[0]], fill=BLACK, width=8)
        # lapels + shine
        d.polygon([(bx0 - 40, by0 + 285), (bx0 + 95, by0 + 330), (bx0 + 30, by0 + 350)], fill=(55, 55, 62))
        d.polygon([(bx1 + 40, by0 + 285), (bx1 - 95, by0 + 330), (bx1 - 30, by0 + 350)], fill=(55, 55, 62))
        d.line([(bx0 + 10, by0 + 360), (bx0 + 30, by1 - 20)], fill=(90, 90, 100), width=6)
        d.line([(bx1 - 10, by0 + 360), (bx1 - 30, by1 - 20)], fill=(90, 90, 100), width=6)
        # zipper teeth
        for i in range(4):
            d.rectangle([bx0 + 102 + 6, by0 + 350 + i * 40, bx0 + 114, by0 + 370 + i * 40], fill=(150, 150, 160))
            d.rectangle([bx1 - 114, by0 + 350 + i * 40, bx1 - 108, by0 + 370 + i * 40], fill=(150, 150, 160))
    if scale != 1.0:
        im = im.resize((int(W * scale), int(H * scale)), Image.LANCZOS)
    return im


def spy():
    """Anonimowa sylwetka w prochowcu i kapeluszu ze znakiem zapytania (bez twarzy)."""
    W, H = 520, 980
    im = _canvas(W, H); d = ImageDraw.Draw(im)
    c = (35, 35, 48)
    d.polygon([(130, 330), (390, 330), (450, 900), (70, 900)], fill=c)        # coat
    d.polygon([(260, 330), (200, 520), (260, 600), (320, 520)], fill=(60, 60, 78))  # collar
    d.ellipse([170, 160, 350, 360], fill=c)                                     # head
    d.ellipse([90, 140, 430, 210], fill=c)                                      # hat brim
    d.rounded_rectangle([170, 40, 350, 180], 30, fill=c)                        # hat top
    d.rectangle([170, 140, 350, 165], fill=(150, 40, 40))                       # band
    d.rounded_rectangle([185, 235, 335, 275], 18, fill=(10, 10, 12))            # glasses
    d.line([(150, 900), (150, 960)], fill=c, width=40); d.line([(370, 900), (370, 960)], fill=c, width=40)
    f = font("Anton", 260)
    d.text((260, 600), "?", font=f, fill=YELLOW, anchor="mm", stroke_width=10, stroke_fill=BLACK)
    return im


def board_member(i):
    W, H = 260, 420
    im = _canvas(W, H); d = ImageDraw.Draw(im)
    suits = [(40, 50, 80), (60, 60, 66), (30, 40, 60), (70, 50, 50), (45, 45, 55)]
    ties = [RED, YELLOW, (60, 140, 220), (200, 80, 160), GREEN_L]
    d.rounded_rectangle([30, 190, 230, 420], 50, fill=suits[i % 5])
    d.polygon([(130, 200), (105, 260), (130, 360), (155, 260)], fill=ties[i % 5])
    d.polygon([(95, 190), (130, 230), (165, 190)], fill=WHITE)
    d.ellipse([60, 40, 200, 200], fill=SKIN, outline=(180, 140, 110), width=4)
    hair = [(60, 40, 30), (90, 90, 90), (200, 200, 200), (40, 30, 20), (120, 80, 40)]
    d.chord([58, 30, 202, 150], 180, 360, fill=hair[i % 5])
    d.ellipse([95, 105, 115, 125], fill=BLACK); d.ellipse([145, 105, 165, 125], fill=BLACK)
    d.line([(110, 160), (150, 160)], fill=BLACK, width=6)
    if i % 2 == 0:
        d.rounded_rectangle([82, 98, 128, 132], 10, outline=BLACK, width=5)
        d.rounded_rectangle([132, 98, 178, 132], 10, outline=BLACK, width=5)
    return im


def capitol(w=700):
    H = w
    im = _canvas(w, H); d = ImageDraw.Draw(im)
    wc = (245, 245, 240); sh = (170, 175, 190)
    cx = w // 2; u = w / 700
    d.rectangle([40*u, H-120*u, w-40*u, H-20*u], fill=wc, outline=sh, width=6)
    for i in range(9):
        x = 80*u + i * (w - 160*u) / 8
        d.rectangle([x-12*u, H-230*u, x+12*u, H-120*u], fill=wc, outline=sh, width=3)
    d.rectangle([60*u, H-252*u, w-60*u, H-228*u], fill=wc, outline=sh, width=4)
    d.rectangle([cx-160*u, H-330*u, cx+160*u, H-252*u], fill=wc, outline=sh, width=4)
    for i in range(7):
        x = cx-130*u + i*260*u/6
        d.rectangle([x-8*u, H-325*u, x+8*u, H-262*u], fill=(225,225,230))
    d.pieslice([cx-170*u, H-520*u, cx+170*u, H-180*u], 180, 360, fill=wc, outline=sh, width=5)
    d.rectangle([cx-24*u, H-590*u, cx+24*u, H-500*u], fill=wc, outline=sh, width=3)
    d.ellipse([cx-18*u, H-630*u, cx+18*u, H-590*u], fill=wc, outline=sh, width=3)
    return im


def gavel():
    im = _canvas(600, 600); d = ImageDraw.Draw(im)
    wood = (150, 90, 45); wd = (100, 55, 25)
    d.rounded_rectangle([60, 120, 420, 260], 40, fill=wood, outline=wd, width=10)
    d.rectangle([110, 110, 150, 270], fill=GOLD)
    d.rectangle([330, 110, 370, 270], fill=GOLD)
    d.line([(240, 260), (420, 560)], fill=wood, width=46)
    d.line([(240, 260), (420, 560)], fill=wd, width=10)
    return im


def truck():
    im = _canvas(760, 420); d = ImageDraw.Draw(im)
    d.rounded_rectangle([20, 60, 520, 330], 20, fill=(240, 240, 245), outline=BLACK, width=10)
    for r in range(3):
        for c in range(5):
            x, y = 60 + c * 90, 95 + r * 75
            d.rounded_rectangle([x, y, x + 70, y + 55], 8, fill=GREEN, outline=GOLD, width=5)
    d.rounded_rectangle([520, 140, 730, 330], 30, fill=RED, outline=BLACK, width=10)
    d.rounded_rectangle([570, 165, 700, 240], 12, fill=(160, 210, 255), outline=BLACK, width=6)
    for x in (130, 400, 640):
        d.ellipse([x - 55, 290, x + 55, 400], fill=BLACK); d.ellipse([x - 22, 323, x + 22, 367], fill=(170, 170, 175))
    return im


def heart(broken=False, size=400):
    im = _canvas(size, size); d = ImageDraw.Draw(im)
    s = size
    d.ellipse([s * .05, s * .1, s * .55, s * .6], fill=RED)
    d.ellipse([s * .45, s * .1, s * .95, s * .6], fill=RED)
    d.polygon([(s * .07, s * .45), (s * .93, s * .45), (s * .5, s * .95)], fill=RED)
    d.ellipse([s * .18, s * .2, s * .32, s * .32], fill=(255, 140, 140))
    if broken:
        d.line([(s * .5, s * .2), (s * .42, s * .4), (s * .58, s * .55), (s * .45, s * .72), (s * .52, s * .92)],
               fill=(255, 255, 255, 0), width=int(s * .05))
    return im


def newspaper(title, headline, w=760):
    h = int(w * 0.62)
    im = _canvas(w, h); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w, h], fill=(248, 245, 236), outline=(60, 60, 60), width=6)
    d.text((w // 2, 60), title, font=font("Anton", 70), fill=BLACK, anchor="mm")
    d.line([(30, 110), (w - 30, 110)], fill=BLACK, width=5)
    f = font("Inter-900", 50)
    y = 135
    for line in headline.split("\n"):
        d.text((40, y), line, font=f, fill=BLACK); y += 62
    for i in range(5):
        yy = y + 20 + i * 28
        if yy < h - 30:
            d.rectangle([40, yy, w - 40 - (i * 37 % 120), yy + 12], fill=(170, 170, 170))
    return im


def ticket():
    im = _canvas(820, 420); d = ImageDraw.Draw(im)
    d.rounded_rectangle([10, 10, 810, 410], 36, fill=YELLOW, outline=BLACK, width=12)
    d.ellipse([-40, 170, 40, 250], fill=(0, 0, 0, 0)); d.ellipse([780, 170, 860, 250], fill=(0, 0, 0, 0))
    for y in range(40, 390, 30):
        d.line([(600, y), (600, y + 15)], fill=BLACK, width=6)
    d.text((310, 120), "BILET", font=font("Anton", 90), fill=BLACK, anchor="mm")
    d.text((310, 230), "FOUNDERS MIND", font=font("Anton", 70), fill=BLACK, anchor="mm")
    d.text((310, 330), "KOD: BEKA20", font=font("Inter-900", 54), fill=RED, anchor="mm")
    tx=Image.new("RGBA",(380,140),(0,0,0,0)); ImageDraw.Draw(tx).text((190,70),"TANIEJ",font=font("Anton",100),fill=BLACK,anchor="mm"); im.alpha_composite(tx.rotate(90,expand=True),(635,20))
    return im


def skyscraper():
    im = _canvas(300, 620); d = ImageDraw.Draw(im)
    d.polygon([(150, 0), (175, 60), (125, 60)], fill=GOLD)
    d.rectangle([90, 60, 210, 620], fill=(60, 80, 110), outline=BLACK, width=6)
    d.rectangle([40, 200, 260, 620], fill=(70, 95, 130), outline=BLACK, width=6)
    for r in range(12):
        for c in range(4):
            col = YELLOW if (r * 3 + c) % 4 else (200, 230, 255)
            d.rectangle([60 + c * 50, 225 + r * 32, 90 + c * 50, 245 + r * 32], fill=col)
    return im


def podium():
    im = _canvas(560, 420); d = ImageDraw.Draw(im)
    d.polygon([(60, 40), (500, 40), (460, 420), (100, 420)], fill=(110, 70, 40), outline=BLACK)
    d.line([(60, 40), (500, 40), (460, 420), (100, 420), (60, 40)], fill=BLACK, width=8)
    d.rectangle([40, 20, 520, 60], fill=(140, 90, 50), outline=BLACK, width=8)
    for x in (230, 330):
        d.line([(x, 20), (x - 20 if x < 280 else x + 20, -90)], fill=(40, 40, 40), width=10)
        d.ellipse([(x - 20 if x < 280 else x + 20) - 22, -120, (x - 20 if x < 280 else x + 20) + 22, -70], fill=(60, 60, 60))
    return im


def warranty_sticker(void=False):
    im = _canvas(520, 300); d = ImageDraw.Draw(im)
    d.rounded_rectangle([10, 10, 510, 290], 40, fill=(250, 250, 250), outline=(30, 120, 220) if not void else RED, width=14)
    if not void:
        d.text((260, 100), "GWARANCJA", font=font("Anton", 90), fill=(30, 120, 220), anchor="mm")
        d.text((260, 200), "WIEMY, GDZIE TRAFIAJĄ", font=font("Inter-900", 30), fill=BLACK, anchor="mm")
        d.text((260, 245), "NASZE CHIPY", font=font("Inter-900", 30), fill=BLACK, anchor="mm")
    else:
        d.text((260, 110), "GWARANCJA", font=font("Anton", 90), fill=RED, anchor="mm")
        d.text((260, 215), "UTRACONA", font=font("Anton", 80), fill=RED, anchor="mm")
    return im
