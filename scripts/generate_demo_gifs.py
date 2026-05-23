from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "web" / "assets" / "demo"
OUT_DIR.mkdir(parents=True, exist_ok=True)

WIDTH = 920
HEIGHT = 520
BG = "#111318"
PANEL = "#1e2128"
PANEL_2 = "#262a33"
TEXT = "#f2f4f8"
MUTED = "#aab2c0"
ACCENT = "#7dd3fc"
SUCCESS = "#8bdc88"
WARN = "#f7c76b"
BOT = "#b7a7ff"
USER = "#8ab4ff"
GRID = "#333946"


def font(size, bold=False):
    names = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for name in names:
        if Path(name).exists():
            return ImageFont.truetype(name, size)
    return ImageFont.load_default()


F_TITLE = font(34, True)
F_H = font(23, True)
F_BODY = font(21)
F_SMALL = font(16)
F_MONO = font(20)
F_MONO_B = font(20, True)


def rounded(draw, box, fill, outline=None, width=1, radius=18):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def text(draw, xy, value, fill=TEXT, fnt=F_BODY, anchor=None):
    draw.text(xy, value, fill=fill, font=fnt, anchor=anchor)


def wrap(draw, value, max_width, fnt):
    words = value.split()
    lines = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if draw.textbbox((0, 0), trial, font=fnt)[2] <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def base(title, subtitle):
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    d = ImageDraw.Draw(img)
    rounded(d, (24, 24, WIDTH - 24, HEIGHT - 24), PANEL, radius=22)
    text(d, (54, 48), title, fnt=F_TITLE)
    text(d, (56, 88), subtitle, fill=MUTED, fnt=F_SMALL)
    d.line((48, 120, WIDTH - 48, 120), fill="#333845", width=2)
    return img, d


def avatar(draw, x, y, color, label):
    draw.ellipse((x, y, x + 42, y + 42), fill=color)
    text(draw, (x + 21, y + 21), label, fill="#101218", fnt=font(18, True), anchor="mm")


def message(draw, y, speaker, color, lines, accent=None):
    avatar(draw, 58, y, color, speaker[:1].upper())
    text(draw, (112, y + 2), speaker, fill=color, fnt=F_H)
    box_top = y + 34
    line_h = 27
    box_h = max(54, 22 + line_h * len(lines))
    rounded(draw, (106, box_top, 840, box_top + box_h), PANEL_2, radius=12)
    if accent:
        draw.rounded_rectangle((106, box_top, 112, box_top + box_h), radius=4, fill=accent)
    yy = box_top + 13
    for line in lines:
        fill = TEXT
        fnt = F_BODY
        if line.startswith("$"):
            fill = ACCENT
            fnt = F_MONO_B
            line = line[1:]
        elif line.startswith(">"):
            fill = MUTED
            fnt = F_MONO
            line = line[1:]
        text(draw, (126, yy), line, fill=fill, fnt=fnt)
        yy += line_h
    return box_top + box_h + 18


def save_gif(name, frames, duration=900):
    path = OUT_DIR / name
    frames[0].save(
        path,
        save_all=True,
        append_images=frames[1:],
        duration=duration,
        loop=0,
        optimize=True,
    )
    print(path)


def roll_demo():
    frames = []
    steps = [
        [("devinb", USER, ["$!roll 3x 1d20+5"], None)],
        [
            ("devinb", USER, ["$!roll 3x 1d20+5"], None),
            ("DICEwithoutNumber", BOT, ["Rolling 3 times...", ">d20 + modifier"], ACCENT),
        ],
        [
            ("devinb", USER, ["$!roll 3x 1d20+5"], None),
            ("DICEwithoutNumber", BOT, ["3x 1d20+5", "Roll 1: (14) +5 = 19", "Roll 2: (7) +5 = 12", "Roll 3: (18) +5 = 23"], SUCCESS),
        ],
        [
            ("devinb", USER, ["$!roll 3x 1d20+5"], None),
            ("DICEwithoutNumber", BOT, ["3x 1d20+5", "Roll 1: (14) +5 = 19", "Roll 2: (7) +5 = 12", "Roll 3: (18) +5 = 23", "Grand Total: 54"], SUCCESS),
        ],
    ]
    for step in steps:
        img, d = base("Fast Dice For Without Number Tables", "Complex dice, repeats, keep/drop, and modifiers in one command.")
        y = 148
        for speaker, color, lines, accent in step:
            y = message(d, y, speaker, color, lines, accent)
        frames.append(img)
    save_gif("demo_roll.gif", frames)


