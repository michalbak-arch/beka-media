"""Renderuje overlay.html do PNG z przezroczystością. Użycie: shoot.py out_dir a b [step] | shoot.py --times t1,t2 out.png"""
import sys, os, json
from playwright.sync_api import sync_playwright
here = os.path.dirname(os.path.abspath(__file__))
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--allow-file-access-from-files", "--disable-web-security", "--no-first-run", "--disable-sync", "--disable-background-networking", "--disable-component-update"])
    pg = b.new_page(viewport={"width": 1080, "height": 1920})
    logs = []; pg.on("console", lambda m: logs.append(m.text))
    pg.goto("file://" + here + "/overlay.html"); pg.wait_for_function("window.render!==undefined"); pg.evaluate("document.fonts.ready")
    if sys.argv[1] == "--times":
        for i, t in enumerate(map(float, sys.argv[2].split(","))):
            pg.evaluate(f"render({t})"); pg.screenshot(path=f"{sys.argv[3]}_{i:02d}.png", omit_background=True)
    else:
        out, a, z = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]); os.makedirs(out, exist_ok=True)
        for f in range(a, z):
            pg.evaluate(f"render({f/30})"); pg.screenshot(path=f"{out}/{f:05d}.png", omit_background=True)
    if logs: print("\n".join(logs[:20]))
    b.close()
