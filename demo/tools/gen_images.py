"""Draw the pictures of the Northwind Notes sample site with Pillow.

Usage: python3 gen_images.py OUT_DIR

Writes nine .webp files (notes-*.webp) into OUT_DIR, which is created when missing. Nothing else is touched.
Needs Pillow and the DejaVu Sans fonts (the Linux path below; edit FONT, BOLD and MONO elsewhere).
"""

import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

if len(sys.argv) != 2 or sys.argv[1] in ("-h", "--help"):
    raise SystemExit(__doc__)

OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
S = 2
W, H = 1600, 1000
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

PAL = {
    "dark": dict(bg="#0f1316", win="#171d21", side="#12181b", card="#1f272c", line="#2b353b", text="#eef3f5", mute="#8b99a1", acc="#3bb3c4", acc2="#e8a33d", soft="#2a343a"),
    "light": dict(bg="#e9eef0", win="#fbfcfc", side="#f0f4f5", card="#ffffff", line="#d6dee2", text="#1b2428", mute="#6d7b83", acc="#1f8a9b", acc2="#c9831a", soft="#e3eaed"),
}


def f(size, face=FONT):
    return ImageFont.truetype(face, int(size * S))


class Canvas:
    def __init__(self, p):
        self.p = p
        self.im = Image.new("RGB", (W * S, H * S), p["bg"])
        self.d = ImageDraw.Draw(self.im)

    def rect(self, x, y, w, h, fill, r=10, outline=None):
        self.d.rounded_rectangle([x * S, y * S, (x + w) * S, (y + h) * S], radius=r * S, fill=fill, outline=outline, width=S if outline else 0)

    def text(self, x, y, s, size, fill, face=FONT):
        self.d.text((x * S, y * S), s, font=f(size, face), fill=fill)

    def line(self, x1, y1, x2, y2, fill, w=1):
        self.d.line([x1 * S, y1 * S, x2 * S, y2 * S], fill=fill, width=int(w * S))

    def dot(self, cx, cy, r, fill):
        self.d.ellipse([(cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S], fill=fill)

    def bars(self, x, y, w, lines, fill, gap=22, h=9):
        for i, frac in enumerate(lines):
            self.rect(x, y + i * gap, w * frac, h, fill, r=4)

    def window(self, title):
        p = self.p
        self.rect(60, 50, W - 120, H - 100, p["win"], r=18, outline=p["line"])
        for i, c in enumerate(("#ec6a5e", "#f4bf4f", "#61c554")):
            self.dot(96 + i * 24, 84, 7, c)
        self.text(W / 2 - 60, 74, title, 17, p["mute"])
        self.line(61, 112, W - 61, 112, p["line"])

    def sidebar(self, active=0):
        p = self.p
        self.rect(61, 113, 270, H - 164, p["side"], r=0)
        self.line(331, 113, 331, H - 51, p["line"])
        names = ["All notes", "Field journal", "Trip planning", "Reading list", "Recipes", "Archive"]
        for i, n in enumerate(names):
            y = 140 + i * 52
            if i == active:
                self.rect(75, y - 8, 242, 40, p["soft"], r=9)
            self.rect(92, y + 4, 14, 14, p["acc"] if i == active else p["mute"], r=4)
            self.text(122, y, n, 18, p["text"] if i == active else p["mute"])
        self.text(92, H - 130, "Stored on this computer", 14, p["mute"])

    def save(self, name):
        im = self.im.resize((W, H), Image.LANCZOS)
        im.save(OUT / name, "WEBP", quality=88, method=6)


def hero(mode):
    p = PAL[mode]
    c = Canvas(p)
    c.window("Northwind Notes")
    c.sidebar(1)
    c.rect(350, 135, 300, H - 205, p["win"], r=0)
    c.text(372, 140, "Field journal", 22, p["text"], BOLD)
    items = [("Basalt columns, day two", 0.8), ("Tide table for the cove", 0.55), ("Glacier lake route", 0.7), ("Weather notes", 0.45), ("Gear check", 0.62)]
    for i, (t, fr) in enumerate(items):
        y = 190 + i * 120
        c.rect(364, y, 272, 104, p["soft"] if i == 0 else p["card"], r=12, outline=p["line"])
        c.text(382, y + 14, t, 16, p["text"], BOLD)
        c.bars(382, y + 50, 232, [fr, fr * 0.7], p["line"], gap=20, h=8)
    c.line(660, 113, 660, H - 51, p["line"])
    c.text(700, 150, "Basalt columns, day two", 36, p["text"], BOLD)
    c.rect(700, 214, 74, 26, p["soft"], r=13)
    c.text(714, 218, "geology", 13, p["acc"])
    c.rect(784, 214, 74, 26, p["soft"], r=13)
    c.text(798, 218, "coast", 13, p["acc2"])
    c.bars(700, 280, 780, [0.98, 0.92, 0.96, 0.6], p["mute"], gap=30, h=11)
    c.rect(700, 430, 780, 170, p["card"], r=14, outline=p["line"])
    c.text(724, 448, "Linked notes", 15, p["mute"])
    for i, t in enumerate(["Tide table for the cove", "Glacier lake route", "Gear check"]):
        c.rect(724 + i * 250, 490, 232, 80, p["soft"], r=10)
        c.text(740 + i * 250, 520, t, 15, p["text"])
    c.bars(700, 640, 780, [0.9, 0.97, 0.5], p["mute"], gap=30, h=11)
    c.rect(700, 760, 220, 56, p["acc"], r=12)
    c.text(738, 775, "Export notes", 18, "#08181b", BOLD)
    c.save(f"notes-hero-{mode}.webp")


def board(mode):
    p = PAL[mode]
    c = Canvas(p)
    c.window("Northwind Notes - All notes")
    c.sidebar(0)
    titles = ["Basalt columns", "Tide table", "Glacier lake route", "Weather notes", "Gear check", "Ferry times", "Soup, take three", "Reading: Ch. 4", "Trail map scan"]
    for i, t in enumerate(titles):
        col, row = i % 3, i // 3
        x, y = 370 + col * 390, 140 + row * 270
        c.rect(x, y, 366, 246, p["card"], r=14, outline=p["line"])
        c.rect(x + 20, y + 20, 10, 10, [p["acc"], p["acc2"], p["mute"]][(i + row) % 3], r=5)
        c.text(x + 40, y + 14, t, 19, p["text"], BOLD)
        c.bars(x + 24, y + 70, 318, [0.95, 0.88, 0.7, 0.9], p["line"], gap=28, h=10)
        c.rect(x + 24, y + 196, 72, 24, p["soft"], r=12)
        c.text(x + 36, y + 199, "tag", 13, p["mute"])
    c.save(f"notes-board-{mode}.webp")


def editor(mode):
    p = PAL[mode]
    c = Canvas(p)
    c.window("Northwind Notes - Trip planning")
    c.rect(61, 113, 250, H - 164, p["side"], r=0)
    c.line(311, 113, 311, H - 51, p["line"])
    c.text(86, 136, "Outline", 15, p["mute"])
    for i, t in enumerate(["Overview", "Getting there", "Day one", "Day two", "Packing"]):
        c.text(86, 176 + i * 44, t, 18, p["text"] if i == 2 else p["mute"])
    c.rect(330, 125, 600, 80, p["win"], r=0)
    c.text(350, 140, "Source", 15, p["acc"])
    code = ["# Day one", "", "Take the early ferry.", "Walk the **north ridge**", "and log the stops:", "", "- [x] coffee at the pier", "- [ ] photos at the cove"]
    for i, s in enumerate(code):
        c.text(350, 190 + i * 40, s, 18, p["text"] if s else p["mute"], MONO)
    c.line(940, 113, 940, H - 51, p["line"])
    c.text(970, 140, "Preview", 15, p["acc2"])
    c.text(970, 190, "Day one", 40, p["text"], BOLD)
    c.text(970, 260, "Take the early ferry.", 20, p["text"])
    c.text(970, 296, "Walk the north ridge and log the stops:", 18, p["mute"])
    for i, t in enumerate(["coffee at the pier", "photos at the cove"]):
        c.rect(970, 360 + i * 56, 24, 24, p["acc"] if i == 0 else p["soft"], r=6, outline=None if i == 0 else p["line"])
        c.text(1010, 360 + i * 56, t, 19, p["text"])
    c.rect(970, 560, 530, 220, p["card"], r=14, outline=p["line"])
    c.text(994, 578, "Compare", 15, p["mute"])
    c.bars(994, 626, 480, [0.9, 0.75, 0.82, 0.6], p["line"], gap=34, h=12)
    c.save(f"notes-editor-{mode}.webp")


def sync():
    p = PAL["dark"]
    c = Canvas(p)
    c.window("Northwind Notes - Export")
    rows = [("Field journal", 0.92, "48 notes"), ("Trip planning", 0.64, "31 notes"), ("Recipes", 0.38, "27 notes")]
    for i, (t, fr, n) in enumerate(rows):
        y = 170 + i * 190
        c.rect(110, y, W - 220, 150, p["card"], r=16, outline=p["line"])
        c.text(144, y + 26, t, 24, p["text"], BOLD)
        c.text(144, y + 68, n + " to a folder of plain files", 17, p["mute"])
        c.rect(144, y + 108, W - 400, 14, p["soft"], r=7)
        c.rect(144, y + 108, (W - 400) * fr, 14, p["acc"], r=7)
        c.text(W - 230, y + 56, f"{int(fr * 100)}%", 30, p["acc"], BOLD)
    c.rect(110, 760, 240, 60, p["acc"], r=14)
    c.text(150, 777, "Export all", 20, "#08181b", BOLD)
    c.save("notes-export.webp")


def activity(mode):
    p = PAL[mode]
    c = Canvas(p)
    c.rect(270, 110, 1060, 780, p["win"], r=18, outline=p["line"])
    c.text(310, 150, "Notes written each week", 28, p["text"], BOLD)
    c.text(310, 196, "Beta, first sixteen weeks", 17, p["mute"])
    vals = [4, 7, 5, 9, 12, 8, 14, 11, 16, 13, 18, 15, 20, 17, 22, 19]
    base, top = 800, 270
    for i, v in enumerate(vals):
        h = (base - top) * v / 22
        x = 312 + i * 62
        c.rect(x, base - h, 40, h, p["acc"] if i % 4 != 3 else p["acc2"], r=7)
        c.text(x + 4, base + 14, f"W{i + 1}", 12, p["mute"])
    c.line(300, base, 1300, base, p["line"], 2)
    c.save(f"notes-activity-{mode}.webp")


for m in ("dark", "light"):
    hero(m)
    board(m)
    editor(m)
    activity(m)
sync()
print(sorted(x.name for x in OUT.iterdir()))