def skill_demo():
    frames = []
    steps = [
        [("Pilot", USER, ["$/skill notice wisdom"], None)],
        [
            ("Pilot", USER, ["$/skill notice wisdom"], None),
            ("DICEwithoutNumber", BOT, ["Checking active character...", ">Notice 1 + Wisdom 1"], ACCENT),
        ],
        [
            ("Pilot", USER, ["$/skill notice wisdom"], None),
            ("DICEwithoutNumber", BOT, ["Skill Check: Notice", "Result: 10", "Details: (5, 3) +2 = 10", "Playing as Valerius"], SUCCESS),
        ],
    ]
    for step in steps:
        img, d = base("Character-Aware Skill Checks", "Players roll from their active sheet instead of retyping every modifier.")
        y = 148
        for speaker, color, lines, accent in step:
            y = message(d, y, speaker, color, lines, accent)
        frames.append(img)
    save_gif("demo_skill.gif", frames)


def attack_demo():
    frames = []
    steps = [
        [("Soldier", USER, ["$/attack laser rifle"], None)],
        [
            ("Soldier", USER, ["$/attack laser rifle"], None),
            ("DICEwithoutNumber", BOT, ["Attack: Laser Rifle", "To hit: (16) +3 = 19", "Damage: 1d10+1 ready to roll", "Playing as Mara Voss"], WARN),
        ],
        [
            ("Soldier", USER, ["$/roll 1d10+1 damage"], None),
            ("DICEwithoutNumber", BOT, ["1d10+1 (damage)", "Result: (8) +1 = 9"], SUCCESS),
        ],
    ]
    for step in steps:
        img, d = base("Attacks That Remember The Sheet", "Use weapon names and sheet bonuses instead of hunting through notes mid-fight.")
        y = 148
        for speaker, color, lines, accent in step:
            y = message(d, y, speaker, color, lines, accent)
        frames.append(img)
    save_gif("demo_attack.gif", frames)


def draw_grid(draw, x, y):
    cell = 42
    for row in range(6):
        for col in range(8):
            fill = "#202530" if (row + col) % 2 == 0 else "#242a35"
            draw.rectangle((x + col * cell, y + row * cell, x + (col + 1) * cell, y + (row + 1) * cell), fill=fill, outline=GRID)
    labels = {"Hero": (1, 3, SUCCESS), "Raider": (4, 2, WARN), "Drone": (6, 4, ACCENT)}
    for name, (col, row, color) in labels.items():
        cx = x + col * cell + cell // 2
        cy = y + row * cell + cell // 2
        draw.ellipse((cx - 15, cy - 15, cx + 15, cy + 15), fill=color)
        text(draw, (cx, cy), name[:1], fill="#12151b", fnt=font(16, True), anchor="mm")


def tracker_demo():
    frames = []
    captions = [
        ("$/tracker add Raider 12 14 2", "Add enemies in seconds."),
        ("$/tracker party", "Pull the party into initiative."),
        ("$/tracker map", "Open a tactical map for the whole table."),
        ("$/tracker move 2 E3", "Move tokens by coordinate while combat flows."),
    ]
    for command, caption in captions:
        img, d = base("GM Tracker And Tactical Map", "Combat state, tokens, and movement without leaving Discord.")
        message(d, 142, "GM", USER, [command], None)
        rounded(d, (486, 154, 842, 430), "#171b22", radius=14)
        draw_grid(d, 496, 166)
        text(d, (122, 250), caption, fill=TEXT, fnt=F_H)
        for idx, item in enumerate(["Hero  HP 18  AC 14", "Raider HP 12  AC 14", "Drone  HP 8   AC 16"]):
            rounded(d, (118, 292 + idx * 42, 428, 326 + idx * 42), "#252b35", radius=8)
            text(d, (132, 299 + idx * 42), item, fill=MUTED if idx else SUCCESS, fnt=F_SMALL)
        frames.append(img)
    save_gif("demo_tracker.gif", frames)


if __name__ == "__main__":
    roll_demo()
    skill_demo()
    attack_demo()
    tracker_demo()
