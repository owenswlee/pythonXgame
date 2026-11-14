"""
SKY HOPPER

Modes:   Solo Climb, 1 v 1, 2 v 2 and Ranked (computer hoppers play with you)
Extras:  Shop (hoppers + upgrades), power-ups, sky events, daily event, daily quests
Controls: Arrows / A D to move, P pause, M music, F11 fullscreen, mouse for menus
"""

######################載入套件######################

import pygame  # Import pygame for games
import sys  # Import system tools
import random  # Import random for platforms
import math  # Import math for waves and angles
import os  # Import os to find the save files
import json  # The save file is stored as JSON
import datetime  # Daily event, quests and login bonus
from array import array  # Used to build sound effects without sound files

######################遊戲常數######################

BG_X = 400  # Window width
BG_Y = 600  # Window height
CAMERA_LINE = 250  # While climbing, the player is kept at this height
PLATFORM_W = 64  # Platform width
PLATFORM_H = 12  # Platform height
WRAP_SPAN = BG_X + 34  # Sideways distance before a hopper wraps around the screen

GRAVITY = 0.5
JUMP_POWER = -12.5  # Normal jump (max height about 150 px)
SPRING_POWER = -21  # Spring jump
STOMP_POWER = -14  # Jump after stomping a monster
JET_SPEED = -11  # Flying speed with a jetpack
MOVE_ACCEL = 0.9
FRICTION = 0.86

HERE = os.path.dirname(os.path.abspath(__file__))
HIGHSCORE_FILE = os.path.join(HERE, "prjAI_highscore.txt")  # Old high score (read once)
SAVE_FILE = os.path.join(HERE, "prjAI_save.json")  # Coins, hoppers, rank, quests...

# Colors (RGB)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
INK = (30, 30, 60)
METAL = (80, 140, 230)
METAL_LIGHT = (160, 205, 255)
METAL_DARK = (40, 80, 150)
WOOD = (185, 125, 70)
WOOD_DARK = (110, 70, 35)
SPRING_COLOR = (255, 205, 50)
COIN = (255, 200, 40)
COIN_LIGHT = (255, 240, 150)
COIN_DARK = (200, 130, 20)
MONSTER = (160, 80, 200)
MONSTER_DARK = (100, 40, 140)
TEAM_BLUE = (90, 170, 255)
TEAM_RED = (255, 110, 110)
GOOD = (120, 235, 140)
BAD = (255, 120, 120)

# Sky colors at different heights (meters): (height, top color, bottom color)
SKY_STOPS = [
    (0, (100, 175, 255), (205, 235, 255)),
    (400, (80, 140, 235), (255, 215, 175)),
    (1000, (225, 105, 90), (255, 185, 115)),
    (1700, (65, 40, 110), (195, 85, 115)),
    (2600, (8, 8, 30), (35, 25, 75)),
]

# Zones change how the platforms look: (start height, name, top, top light, body, body dark)
ZONES = [
    (0, "Meadow", (90, 200, 90), (160, 240, 140), (135, 95, 60), (90, 60, 40)),
    (400, "Sunset Cliffs", (240, 150, 60), (255, 210, 120), (150, 90, 70), (100, 55, 45)),
    (1000, "Frost Peaks", (235, 245, 255), (255, 255, 255), (120, 150, 195), (75, 100, 145)),
    (1700, "Star Garden", (110, 250, 215), (210, 255, 245), (80, 65, 150), (45, 35, 95)),
]

######################商店資料######################

# Hoppers you can buy. Extra keys are perks: speed, jump, gravity, magnet, coin, shield
CHARACTERS = [
    {"id": "hopper", "name": "Hopper", "price": 0, "look": "blob", "perk": "The classic all-rounder",
     "body": (95, 220, 120), "dark": (40, 140, 70), "light": (175, 245, 180)},
    {"id": "kitty", "name": "Kitty", "price": 150, "look": "cat", "perk": "Quick paws: +15% move speed",
     "body": (250, 170, 80), "dark": (185, 105, 40), "light": (255, 225, 170), "speed": 1.15},
    {"id": "robo", "name": "Robo", "price": 300, "look": "robo", "perk": "Built-in coin magnet",
     "body": (150, 165, 190), "dark": (85, 95, 125), "light": (205, 220, 240), "magnet": 70},
    {"id": "pengu", "name": "Pengu", "price": 450, "look": "pengu", "perk": "Starts with a bubble shield",
     "body": (60, 75, 120), "dark": (30, 40, 75), "light": (245, 248, 255), "shield": 1},
    {"id": "ninja", "name": "Ninja", "price": 600, "look": "ninja", "perk": "Strong legs: +8% jump power",
     "body": (70, 60, 95), "dark": (35, 30, 55), "light": (250, 215, 185), "jump": 1.08},
    {"id": "boo", "name": "Boo", "price": 800, "look": "ghost", "perk": "Floaty: 15% less gravity",
     "body": (235, 240, 255), "dark": (165, 175, 215), "light": (255, 255, 255), "gravity": 0.85},
    {"id": "king", "name": "King", "price": 1200, "look": "king", "perk": "Royal tax: +50% coins",
     "body": (125, 115, 235), "dark": (70, 60, 160), "light": (200, 195, 255), "coin": 1.5},
    {"id": "zorp", "name": "Zorp", "price": 1600, "look": "alien", "perk": "Alien tech: speed, jump and magnet",
     "body": (90, 225, 200), "dark": (35, 135, 125), "light": (190, 255, 240),
     "speed": 1.1, "jump": 1.05, "magnet": 60},
]
CHAR_BY_ID = {c["id"]: c for c in CHARACTERS}

# Permanent upgrades. The price grows with every level
UPGRADES = [
    {"id": "magnet", "name": "Coin Magnet", "desc": "Pulls in coins from farther away", "max": 5, "base": 60},
    {"id": "wallet", "name": "Fat Wallet", "desc": "+10% coins per level", "max": 5, "base": 70},
    {"id": "shield", "name": "Bubble Shield", "desc": "Start every run with a shield", "max": 2, "base": 220},
    {"id": "battery", "name": "Long Battery", "desc": "Power-ups last 20% longer", "max": 5, "base": 80},
    {"id": "luck", "name": "Lucky Drops", "desc": "Power-ups show up more often", "max": 5, "base": 90},
]

POWER_COLORS = {"jet": (255, 130, 70), "shield": (90, 200, 255), "magnet": (235, 80, 100)}
POWER_NAMES = {"jet": "JETPACK!", "shield": "SHIELD!", "magnet": "MAGNET!"}

######################排位與對手資料######################

# Rank tiers: (rank points needed, name, color)
RANKS = [
    (0, "Bronze", (205, 127, 50)),
    (100, "Silver", (190, 200, 215)),
    (250, "Gold", (255, 205, 60)),
    (450, "Platinum", (110, 230, 215)),
    (700, "Diamond", (120, 175, 255)),
    (1000, "Master", (200, 115, 255)),
    (1400, "Legend", (255, 95, 95)),
]
BAND_POWER = {"1v1": 1.0, "2v2": 1.0, "ranked": 0.5, "attract": 1.5}  # How much bots adapt to your height
RANKED_COINS = [60, 35, 20, 10]  # Coin reward for 1st, 2nd, 3rd, 4th
RANKED_RP = [28, 12, -8, -18]  # Rank point change for 1st, 2nd, 3rd, 4th
ORDINALS = ["1st", "2nd", "3rd", "4th"]
PLACE_COLORS = [COIN_LIGHT, (215, 225, 240), (235, 160, 100), (190, 190, 200)]
FFA_TAGS = [(255, 170, 70), (255, 120, 200), (110, 235, 225)]  # Name colors in ranked

BOT_NAMES = ["Zippy", "Bolt", "Mochi", "Nova", "Pixel", "Turbo", "Luna", "Rex", "Bean", "Dash",
             "Coco", "Blitz", "Momo", "Sparky", "Juno", "Pogo", "Kiwi", "Ace", "Waffle", "Comet"]
CHAT_PASS = ["See ya!", "Zoom!", "Too slow!", "Catch me!"]
CHAT_PASSED = ["Hey!", "Wait up!", "No way!", "Whoa!"]
CHAT_MATE = ["Let's go!", "Follow me!", "Nice!", "We got this!"]
CHAT_HURT = ["Ouch!", "Oof!", "Yikes!"]

MODE_INFO = {  # mode: (title, how to win)
    "1v1": ("1 v 1 DUEL", "First to {goal} m wins!"),
    "2v2": ("2 v 2 TEAM CLIMB", "First team to climb {goal} m together"),
    "ranked": ("RANKED MATCH", "4 hoppers race to {goal} m"),
}
TIPS = [
    "Tip: bounce on other hoppers' heads for a free jump!",
    "Tip: springs launch you three times higher",
    "Tip: a bubble shield saves you from one hit",
    "Tip: cracked wooden platforms break. Skip them!",
    "Tip: fluffy cloud platforms only work once",
    "Tip: you can wrap around the sides of the screen",
]

######################活動與任務資料######################

# Sky events happen while you play
SKY_EVENTS = [
    {"id": "coins", "name": "COIN RAIN", "color": COIN, "time": 600},
    {"id": "moon", "name": "MOON GRAVITY", "color": (170, 190, 255), "time": 600},
    {"id": "wind", "name": "WIND STORM", "color": (200, 240, 255), "time": 540},
    {"id": "meteor", "name": "METEOR SHOWER", "color": (255, 130, 70), "time": 540},
    {"id": "spring", "name": "SPRING FEVER", "color": SPRING_COLOR, "time": 600},
]

# One daily event for each day of the week (Monday first). Extra keys are multipliers
DAILY_EVENTS = [
    {"name": "Coin Monday", "desc": "Every coin is worth double", "coin": 2},
    {"name": "Turbo Tuesday", "desc": "+50% rank points when you win", "rp": 1.5},
    {"name": "Wild Wednesday", "desc": "Sky events strike twice as often", "events": 2},
    {"name": "Thrifty Thursday", "desc": "Everything in the shop is 20% off", "sale": 0.8},
    {"name": "Spring Friday", "desc": "Twice as many springs", "springs": 2},
    {"name": "Super Saturday", "desc": "Double coin rewards from matches", "reward": 2},
    {"name": "Lucky Sunday", "desc": "Twice as many power-ups", "power": 2},
]

# Three of these are picked every day. "best" quests keep your best single run
QUESTS = [
    {"id": "coins", "text": "Collect {n} coins", "n": 40, "reward": 60},
    {"id": "stomp", "text": "Stomp {n} monsters", "n": 5, "reward": 70},
    {"id": "height", "text": "Reach {n} m in a Solo run", "n": 600, "reward": 80, "best": True},
    {"id": "springs", "text": "Bounce on {n} springs", "n": 8, "reward": 50},
    {"id": "wins", "text": "Win {n} matches", "n": 2, "reward": 100},
    {"id": "matches", "text": "Play {n} matches", "n": 3, "reward": 60},
    {"id": "power", "text": "Grab {n} power-ups", "n": 4, "reward": 50},
    {"id": "climb", "text": "Climb {n} m in total", "n": 2000, "reward": 70},
]
QUEST_BY_ID = {q["id"]: q for q in QUESTS}

DEFAULT_SAVE = {
    "coins": 0,
    "high_score": 0,
    "owned": ["hopper"],
    "character": "hopper",
    "upgrades": {},
    "rp": 0,
    "stats": {},
    "daily": {"date": "", "streak": 0, "quests": []},
    "music": True,
}

######################小工具函式######################


def lerp(a, b, t):
    """Blend two numbers: t=0 gives a, t=1 gives b"""
    return a + (b - a) * t


def mix(c1, c2, t):
    """Blend two colors"""
    return tuple(int(lerp(c1[i], c2[i], t)) for i in range(3))


def clamp(value, low=0.0, high=1.0):
    """Keep a value between low and high"""
    return max(low, min(high, value))


def ease(t):
    """Smooth slide: fast at first, gentle at the end"""
    t = clamp(t)
    return 1 - (1 - t) ** 3


def wrap_dx(dx):
    """Shortest sideways distance on a screen that wraps around"""
    return (dx + WRAP_SPAN / 2) % WRAP_SPAN - WRAP_SPAN / 2


def sky_colors(height):
    """Return (top color, bottom color) of the sky for a height"""
    for i in range(len(SKY_STOPS) - 1):
        h0, top0, bottom0 = SKY_STOPS[i]
        h1, top1, bottom1 = SKY_STOPS[i + 1]
        if height < h1:
            t = (height - h0) / (h1 - h0)
            return mix(top0, top1, t), mix(bottom0, bottom1, t)
    return SKY_STOPS[-1][1], SKY_STOPS[-1][2]


def zone_of(height):
    """Which zone a height belongs to"""
    zone = 0
    for i, info in enumerate(ZONES):
        if height >= info[0]:
            zone = i
    return zone


def rank_tier(rp):
    """Which rank tier a number of rank points belongs to"""
    tier = 0
    for i, info in enumerate(RANKS):
        if rp >= info[0]:
            tier = i
    return tier


def rotated_rect_points(cx, cy, w, h, angle):
    """Corners of a rectangle turned by an angle (used for broken platforms)"""
    c, s = math.cos(angle), math.sin(angle)
    points = []
    for dx, dy in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)):
        points.append((cx + dx * c - dy * s, cy + dx * s + dy * c))
    return points


def star_points(cx, cy, r_out, r_in, n=5):
    """Corners of a star shape"""
    points = []
    for i in range(n * 2):
        r = r_out if i % 2 == 0 else r_in
        a = -math.pi / 2 + i * math.pi / n
        points.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    return points


def fmt_time(frames):
    seconds = frames // 60
    return f"{seconds // 60}:{seconds % 60:02d}"


######################初始化設定######################

pygame.mixer.pre_init(22050, -16, 1, 512)
pygame.init()  # Initialize pygame
FPS = pygame.time.Clock()  # Create the frame clock

pygame.display.set_caption("Sky Hopper")  # Window title
try:
    # SCALED keeps the game 400x600 inside, but the window can be resized or made fullscreen
    screen = pygame.display.set_mode((BG_X, BG_Y), pygame.SCALED | pygame.RESIZABLE)
except pygame.error:
    screen = pygame.display.set_mode((BG_X, BG_Y))  # Create the window
world = pygame.Surface((BG_X, BG_Y))  # The game is drawn here first, so it can shake


def load_font(size):
    return pygame.font.SysFont("arialrounded,verdana,arial", size, bold=True)


font_title = load_font(54)
font_big = load_font(40)
font_mid = load_font(26)
font_small = load_font(18)
font_tiny = load_font(14)

######################文字與特效工具######################

text_cache = {}  # Rendered text is kept here, so it is not rebuilt every frame
glow_cache = {}
OUTLINE_OFFSETS = ((-2, 0), (2, 0), (0, -2), (0, 2), (-2, -2), (2, 2), (-2, 2), (2, -2))


def text_image(text, font, color, alpha=None):
    key = (text, id(font), color, alpha)
    img = text_cache.get(key)
    if img is None:
        if len(text_cache) > 700:
            text_cache.clear()
        img = font.render(text, True, color)
        if alpha is not None:
            img.set_alpha(alpha)
        text_cache[key] = img
    return img


def draw_text(surf, text, font, pos, color=WHITE, anchor="center", outline=None, shadow=True):
    """Draw text with an optional outline and soft shadow"""
    img = text_image(text, font, color)
    rect = img.get_rect(**{anchor: (int(pos[0]), int(pos[1]))})
    if outline:
        edge = text_image(text, font, outline)
        for dx, dy in OUTLINE_OFFSETS:
            surf.blit(edge, rect.move(dx, dy))
    elif shadow:
        surf.blit(text_image(text, font, BLACK, 110), rect.move(2, 3))
    surf.blit(img, rect)
    return rect


def wrap_text(text, font, width):
    """Split text into lines that fit a width"""
    lines, line = [], ""
    for word in text.split():
        test = (line + " " + word).strip()
        if font.size(test)[0] <= width or not line:
            line = test
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def draw_panel(surf, rect, alpha=150, border=(255, 255, 255), radius=18):
    """See-through dark box with rounded corners"""
    rect = pygame.Rect(rect)
    panel = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(panel, (10, 10, 25, alpha), panel.get_rect(), border_radius=radius)
    pygame.draw.rect(panel, (*border, 70), panel.get_rect(), 2, border_radius=radius)
    surf.blit(panel, rect)


def glow_image(radius, color):
    """A soft ball of light. It is drawn with ADD blending, so it brightens what is behind it"""
    key = (radius, color)
    surf = glow_cache.get(key)
    if surf is None:
        if len(glow_cache) > 400:
            glow_cache.clear()
        surf = pygame.Surface((radius * 2, radius * 2))
        for r in range(radius, 0, -1):
            k = (1 - r / radius) ** 2
            pygame.draw.circle(surf, (int(color[0] * k), int(color[1] * k), int(color[2] * k)), (radius, radius), r)
        glow_cache[key] = surf
    return surf


def add_glow(surf, x, y, radius, color):
    surf.blit(glow_image(radius, color), (int(x) - radius, int(y) - radius), special_flags=pygame.BLEND_RGB_ADD)


def draw_coin_icon(surf, x, y, r=8):
    pygame.draw.circle(surf, COIN_DARK, (int(x), int(y) + 1), r)
    pygame.draw.circle(surf, COIN, (int(x), int(y)), r)
    pygame.draw.circle(surf, COIN_LIGHT, (int(x), int(y)), max(2, r - 3))


def draw_rank_badge(surf, cx, cy, tier, s=16):
    """A shield in the color of the rank tier, with a star"""
    color = RANKS[tier][2]
    shape = [(cx - s, cy - s), (cx + s, cy - s), (cx + s, cy + s * 0.25), (cx, cy + s * 1.15), (cx - s, cy + s * 0.25)]
    pygame.draw.polygon(surf, mix(color, BLACK, 0.55), [(x, y + 3) for x, y in shape])
    pygame.draw.polygon(surf, color, shape)
    inner = [(cx + (x - cx) * 0.72, cy + (y - cy) * 0.72) for x, y in shape]
    pygame.draw.polygon(surf, mix(color, WHITE, 0.35), inner)
    pygame.draw.polygon(surf, mix(color, BLACK, 0.35), shape, 2)
    pygame.draw.polygon(surf, WHITE, star_points(cx, cy - s * 0.1, s * 0.5, s * 0.22))


def draw_power_icon(surf, kind, x, y):
    """Small white picture for each power-up"""
    x, y = int(x), int(y)
    if kind == "jet":
        pygame.draw.polygon(surf, WHITE, [(x, y - 9), (x + 5, y - 2), (x - 5, y - 2)])
        pygame.draw.rect(surf, WHITE, (x - 4, y - 2, 8, 7))
        pygame.draw.polygon(surf, COIN, [(x - 3, y + 5), (x + 3, y + 5), (x, y + 10)])
    elif kind == "shield":
        pygame.draw.circle(surf, WHITE, (x, y), 8, 2)
        pygame.draw.arc(surf, WHITE, (x - 5, y - 5, 10, 10), 1.6, 3.0, 2)
    else:
        pygame.draw.arc(surf, WHITE, (x - 7, y - 6, 14, 14), math.pi, math.tau, 4)
        pygame.draw.rect(surf, WHITE, (x - 7, y - 7, 4, 9))
        pygame.draw.rect(surf, WHITE, (x + 3, y - 7, 4, 9))
        pygame.draw.rect(surf, COIN, (x - 7, y - 8, 4, 3))
        pygame.draw.rect(surf, COIN, (x + 3, y - 8, 4, 3))


######################音效######################

AUDIO = pygame.mixer.get_init() is not None


def make_sound(notes, volume=0.25, wave="square"):
    """
    Build a retro sound effect from code \n
    notes: list of (start frequency, end frequency, seconds) \n
    wave: "square", "sine" or "noise" \n
    """
    if not AUDIO:
        return None
    try:
        rate, _, channels = pygame.mixer.get_init()
        buf = array("h")
        phase = 0.0
        for f0, f1, duration in notes:
            n = int(rate * duration)
            for i in range(n):
                t = i / n
                phase += lerp(f0, f1, t) / rate
                if wave == "square":
                    sample = 1.0 if phase % 1 < 0.5 else -1.0
                elif wave == "noise":
                    sample = random.uniform(-1, 1)
                else:
                    sample = math.sin(phase * math.tau)
                envelope = min(1.0, i / (rate * 0.005)) * (1 - t)  # Quick fade in, slow fade out
                value = int(sample * envelope * volume * 32767)
                buf.extend([value] * channels)
        return pygame.mixer.Sound(buffer=buf.tobytes())
    except (pygame.error, ValueError, TypeError):
        return None


def make_music():
    """A gentle looping tune built from four chords (C, Am, F, G)"""
    if not AUDIO:
        return None
    try:
        rate, _, channels = pygame.mixer.get_init()
        chords = [(262, 330, 392), (220, 262, 330), (175, 220, 262), (196, 247, 294)]
        pattern = (0, 1, 2, 1, 0, 2, 1, 2)
        n = int(rate * 0.2)  # Samples in one note
        buf = array("h")
        for chord in chords:
            for step in pattern:
                melody, bass = chord[step] * 2, chord[0] / 2
                for i in range(n):
                    t = i / rate
                    envelope = min(1.0, i / 150) * (1 - i / n) ** 1.5
                    sample = math.sin(math.tau * melody * t) * 0.55 + math.sin(math.tau * bass * t) * 0.45
                    buf.extend([int(sample * envelope * 0.11 * 32767)] * channels)
        return pygame.mixer.Sound(buffer=buf.tobytes())
    except (pygame.error, ValueError, TypeError):
        return None


SOUNDS = {
    "jump": make_sound([(300, 620, 0.12)], 0.12),
    "spring": make_sound([(250, 1300, 0.32)], 0.14),
    "break": make_sound([(0, 0, 0.22)], 0.22, "noise"),
    "coin": make_sound([(988, 988, 0.06), (1319, 1319, 0.2)], 0.3, "sine"),
    "stomp": make_sound([(650, 150, 0.16)], 0.16),
    "hurt": make_sound([(500, 80, 0.45)], 0.16),
    "fall": make_sound([(800, 120, 0.8)], 0.3, "sine"),
    "milestone": make_sound([(660, 660, 0.08), (880, 880, 0.08), (1320, 1320, 0.25)], 0.3, "sine"),
    "click": make_sound([(720, 720, 0.04)], 0.1),
    "buy": make_sound([(660, 660, 0.07), (880, 880, 0.07), (1320, 1320, 0.07), (1760, 1760, 0.22)], 0.3, "sine"),
    "error": make_sound([(210, 150, 0.2)], 0.14),
    "power": make_sound([(400, 900, 0.12), (900, 1500, 0.2)], 0.3, "sine"),
    "pop": make_sound([(900, 200, 0.14)], 0.3, "sine"),
    "beep": make_sound([(660, 660, 0.14)], 0.3, "sine"),
    "go": make_sound([(990, 990, 0.4)], 0.3, "sine"),
    "win": make_sound([(523, 523, 0.1), (659, 659, 0.1), (784, 784, 0.1), (1047, 1047, 0.4)], 0.3, "sine"),
    "lose": make_sound([(440, 440, 0.15), (370, 370, 0.15), (294, 294, 0.45)], 0.3, "sine"),
    "event": make_sound([(520, 520, 0.09), (780, 780, 0.09), (1040, 1040, 0.25)], 0.1),
    "boom": make_sound([(0, 0, 0.35)], 0.25, "noise"),
}
MUSIC = make_music()


def play(name):
    sound = SOUNDS.get(name)
    if sound:
        sound.play()


def set_music(on):
    """Start or stop the background tune"""
    if MUSIC:
        MUSIC.stop()
        if on:
            MUSIC.play(loops=-1)


######################存檔######################


def load_save():
    """Read the save file. Anything missing or broken is replaced by the default"""
    data = None
    try:
        with open(SAVE_FILE) as f:
            data = json.load(f)
    except (OSError, ValueError):
        pass
    first_time = not isinstance(data, dict)
    if first_time:
        data = {}
    for key, value in DEFAULT_SAVE.items():
        if type(data.get(key)) is not type(value):
            data[key] = json.loads(json.dumps(value))  # A fresh copy of the default
    if first_time:  # Keep the best score from the older version of the game
        try:
            with open(HIGHSCORE_FILE) as f:
                data["high_score"] = int(f.read().strip() or 0)
        except (OSError, ValueError):
            pass
    for key, value in DEFAULT_SAVE["daily"].items():  # The same check for the daily part
        if type(data["daily"].get(key)) is not type(value):
            data["daily"][key] = json.loads(json.dumps(value))
    data["upgrades"] = {k: v for k, v in data["upgrades"].items() if type(v) is int}
    data["stats"] = {k: v for k, v in data["stats"].items() if type(v) is int}
    data["owned"] = [c for c in data["owned"] if c in CHAR_BY_ID] or ["hopper"]
    if "hopper" not in data["owned"]:
        data["owned"].insert(0, "hopper")
    if data["character"] not in data["owned"]:
        data["character"] = "hopper"
    return data


def save_game():
    try:
        with open(SAVE_FILE, "w") as f:
            json.dump(save, f, indent=1)
    except OSError:
        pass


save = load_save()
today = datetime.date.today()
today_event = DAILY_EVENTS[today.weekday()]
toasts = []  # Little messages that slide in at the top: [text, color, frames left]


def daily(key):
    """Multiplier from today's daily event (1 when today's event does not change it)"""
    return today_event.get(key, 1)


def toast(text, color=WHITE):
    toasts.append([text, color, 200])


def refresh_daily():
    """On the first launch of a new day: login bonus, streak and three new quests"""
    info = save["daily"]
    quests_ok = len(info["quests"]) == 3 and all(
        isinstance(q, dict) and q.get("id") in QUEST_BY_ID and type(q.get("p")) is int and type(q.get("done")) is bool
        for q in info["quests"])
    if info["date"] == today.isoformat() and quests_ok:
        return
    if info["date"] != today.isoformat():
        yesterday = (today - datetime.timedelta(days=1)).isoformat()
        info["streak"] = info["streak"] + 1 if info["date"] == yesterday else 1
        bonus_coins = min(100, 40 + 10 * info["streak"])
        save["coins"] += bonus_coins
        toast(f"Daily bonus!  +{bonus_coins} coins  (day {info['streak']})", COIN_LIGHT)
    info["date"] = today.isoformat()
    picker = random.Random(today.toordinal())  # Same quests all day
    info["quests"] = [{"id": q["id"], "p": 0, "done": False} for q in picker.sample(QUESTS, 3)]
    save_game()


def quest_progress(quest_id, amount=1):
    """Add progress to a daily quest and pay the reward when it is finished"""
    for quest in save["daily"]["quests"]:
        if quest["id"] != quest_id or quest["done"]:
            continue
        info = QUEST_BY_ID[quest_id]
        quest["p"] = max(quest["p"], amount) if info.get("best") else quest["p"] + amount
        if quest["p"] >= info["n"]:
            quest["p"] = info["n"]
            quest["done"] = True
            save["coins"] += info["reward"]
            toast(f"Quest done!  +{info['reward']} coins", COIN_LIGHT)
            play("buy")
            save_game()


def upgrade_level(upgrade_id):
    return int(save["upgrades"].get(upgrade_id, 0))


def upgrade_price(upgrade):
    return int(upgrade["base"] * 1.6 ** upgrade_level(upgrade["id"]) * daily("sale"))


def character_price(char):
    return int(char["price"] * daily("sale"))


def my_character():
    return CHAR_BY_ID.get(save["character"], CHARACTERS[0])


######################遊戲狀態變數######################

state = "menu"  # "menu", "shop", "quests", "intro", "countdown", "play", "paused", "dying", "over", "finish", "results"
state_t = 0  # Frames spent in the current state
mode = "attract"  # "attract" (menu background), "solo", "1v1", "2v2" or "ranked"
ticks = 0
racers = []  # Every hopper in the game (you and the computer players)
me = None  # The hopper the camera follows
platforms, coins, monsters, powerups, meteors, particles, popups = [], [], [], [], [], [], []
top_y = 0  # Height of the highest platform row made so far
row_cx = BG_X / 2  # Middle of the platform in that row
bonus = 0  # Solo points from coins and stomps
shake = 0.0
flash = 0.0
next_milestone = 500
rows_since_monster = 0
new_best = False
goal = 0  # Height needed to win a match
zone_scale = 1.0  # Matches are short, so the sky changes faster
diff_bonus = 0  # Matches start harder than Solo
match_t = 0
finish_order = []
result = None  # Filled in when a match ends
sky_event = None  # The sky event happening right now
event_wait = 900  # Frames until the next sky event
wind_now = 0.0  # Sideways push from the wind
gravity_scale = 1.0  # Lower during Moon Gravity
zone_index = 0
match_tip = 0  # Which tip is shown before the match
autopilot = None  # Set to a BotBrain to let the computer play for you (used for testing)

######################物件類別######################


class Particle:
    def __init__(self, x, y, vx, vy, color, size, life, gravity=0.15, glow=False):
        """A small dot that flies, shrinks and disappears"""
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.color = color
        self.size = size
        self.life = self.max_life = life
        self.gravity = gravity
        self.glow = glow

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += self.gravity
        self.vx *= 0.98
        self.life -= 1

    def draw(self, surf, cam):
        radius = self.size * self.life / self.max_life
        if radius >= 0.5:
            x, y = int(self.x), int(self.y - cam)
            if self.glow:
                add_glow(surf, x, y, int(radius * 3) + 3, mix(self.color, BLACK, 0.55))
            pygame.draw.circle(surf, self.color, (x, y), max(1, round(radius)))


class FloatText:
    def __init__(self, x, y, text, color, font, life=50, speed=1.0, in_world=True):
        """Text that floats up and fades out (like "+25")"""
        self.x, self.y = x, y
        self.image = font.render(text, True, color)
        self.shadow = font.render(text, True, BLACK)
        self.life = self.max_life = life
        self.speed = speed
        self.in_world = in_world  # World text moves with the camera, screen text does not

    def update(self):
        self.y -= self.speed
        self.life -= 1

    def draw(self, surf, cam=0):
        alpha = int(255 * clamp(self.life / 20))
        rect = self.image.get_rect(center=(int(self.x), int(self.y - cam)))
        self.shadow.set_alpha(alpha // 2)
        self.image.set_alpha(alpha)
        surf.blit(self.shadow, rect.move(2, 2))
        surf.blit(self.image, rect)


def draw_hopper(surf, char, cx, bottom, vy=0.0, squash=0.0, facing=1, blink=False, dead=False, t=0):
    """Draw any hopper: a squishy body, plus the extras that make each character special"""
    look = char["look"]
    main, dark, light = char["body"], char["dark"], char["light"]

    # Squash and stretch: tall when flying up, flat right after landing
    stretch = clamp(-vy / 30, -0.12, 0.2)
    w = int(34 * (1 - stretch * 0.6 + squash * 0.3))
    h = int(34 * (1 + stretch - squash * 0.3))
    body = pygame.Rect(0, 0, w, h)
    body.midbottom = (round(cx), round(bottom))
    bx = body.centerx
    back = -facing  # Tails, capes and headbands hang behind the hopper
    sway = math.sin(t * 0.2) * 2 + clamp(vy, -8, 8) * 0.5
    eye_y = int(body.top + h * 0.35)
    ink = (225, 240, 255) if look == "robo" else BLACK

    # Things behind the body
    if look == "king":
        pygame.draw.polygon(surf, (215, 55, 70), [
            (bx - 11, body.top + 9), (bx + 11, body.top + 9),
            (bx + back * 16 + 10, body.bottom - 3 - sway), (bx + back * 16 - 10, body.bottom - 1 - sway)])
    elif look == "cat":
        base = (bx + back * (w // 2 - 3), body.bottom - 9)
        pygame.draw.lines(surf, dark, False, [
            base, (base[0] + back * 8, base[1] - 4), (base[0] + back * 10, base[1] - 13 - sway)], 4)
    elif look == "ninja":
        knot = (bx + back * (w // 2 - 1), eye_y - 8)
        for k in (0, 5):
            pygame.draw.line(surf, (220, 50, 60), knot, (knot[0] + back * 13, knot[1] + k - sway), 3)

    # Feet
    if look != "ghost":
        foot = (255, 165, 60) if look == "pengu" else dark
        for fx in (-8, 8):
            pygame.draw.ellipse(surf, foot, (bx + fx - 6, body.bottom - 3, 12, 7))

    # Body
    if look == "ghost":
        upper = pygame.Rect(body.x, body.y, w, h - 5)
        pygame.draw.rect(surf, dark, upper.move(0, 3), border_top_left_radius=14, border_top_right_radius=14)
        for i in range(3):  # Wavy bottom edge
            pygame.draw.circle(surf, dark, (body.x + w * (2 * i + 1) // 6, body.bottom - 4), w // 6 + 1)
            pygame.draw.circle(surf, main, (body.x + w * (2 * i + 1) // 6, body.bottom - 6), w // 6 + 1)
        pygame.draw.rect(surf, main, upper, border_top_left_radius=14, border_top_right_radius=14)
    else:
        radius = 6 if look == "robo" else 12
        pygame.draw.rect(surf, dark, body.move(0, 2), border_radius=radius)
        pygame.draw.rect(surf, main, body, border_radius=radius)

    # Belly
    if look == "pengu":
        belly = pygame.Rect(0, 0, max(6, w - 10), max(6, h - 9))
        belly.midbottom = (bx, body.bottom - 2)
        pygame.draw.ellipse(surf, light, belly)
    elif look == "robo":
        panel = pygame.Rect(0, 0, max(8, w - 16), 7)
        panel.midbottom = (bx, body.bottom - 4)
        pygame.draw.rect(surf, dark, panel, border_radius=3)
        for i, lamp in enumerate(((255, 90, 90), (255, 220, 80), (110, 240, 130))):
            lit = (t // 12) % 3 == i
            pygame.draw.circle(surf, lamp if lit else mix(lamp, dark, 0.65),
                               (panel.x + 4 + i * (panel.width - 8) // 2, panel.centery), 2)
        pygame.draw.rect(surf, (30, 35, 60), (body.x + 4, eye_y - 6, w - 8, 12), border_radius=4)  # Visor
    elif look == "ninja":
        pygame.draw.rect(surf, light, (body.x + 3, eye_y - 5, w - 6, 11), border_radius=5)  # Face
        pygame.draw.rect(surf, (220, 50, 60), (body.x + 1, eye_y - 11, w - 2, 5), border_radius=2)  # Headband
    elif look != "ghost":
        belly = pygame.Rect(0, 0, max(4, w - 14), max(4, h // 2 - 2))
        belly.midbottom = (bx, body.bottom - 4)
        pygame.draw.ellipse(surf, light, belly)
    if look not in ("ninja", "ghost"):
        pygame.draw.ellipse(surf, WHITE, (body.left + 5, body.top + 4, 8, 5))  # Shine

    # Eyes
    look_y = int(clamp(vy / 5, -2, 2))
    for ex in (-7, 7):
        eye_x = bx + ex + facing * 2
        if dead:
            pygame.draw.line(surf, ink, (eye_x - 3, eye_y - 3), (eye_x + 3, eye_y + 3), 2)
            pygame.draw.line(surf, ink, (eye_x - 3, eye_y + 3), (eye_x + 3, eye_y - 3), 2)
        elif blink:
            pygame.draw.line(surf, ink, (eye_x - 4, eye_y), (eye_x + 4, eye_y), 2)
        elif look == "robo":
            pygame.draw.rect(surf, (90, 240, 255), (eye_x - 3, eye_y - 3 + look_y, 6, 6), border_radius=1)
        elif look == "alien":
            pygame.draw.ellipse(surf, BLACK, (eye_x - 5, eye_y - 6, 10, 13))
            pygame.draw.circle(surf, WHITE, (eye_x - 1 + facing, eye_y - 2 + look_y), 2)
        elif look == "ghost":
            pygame.draw.ellipse(surf, (40, 40, 70), (eye_x - 3, eye_y - 5 + look_y, 7, 10))
        elif look == "ninja":
            pygame.draw.ellipse(surf, WHITE, (eye_x - 4, eye_y - 3, 8, 7))
            pygame.draw.circle(surf, BLACK, (eye_x + facing * 2, eye_y + look_y // 2), 2)
        else:
            pygame.draw.circle(surf, WHITE, (eye_x, eye_y), 5)
            pygame.draw.circle(surf, BLACK, (eye_x + facing * 2, eye_y + look_y), 3)

    # Mouth: "O" when flying fast, smile otherwise
    mouth_x = bx + facing * 2
    if look == "pengu":
        pygame.draw.polygon(surf, (255, 165, 60), [
            (mouth_x - 4, eye_y + 5), (mouth_x + 4, eye_y + 5), (mouth_x + facing * 3, eye_y + 11)])
    elif look == "robo":
        for i in (-3, 0, 3):
            pygame.draw.line(surf, dark, (mouth_x + i, eye_y + 9), (mouth_x + i, eye_y + 12), 1)
    elif look == "cat":
        pygame.draw.circle(surf, (255, 130, 150), (mouth_x, eye_y + 6), 2)  # Nose
        for side in (-1, 1):  # Whiskers
            for dy in (-2, 2):
                pygame.draw.line(surf, dark, (mouth_x + side * 5, eye_y + 7), (mouth_x + side * 13, eye_y + 7 + dy), 1)
    elif look == "ghost":
        pygame.draw.circle(surf, (40, 40, 70), (mouth_x, eye_y + 10), 3 if vy >= -13 else 4)
    elif look != "ninja":
        if dead or vy < -13:
            pygame.draw.circle(surf, dark, (mouth_x, eye_y + 9), 3)
        else:
            pygame.draw.arc(surf, dark, (mouth_x - 5, eye_y + 3, 10, 8), math.pi * 1.1, math.pi * 1.9, 2)
    if look in ("blob", "cat", "king", "pengu"):  # Blush cheeks
        for side in (-12, 12):
            pygame.draw.circle(surf, (255, 150, 150), (bx + side, eye_y + 7), 2)

    # Things on top of the head
    if look == "cat":
        for side in (-1, 1):
            pygame.draw.polygon(surf, main, [
                (bx + side * 14, body.top + 7), (bx + side * 12, body.top - 8), (bx + side * 3, body.top + 1)])
            pygame.draw.polygon(surf, (255, 170, 180), [
                (bx + side * 11, body.top + 2), (bx + side * 11, body.top - 4), (bx + side * 6, body.top + 1)])
    elif look == "robo":
        pygame.draw.line(surf, dark, (bx, body.top), (bx, body.top - 8), 2)
        pygame.draw.circle(surf, (255, 80, 80) if (t // 20) % 2 else (255, 220, 90), (bx, body.top - 9), 3)
    elif look == "king":
        y0 = body.top + 1
        crown = [(bx - 10, y0), (bx - 12, y0 - 10), (bx - 5, y0 - 5), (bx, y0 - 12),
                 (bx + 5, y0 - 5), (bx + 12, y0 - 10), (bx + 10, y0)]
        pygame.draw.polygon(surf, COIN, crown)
        pygame.draw.polygon(surf, COIN_DARK, crown, 1)
        pygame.draw.circle(surf, (230, 60, 80), (bx, y0 - 4), 2)
    elif look == "alien":
        for side in (-1, 1):
            tip = (bx + side * 11, int(body.top - 9 + math.sin(t * 0.15 + side) * 1.5))
            pygame.draw.line(surf, dark, (bx + side * 6, body.top + 1), tip, 2)
            pygame.draw.circle(surf, light, tip, 3)


class Racer:
    W = 34
    H = 34

    def __init__(self, x, y, char, name="You", brain=None, team=0, tag=WHITE):
        """
        A hopper: you, or a computer player when it has a brain \n
        char: one of CHARACTERS (look and perks) \n
        """
        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0  # Sideways speed (smooth speed up / slow down)
        self.vy = 0.0  # Vertical speed
        self.char = char
        self.name = name
        self.brain = brain  # BotBrain for computer players, None for the human
        self.team = team
        self.tag = tag  # Color of the name tag
        self.tier = 0  # Rank badge shown on the "versus" screen
        self.final = 0  # Height when the match ended
        self.facing = 1  # 1 = looking right, -1 = looking left
        self.squash = 0.0  # Squish amount right after landing
        self.blink = 0
        self.blink_timer = random.randint(90, 200)
        self.t = random.randint(0, 100)
        self.trail = []  # Glow trail after a spring jump
        self.cam = 0  # Top of this hopper's own screen. It only moves up, like a camera
        self.dead = False
        self.respawn_t = 0  # Frames until it comes back (matches only)
        self.invuln = 0  # Frames of blinking safety after a hit or respawn
        self.finished = False
        self.finish_t = 0
        self.gone = False  # Left the match after finishing
        self.coins = 0.0  # Coins collected this run
        self.emote = ""
        self.emote_t = 0
        self.chat_wait = 0
        self.was_ahead = False
        # Perks from the character
        self.speed = char.get("speed", 1.0)
        self.jump = char.get("jump", 1.0)
        self.grav = char.get("gravity", 1.0)
        self.magnet = char.get("magnet", 0)
        self.coin_mult = char.get("coin", 1.0)
        self.shield = char.get("shield", 0)
        self.jet_t = 0  # Frames of jetpack left
        self.magnet_t = 0  # Frames of magnet power-up left

    @property
    def rect(self):
        return pygame.Rect(round(self.x), round(self.y), self.W, self.H)

    @property
    def cx(self):
        return self.x + self.W / 2

    @property
    def cy(self):
        return self.y + self.H / 2

    @property
    def height(self):
        """Climbed height in meters"""
        return int(-self.cam // 10)

    def say(self, text):
        if self.chat_wait <= 0:
            self.emote = text
            self.emote_t = 100
            self.chat_wait = 240

    def steer(self, direction):
        """direction: -1 left, 0 none, 1 right"""
        if direction:
            self.vx += direction * MOVE_ACCEL * self.speed
            self.facing = direction
        self.vx *= FRICTION
        self.vx = clamp(self.vx, -7 * self.speed, 7 * self.speed)

    def update(self, platforms):
        """
        Move the hopper and return the platform it landed on (or None) \n
        The whole path since last frame is checked, so fast falls never skip a platform \n
        """
        self.t += 1
        # Sideways move with screen wrap
        self.x += self.vx + wind_now
        if self.x + self.W < 0:
            self.x = BG_X
        elif self.x > BG_X:
            self.x = -self.W

        prev_bottom = self.y + self.H
        if self.jet_t > 0:
            self.jet_t -= 1
            self.vy = lerp(self.vy, JET_SPEED, 0.15)
        else:
            self.vy = min(self.vy + GRAVITY * self.grav * gravity_scale, 16)
        self.y += self.vy

        # Animations and timers
        self.squash = max(0.0, self.squash - 0.08)
        self.blink_timer -= 1
        if self.blink_timer <= 0:
            self.blink = 8
            self.blink_timer = random.randint(120, 260)
        self.blink = max(0, self.blink - 1)
        self.invuln = max(0, self.invuln - 1)
        self.magnet_t = max(0, self.magnet_t - 1)
        self.emote_t = max(0, self.emote_t - 1)
        self.chat_wait = max(0, self.chat_wait - 1)
        if self.vy < -13:
            self.trail.append((self.cx, self.cy))
            self.trail = self.trail[-8:]
        elif self.trail:
            self.trail.pop(0)

        if self.dead:
            return None
        self.cam = min(self.cam, math.floor(self.y - CAMERA_LINE))
        if self.vy <= 0 or self.jet_t > 0:  # Only land while falling
            return None
        bottom = self.y + self.H
        left, right = self.x + 4, self.x + self.W - 4  # Feet are a bit narrower than the body
        for platform in platforms:
            top = platform.rect.top
            if top < prev_bottom or top > bottom or platform.broken or platform.gone:
                continue
            if right > platform.rect.left and left < platform.rect.right:
                return platform
        return None

    def bounce(self, top, power):
        """Stand on top of something and jump"""
        self.y = top - self.H
        self.vy = power
        self.squash = 1.0

    def draw(self, surf, cam):
        if self.gone or self.respawn_t > 0:
            return
        cx, bottom = self.cx, self.y + self.H - cam
        if bottom < -60 or bottom > BG_Y + 90:
            return
        # Glow trail
        for i, (tx, ty) in enumerate(self.trail):
            pygame.draw.circle(surf, mix(self.char["light"], WHITE, 0.4), (int(tx), int(ty - cam)), int(4 + i * 1.6))

        if self.jet_t > 0:  # Jetpack with a flickering flame
            jx = int(cx - self.facing * 15)
            flame = random.randint(10, 20)
            pygame.draw.polygon(surf, (255, 170, 40), [(jx - 5, bottom - 8), (jx + 5, bottom - 8), (jx, bottom - 8 + flame)])
            pygame.draw.polygon(surf, (255, 240, 150), [(jx - 3, bottom - 8), (jx + 3, bottom - 8), (jx, bottom - 8 + flame * 0.6)])
            add_glow(surf, jx, bottom, 24, (100, 55, 10))
            pygame.draw.rect(surf, (200, 205, 220), (jx - 5, bottom - 28, 10, 20), border_radius=4)
            pygame.draw.rect(surf, (230, 70, 70), (jx - 5, bottom - 28, 10, 6), border_radius=3)

        if not (self.invuln > 0 and (self.t // 3) % 2 == 0):  # Blink while safe
            draw_hopper(surf, self.char, cx, bottom, self.vy, self.squash, self.facing, self.blink > 0, self.dead, self.t)

        if self.shield > 0 and not self.dead:  # Bubble shield
            center = (int(cx), int(bottom - self.H / 2))
            wobble = int(math.sin(self.t * 0.1) * 1.5)
            add_glow(surf, center[0], center[1], 34, (10, 35, 50))
            pygame.draw.circle(surf, (150, 230, 255), center, 25 + wobble, 2)
            if self.shield > 1:
                pygame.draw.circle(surf, (150, 230, 255), center, 29 + wobble, 1)
            pygame.draw.arc(surf, WHITE, (center[0] - 20, center[1] - 20, 40, 40), 1.9, 2.8, 2)

    def draw_tag(self, surf, cam):
        """Name tag and chat bubble above the head"""
        if self.gone or self.respawn_t > 0:
            return
        top = self.y - cam
        if top < -20 or top > BG_Y:
            return
        cx = int(clamp(self.cx, 24, BG_X - 24))
        if self.brain:
            draw_text(surf, self.name, font_tiny, (cx, top - 13), self.tag)
        else:
            pygame.draw.polygon(surf, INK, [(cx - 7, top - 19), (cx + 7, top - 19), (cx, top - 8)])
            pygame.draw.polygon(surf, COIN_LIGHT, [(cx - 5, top - 18), (cx + 5, top - 18), (cx, top - 10)])
        if self.emote_t > 0:
            img = text_image(self.emote, font_tiny, INK)
            box = img.get_rect(center=(cx, top - 36)).inflate(14, 8)
            box.clamp_ip(pygame.Rect(2, 2, BG_X - 4, BG_Y))
            pygame.draw.rect(surf, WHITE, box, border_radius=8)
            pygame.draw.polygon(surf, WHITE, [(cx - 4, box.bottom - 1), (cx + 4, box.bottom - 1), (cx, box.bottom + 5)])
            surf.blit(img, img.get_rect(center=box.center))


class Platform:
    def __init__(self, x, y, kind="normal", width=PLATFORM_W, zone=0):
        """
        Initialize the platform  \n
        kind: "normal", "moving", "break" (no bounce) or "cloud" (one bounce only)  \n
        zone: decides the colors of a normal platform  \n
        """
        self.rect = pygame.Rect(int(x), int(y), width, PLATFORM_H)
        self.x = float(x)  # Exact horizontal position for smooth moving
        self.kind = kind
        self.zone = zone
        self.broken = False
        self.gone = False  # Clouds vanish after one bounce
        self.break_t = 0  # Frames since breaking
        self.bump = 0.0  # Dips down a little when someone lands on it
        self.direction = random.choice([-1, 1])
        self.speed = random.uniform(1.0, 2.2)
        self.has_spring = False
        self.spring_x = 0
        self.spring_t = 0  # Frames the spring stays popped up
        self.tufts = [random.randint(4, width - 4) for _ in range(max(2, width // 22))]

    def add_spring(self):
        self.has_spring = True
        self.spring_x = random.randint(8, max(8, self.rect.width - 24))

    def spring_rect(self):
        return pygame.Rect(self.rect.x + self.spring_x, self.rect.top - 12, 16, 12)

    def update(self):
        if self.kind == "moving" and not self.broken:
            self.x += self.direction * self.speed
            if self.x <= 0 or self.x + self.rect.width >= BG_X:
                self.direction *= -1  # Turn around at the walls
                self.x = clamp(self.x, 0, BG_X - self.rect.width)
            self.rect.x = round(self.x)
        if self.broken:
            self.break_t += 1
            self.rect.y += 2 + int(self.break_t * 0.3)  # Pieces fall faster and faster
        self.spring_t = max(0, self.spring_t - 1)
        self.bump *= 0.75

    def draw(self, surf, cam):
        r = self.rect.move(0, -cam + round(self.bump))
        if self.kind == "normal":
            _, _, grass, grass_light, dirt, dirt_dark = ZONES[self.zone]
            if self.zone == 2:  # Icicles
                for tx in self.tufts:
                    pygame.draw.polygon(surf, (190, 225, 255), [(r.x + tx - 3, r.bottom), (r.x + tx + 3, r.bottom), (r.x + tx, r.bottom + 8)])
            elif self.zone == 3:  # Star platforms glow
                add_glow(surf, r.centerx, r.centery, 30, (12, 45, 40))
            pygame.draw.rect(surf, dirt_dark, r.move(0, 4), border_radius=6)
            pygame.draw.rect(surf, dirt, r, border_radius=6)
            pygame.draw.line(surf, dirt_dark, (r.x + 10, r.y + 8), (r.x + 14, r.y + 8), 2)
            pygame.draw.line(surf, dirt_dark, (r.right - 18, r.y + 9), (r.right - 13, r.y + 9), 2)
            pygame.draw.rect(surf, grass, (r.x - 1, r.y - 3, r.width + 2, 8), border_radius=4)
            pygame.draw.line(surf, grass_light, (r.x + 4, r.y - 2), (r.right - 5, r.y - 2), 2)
            for tx in self.tufts:
                pygame.draw.line(surf, grass, (r.x + tx, r.y - 2), (r.x + tx - 2, r.y - 6), 2)
                pygame.draw.line(surf, grass, (r.x + tx, r.y - 2), (r.x + tx + 2, r.y - 5), 2)
        elif self.kind == "moving":
            pygame.draw.rect(surf, METAL_DARK, r.move(0, 4), border_radius=6)
            pygame.draw.rect(surf, METAL, r, border_radius=6)
            pygame.draw.line(surf, METAL_LIGHT, (r.x + 5, r.y + 2), (r.right - 6, r.y + 2), 2)
            for rx in (r.x + 6, r.right - 7):
                pygame.draw.circle(surf, METAL_DARK, (rx, r.centery + 1), 2)
            # Little arrows that show it slides
            for side in (-1, 1):
                ax = r.centerx + side * 8
                pygame.draw.lines(surf, METAL_LIGHT, False,
                                  [(ax - side * 3, r.centery - 2), (ax, r.centery + 1), (ax - side * 3, r.centery + 4)], 2)
        elif self.kind == "cloud":
            for color, dy in (((200, 218, 245), 4), (WHITE, 0)):
                for i, rad in enumerate((8, 11, 10, 8)):
                    pygame.draw.circle(surf, color, (r.x + 8 + i * (r.width - 16) // 3, r.y + 6 + dy - (rad - 8)), rad)
        elif not self.broken:
            pygame.draw.rect(surf, WOOD_DARK, r.move(0, 3), border_radius=4)
            pygame.draw.rect(surf, WOOD, r, border_radius=4)
            for i in (1, 2):
                sx = r.x + r.width * i // 3
                pygame.draw.line(surf, WOOD_DARK, (sx, r.top + 2), (sx, r.bottom - 2), 2)
            pygame.draw.lines(surf, WOOD_DARK, False,
                              [(r.centerx - 6, r.top), (r.centerx - 2, r.centery), (r.centerx + 3, r.top + 3), (r.centerx + 6, r.bottom)], 2)
        else:
            # Two halves flying apart and spinning
            half = r.width / 2
            t = self.break_t
            for side in (-1, 1):
                cx = r.centerx + side * (half / 2 + t * 0.8)
                points = rotated_rect_points(cx, r.centery, half - 2, PLATFORM_H, side * t * 0.07)
                pygame.draw.polygon(surf, WOOD, points)
                pygame.draw.polygon(surf, WOOD_DARK, points, 2)

        if self.has_spring:
            sx = r.x + self.spring_x
            height = 20 if self.spring_t > 0 else 11
            top = r.top - height
            coil = []
            for i in range(6):
                coil.append((sx + (3 if i % 2 == 0 else 13), r.top - i * height / 5))
            pygame.draw.lines(surf, (170, 170, 185), False, coil, 2)
            pygame.draw.rect(surf, SPRING_COLOR, (sx - 2, top - 3, 20, 5), border_radius=2)
            pygame.draw.line(surf, WHITE, (sx, top - 2), (sx + 8, top - 2), 1)


class Coin:
    def __init__(self, x, y, fall=0.0):
        """A spinning coin. Coins from a Coin Rain fall down"""
        self.x, self.y = x, y
        self.fall = fall
        self.t = random.uniform(0, 6)
        self.taken = False

    @property
    def rect(self):
        return pygame.Rect(self.x - 11, self.y - 11, 22, 22)

    def update(self):
        self.t += 0.08
        self.y += self.fall

    def draw(self, surf, cam):
        cy = self.y - cam + math.sin(self.t * 1.5) * 3
        w = max(3, int(abs(math.cos(self.t)) * 18))
        rect = pygame.Rect(0, 0, w, 18)
        rect.center = (int(self.x), int(cy))
        add_glow(surf, self.x, cy, 16, (60, 42, 0))
        pygame.draw.ellipse(surf, COIN_DARK, rect.move(0, 2))
        pygame.draw.ellipse(surf, COIN, rect)
        if w > 8:
            pygame.draw.ellipse(surf, COIN_LIGHT, rect.inflate(-w * 0.55, -9))


class PowerUp:
    def __init__(self, x, y, kind):
        """A floating bubble with a power-up inside: "jet", "shield" or "magnet" """
        self.x, self.y = x, y
        self.kind = kind
        self.t = random.uniform(0, 6)
        self.taken = False

    @property
    def rect(self):
        return pygame.Rect(self.x - 15, self.y - 15, 30, 30)

    def update(self):
        self.t += 0.07

    def draw(self, surf, cam):
        x, y = int(self.x), int(self.y - cam + math.sin(self.t) * 4)
        color = POWER_COLORS[self.kind]
        add_glow(surf, x, y, 30, mix(color, BLACK, 0.6))
        pygame.draw.circle(surf, mix(color, BLACK, 0.5), (x, y + 2), 14)
        pygame.draw.circle(surf, color, (x, y), 14)
        pygame.draw.circle(surf, WHITE, (x, y), 14, 2)
        draw_power_icon(surf, self.kind, x, y)


class Monster:
    W = 40
    H = 30

    def __init__(self, x, y):
        """A flying spiky monster: stomp it from above, don't touch it from the side!"""
        self.x = float(x)
        self.base_y = float(y)
        self.y = float(y)
        self.vx = random.choice([-1, 1]) * random.uniform(0.8, 1.8)
        self.t = random.randint(0, 100)
        self.dead = False
        self.vy = 0.0

    @property
    def rect(self):
        return pygame.Rect(int(self.x) + 5, int(self.y) + 6, self.W - 10, self.H - 8)

    def update(self):
        self.t += 1
        if self.dead:
            self.vy += 0.5
            self.base_y += self.vy
        else:
            self.x += self.vx
            if self.x <= 0 or self.x + self.W >= BG_X:
                self.vx *= -1
                self.x = clamp(self.x, 0, BG_X - self.W)
        self.y = self.base_y + math.sin(self.t * 0.06) * 6

    def draw(self, surf, cam):
        x, y = int(self.x), int(self.y - cam)
        cx = x + self.W // 2
        flap = math.sin(self.t * 0.35) * 6
        # Wings
        for side in (-1, 1):
            wx = cx + side * 18
            pygame.draw.polygon(surf, MONSTER_DARK,
                                [(cx + side * 10, y + 12), (wx + side * 10, y + 4 - flap), (wx + side * 4, y + 20)])
        # Spikes
        for i in range(4):
            sx = x + 8 + i * 8
            pygame.draw.polygon(surf, MONSTER_DARK, [(sx, y + 8), (sx + 4, y - 2), (sx + 8, y + 8)])
        # Body
        pygame.draw.ellipse(surf, MONSTER_DARK, (x, y + 4, self.W, self.H - 2))
        pygame.draw.ellipse(surf, MONSTER, (x + 1, y + 2, self.W - 2, self.H - 4))
        pygame.draw.ellipse(surf, mix(MONSTER, WHITE, 0.35), (x + 7, y + 5, 12, 5))
        # Angry eyes
        for side in (-1, 1):
            ex = cx + side * 8
            if self.dead:
                pygame.draw.line(surf, BLACK, (ex - 3, y + 11), (ex + 3, y + 17), 2)
                pygame.draw.line(surf, BLACK, (ex - 3, y + 17), (ex + 3, y + 11), 2)
            else:
                pygame.draw.circle(surf, WHITE, (ex, y + 14), 5)
                pygame.draw.circle(surf, (200, 0, 30), (ex, y + 15), 2)
                pygame.draw.line(surf, BLACK, (ex - side * 6, y + 7), (ex + side * 3, y + 10), 3)
        # Teeth
        for i in range(4):
            tx = cx - 8 + i * 4
            pygame.draw.polygon(surf, WHITE, [(tx, y + 21), (tx + 4, y + 21), (tx + 2, y + 25)])


class Meteor:
    def __init__(self, x, y):
        """A burning rock from a Meteor Shower. It starts high above the screen, so there is a warning"""
        self.x, self.y = float(x), float(y)
        self.vx = random.uniform(-1.3, 1.3)
        self.vy = 6.5
        self.end_y = y + BG_Y * 2 + 200
        self.t = 0

    @property
    def rect(self):
        return pygame.Rect(self.x - 9, self.y - 9, 18, 18)

    def update(self):
        self.t += 1
        self.x += self.vx
        self.y += self.vy

    def draw(self, surf, cam):
        x, y = int(self.x), int(self.y - cam)
        if y < -30:  # Still above the screen: show a warning where it will come in
            wx = int(clamp(self.x + self.vx * (-y / self.vy), 14, BG_X - 14))
            if (self.t // 5) % 2 == 0:
                pygame.draw.polygon(surf, (255, 70, 60), [(wx, 76), (wx - 10, 94), (wx + 10, 94)])
                draw_text(surf, "!", font_tiny, (wx, 87), WHITE, shadow=False)
            return
        add_glow(surf, x, y, 34, (110, 45, 10))
        for i in range(1, 5):  # Fire tail
            pygame.draw.circle(surf, mix((255, 150, 50), (255, 60, 30), i / 5),
                               (int(x - self.vx * i * 2.5), int(y - self.vy * i * 2.2)), 9 - i * 2)
        pygame.draw.circle(surf, (255, 150, 50), (x, y), 10)
        pygame.draw.circle(surf, (120, 70, 60), (x, y), 7)
        pygame.draw.circle(surf, (85, 45, 40), (x - 2, y + 2), 2)
        pygame.draw.circle(surf, (255, 235, 170), (x + 2, y - 3), 2)


######################電腦玩家######################


class BotBrain:
    def __init__(self, skill):
        """
        The brain of a computer player \n
        skill: 0.0 (clumsy) to 1.0 (expert). Clumsy bots rest more, aim worse and fall for traps \n
        """
        self.skill = clamp(skill, 0.05, 1.0)
        self.band = 0.0  # Small boost when far behind you, small handicap when far ahead
        self.target = None  # The platform it is trying to land on
        self.aim = 0.0  # Where on the platform it aims (0 = the middle)
        self.big_jump = False  # After a spring or jetpack it looks for a new target at the top
        self.last_vy = 0.0
        self.fooled = {}  # Which breaking platforms it thinks are safe
        self.dodges = {}  # Which monsters it noticed in time

    def level(self):
        return clamp(self.skill + self.band, 0.05, 1.0)

    def on_bounce(self, platform):
        """Called after every bounce: forget the old target, or sometimes rest on the same platform"""
        self.target = None
        if len(self.fooled) > 300:
            self.fooled.clear()
            self.dodges.clear()
        resting = random.random() < 0.04 + 0.78 * (1 - self.level()) ** 1.5
        if resting and platform.kind in ("normal", "moving"):
            self.target = platform
            self.aim = 0.0

    def pick(self, bot):
        """Choose the best platform this hopper can still reach from where it is now"""
        level = self.level()
        g = GRAVITY * bot.grav * max(0.3, gravity_scale)
        feet = bot.y + bot.H
        floor = bot.cam + BG_Y - 30  # Lower than this is off its screen
        options, risky, too_far = [], [], []
        for p in platforms:
            top = p.rect.top
            if p.broken or p.gone or top > floor:
                continue
            # Solve "feet + vy*t + g*t*t/2 = top" for the time t when it would land
            inside = bot.vy * bot.vy + 2 * g * (top - feet)
            if inside < 0:
                continue  # Too high to reach
            if bot.vy < 0 and top < feet - bot.vy * bot.vy / (2 * g) + 10:
                continue  # Barely too high
            t = (-bot.vy + math.sqrt(inside)) / g
            if t < 2:
                continue
            # How far it can fly sideways in that time (it needs about 6 frames to speed up)
            reach = 5.5 * bot.speed * max(0.0, t - 6.5) + p.rect.width / 2 + 8
            if abs(wrap_dx(p.rect.centerx - bot.cx - wind_now * t)) > reach:
                if p.kind != "break":
                    too_far.append(p)
                continue
            if p.kind == "break":
                if id(p) not in self.fooled:
                    self.fooled[id(p)] = random.random() > level + 0.15
                if not self.fooled[id(p)]:
                    continue
            danger = False
            if level > 0.4:
                for m in monsters:
                    if not m.dead and -110 < m.y - top < 10 and abs(wrap_dx(m.x + m.W / 2 - p.rect.centerx)) < 60:
                        danger = True
            (risky if danger else options).append(p)
        options = options or risky
        if not options:
            self.target = None
            return
        options.sort(key=lambda p: p.rect.top)  # Highest first
        choice = options[0]
        if len(options) > 1 and random.random() > lerp(0.1, 0.9, level):
            # Plays it safe: the smallest step up instead of the biggest jump
            steps = [p for p in options if p.rect.top < feet - 20]
            choice = steps[-1] if steps else random.choice(options[1:4])
        aim = random.uniform(-1, 1) * (choice.rect.width / 2 - 8) * (1 - level)
        springs = [p for p in options[:3] if p.has_spring]
        if springs and random.random() < level:
            choice = springs[0]
            aim = choice.spring_x + 8 - choice.rect.width / 2
        if random.random() < (1 - level) * 0.1:  # Misjudges the jump
            aim = random.choice((-1, 1)) * (choice.rect.width / 2 + 22)
        higher = [p for p in too_far if p.rect.top < choice.rect.top - 20]
        if higher and choice.rect.top >= feet - 5:
            # Nothing higher is in reach: land on the edge closest to the next platform and try again from there
            goal_p = min(higher, key=lambda p: abs(wrap_dx(p.rect.centerx - choice.rect.centerx)))
            side = 1 if wrap_dx(goal_p.rect.centerx - choice.rect.centerx) > 0 else -1
            aim = side * (choice.rect.width / 2 - 4)
        self.target, self.aim = choice, aim

    def control(self, bot):
        """Return -1, 0 or 1: which way to steer this frame"""
        if bot.vy < -14 or bot.jet_t > 0:
            self.big_jump = True
        at_top = bot.vy >= 0 and self.last_vy < 0
        self.last_vy = bot.vy
        target = self.target
        missed = target is not None and bot.vy > 0 and target.rect.top < bot.y + bot.H - 2
        if target is None or target.broken or target.gone or missed or (at_top and self.big_jump):
            if at_top:
                self.big_jump = False
            self.pick(bot)
            target = self.target

        direction = 0
        if target is not None:
            dx = wrap_dx(target.rect.centerx + self.aim - bot.cx) - bot.vx * 5  # Brake early
            if dx > 5:
                direction = 1
            elif dx < -5:
                direction = -1

        # Steer away from monsters it is flying up into
        if bot.vy < 2 and bot.jet_t == 0 and bot.invuln == 0:
            for m in monsters:
                if m.dead or not -100 < (m.y + m.H / 2) - bot.cy < 25:
                    continue
                mdx = wrap_dx(m.x + m.W / 2 - bot.cx)
                if abs(mdx) < 52:
                    if id(m) not in self.dodges:
                        self.dodges[id(m)] = random.random() < self.level() + 0.1
                    if self.dodges[id(m)]:
                        direction = -1 if mdx > 0 else 1
        return direction


######################背景######################

bg_random = random.Random(11)  # Fixed seed, so the scenery looks the same every time


def make_cloud(scale):
    """Draw a fluffy cloud from overlapping circles, with a soft shadow underneath"""
    w, h = int(120 * scale), int(60 * scale)
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    blobs = []
    for _ in range(7):
        r = random.randint(int(14 * scale), int(24 * scale))
        blobs.append((random.randint(r, w - r), random.randint(max(r, h // 2 - 5), h - r), r))
    for x, y, r in blobs:
        pygame.draw.circle(surf, (200, 216, 245, 235), (x, y + 3), r)
    for x, y, r in blobs:
        pygame.draw.circle(surf, (255, 255, 255, 240), (x, y), r)
    return surf


def make_glow(radius, color):
    """A soft glowing ball (sun / moon)"""
    surf = pygame.Surface((radius * 4, radius * 4), pygame.SRCALPHA)
    center = (radius * 2, radius * 2)
    for r, a in ((radius * 2, 25), (int(radius * 1.5), 50), (int(radius * 1.2), 90)):
        pygame.draw.circle(surf, (*color, a), center, r)
    pygame.draw.circle(surf, (*color, 255), center, radius)
    return surf


def make_vignette():
    """Darker corners make the picture feel deeper"""
    small = pygame.Surface((40, 60), pygame.SRCALPHA)
    for y in range(60):
        for x in range(40):
            d = math.hypot((x - 19.5) / 20, (y - 29.5) / 30)
            small.set_at((x, y), (0, 0, 25, int(105 * clamp((d - 0.8) / 0.6))))
    return pygame.transform.smoothscale(small, (BG_X, BG_Y))


def make_planet():
    surf = pygame.Surface((96, 64), pygame.SRCALPHA)
    pygame.draw.ellipse(surf, (215, 190, 255), (2, 22, 92, 20), 3)  # Back of the ring
    pygame.draw.circle(surf, (225, 140, 110), (48, 32), 21)
    pygame.draw.circle(surf, (245, 180, 135), (43, 27), 14)
    pygame.draw.line(surf, (200, 115, 95), (30, 38), (66, 38), 3)
    pygame.draw.arc(surf, (215, 190, 255), (2, 22, 92, 20), math.pi, math.tau, 3)  # Front of the ring
    return surf


def near_hill(x):
    return math.sin(x * 0.02 + 2) * 18 + math.sin(x * 0.055) * 8


clouds = []
for i in range(8):
    depth = random.uniform(0.2, 0.5)  # Far clouds move slower
    clouds.append({
        "x": random.uniform(-60, BG_X),
        "y": random.uniform(0, BG_Y + 200),
        "speed": depth * random.uniform(0.3, 0.7),
        "depth": depth,
        "surf": make_cloud(depth * 2),
    })

stars = [[random.uniform(0, BG_X), random.uniform(0, BG_Y), random.choice((1, 1, 2)), random.uniform(0, 6)] for _ in range(90)]
shooting = []  # Shooting stars: [x, y, frames left]
sun = make_glow(26, (255, 240, 170))
moon = make_glow(20, (235, 235, 215))
pygame.draw.circle(moon, (200, 200, 185), (36, 34), 4)
pygame.draw.circle(moon, (200, 200, 185), (46, 44), 3)
pygame.draw.circle(moon, (200, 200, 185), (38, 47), 2)
planet = make_planet()
vignette = make_vignette()
aurora_layer = pygame.Surface((BG_X, 260), pygame.SRCALPHA)
dim = pygame.Surface((BG_X, BG_Y), pygame.SRCALPHA)
dim.fill((8, 10, 30, 150))
flash_layer = pygame.Surface((BG_X, BG_Y))
flash_layer.fill(WHITE)

mountains = []  # (x, height): tall peaks and low valleys take turns
mx, tall = -30, True
while mx < BG_X + 60:
    mountains.append((mx, bg_random.uniform(70, 125) if tall else bg_random.uniform(20, 45)))
    mx += bg_random.randint(28, 46)
    tall = not tall
far_hills = [(x, math.sin(x * 0.015) * 25 + math.sin(x * 0.04 + 1) * 10) for x in range(0, BG_X + 21, 20)]
near_hills = [(x, near_hill(x)) for x in range(0, BG_X + 21, 20)]
trees = [(x + bg_random.randint(-8, 8), bg_random.randint(11, 19)) for x in range(14, BG_X, 36)]


def draw_background(sky_m, scroll):
    """Sky that changes with height, sun and moon, stars, mountains, hills and clouds"""
    top, bottom = sky_colors(sky_m)
    gradient = pygame.Surface((1, 2), 0, 32)
    gradient.set_at((0, 0), top)
    gradient.set_at((0, 1), bottom)
    world.blit(pygame.transform.smoothscale(gradient, (BG_X, BG_Y)), (0, 0))

    # Stars fade in at night and twinkle
    star_alpha = clamp((sky_m - 1300) / 900)
    if star_alpha > 0:
        for s in stars:
            y = (s[1] + scroll * 0.05) % BG_Y
            twinkle = 0.6 + 0.4 * math.sin(ticks * 0.05 + s[3])
            bg = mix(top, bottom, y / BG_Y)
            pygame.draw.circle(world, mix(bg, WHITE, star_alpha * twinkle), (int(s[0]), int(y)), s[2])
        if random.random() < 0.006 * star_alpha:
            shooting.append([random.uniform(40, BG_X), random.uniform(20, 250), 26])
        for s in shooting:
            s[0] -= 7
            s[1] += 3.5
            s[2] -= 1
            pygame.draw.line(world, mix(top, WHITE, s[2] / 26), (s[0], s[1]), (s[0] + 28, s[1] - 14), 2)
        shooting[:] = [s for s in shooting if s[2] > 0]

    # Northern lights wave across the night sky
    aurora_alpha = clamp((sky_m - 1500) / 500)
    if aurora_alpha > 0:
        aurora_layer.fill((0, 0, 0, 0))
        for i, color in enumerate(((80, 255, 170), (120, 180, 255), (200, 120, 255))):
            upper, lower = [], []
            for x in range(0, BG_X + 41, 40):
                y = 60 + i * 36 + math.sin(x * 0.012 + ticks * 0.012 + i * 2) * 22
                upper.append((x, y))
                lower.append((x, y + 46 + math.sin(x * 0.02 + ticks * 0.02 + i) * 14))
            pygame.draw.polygon(aurora_layer, (*color, int(40 * aurora_alpha)), upper + lower[::-1])
        world.blit(aurora_layer, (0, 0))

    # Sun (sets as you climb), moon (rises at night) and a ringed planet in space
    sun_alpha = 1 - clamp((sky_m - 900) / 700)
    if sun_alpha > 0:
        sun.set_alpha(int(255 * sun_alpha))
        center = (310, 110 + min(scroll, 20000) * 0.02)
        add_glow(world, center[0], center[1], 90, mix(BLACK, (70, 60, 30), sun_alpha))
        world.blit(sun, sun.get_rect(center=center))
    moon_alpha = clamp((sky_m - 1600) / 500)
    if moon_alpha > 0:
        moon.set_alpha(int(255 * moon_alpha))
        world.blit(moon, moon.get_rect(center=(90, 120)))
    planet_alpha = clamp((sky_m - 2000) / 500)
    if planet_alpha > 0:
        planet.set_alpha(int(255 * planet_alpha))
        world.blit(planet, planet.get_rect(center=(300, 330 + math.sin(ticks * 0.01) * 6)))

    # Mountains with snowy tops, far away
    y0 = BG_Y - 175 + scroll * 0.08
    if y0 - 130 < BG_Y:
        rock = mix(bottom, (95, 110, 150), 0.55)
        pygame.draw.polygon(world, rock, [(x, y0 - h) for x, h in mountains] + [(BG_X + 60, BG_Y), (-30, BG_Y)])
        for x, h in mountains:
            if h > 60:
                pygame.draw.polygon(world, mix(rock, WHITE, 0.75), [(x, y0 - h), (x - 8, y0 - h + 17), (x + 8, y0 - h + 17)])

    # Hills at the start, they slide away as you climb
    for shape, base, speed, color in (
        (far_hills, BG_Y - 150, 0.15, mix(bottom, (70, 130, 120), 0.6)),
        (near_hills, BG_Y - 85, 0.3, mix(bottom, (70, 165, 85), 0.85)),
    ):
        y0 = base + scroll * speed
        if y0 - 40 < BG_Y:
            points = [(x, y0 + dy) for x, dy in shape] + [(BG_X, BG_Y), (0, BG_Y)]
            pygame.draw.polygon(world, color, points)
            if shape is near_hills:  # Little pine trees on the closest hills
                leaf = mix(color, (20, 80, 50), 0.55)
                for x, size in trees:
                    ty = y0 + near_hill(x) + 3
                    pygame.draw.rect(world, mix(color, (80, 50, 30), 0.6), (x - 1, ty - 4, 3, 5))
                    for k in (0, 1):
                        half = size * (0.6 - k * 0.18)
                        pygame.draw.polygon(world, leaf, [
                            (x - half, ty - 3 - k * size * 0.45), (x + half, ty - 3 - k * size * 0.45),
                            (x, ty - 3 - size * (0.75 + k * 0.45))])

    # Clouds drift sideways and fade out high up
    cloud_alpha = 1 - clamp((sky_m - 1300) / 800)
    for c in clouds:
        c["x"] += c["speed"]
        if c["x"] > BG_X + 20:
            c["x"] = -c["surf"].get_width() - 20
        if cloud_alpha > 0:
            y = (c["y"] + scroll * c["depth"]) % (BG_Y + 200) - 100
            c["surf"].set_alpha(int(220 * cloud_alpha))
            world.blit(c["surf"], (c["x"], y))


######################遊戲流程函式######################


def set_state(new_state):
    global state, state_t
    state = new_state
    state_t = 0


def is_human(r):
    """True for the real player (not for bots, and not for the game behind the menu)"""
    return r is me and r.brain is None


def on_screen(y, margin=40):
    return me.cam - margin <= y <= me.cam + BG_Y + margin


def score():
    return me.height + bonus


def team_totals():
    """Climbed meters of each team added together (2 v 2)"""
    totals = [0, 0]
    for r in racers:
        totals[min(r.team, 1)] += r.height
    return totals


def standings():
    """Everyone from first to last: finishers first, then by height"""
    rest = sorted((r for r in racers if not r.finished), key=lambda r: -r.height)
    return finish_order + rest


def casual_skill(key):
    """Bots in 1 v 1 and 2 v 2 get better when you keep winning, easier when you keep losing"""
    stats = save["stats"]
    return clamp(0.35 + 0.05 * (stats.get("wins_" + key, 0) - stats.get("losses_" + key, 0)), 0.1, 0.9)


def burst(x, y, colors, count, speed=3.0, size=4, life=30, gravity=0.15, up=False, glow=False):
    """Spray particles from a point"""
    if not on_screen(y) or len(particles) > 500:
        return
    for _ in range(count):
        angle = random.uniform(math.pi, math.tau) if up else random.uniform(0, math.tau)
        sp = random.uniform(0.4, 1.0) * speed
        particles.append(Particle(x, y, math.cos(angle) * sp, math.sin(angle) * sp,
                                  random.choice(colors), random.uniform(size * 0.6, size),
                                  random.randint(life // 2, life), gravity, glow))


def add_platform_row():
    """
    Add one solid platform above the highest one (plus maybe coins, traps, power-ups, monsters) \n
    Gaps always stay smaller than the max jump height, so the game is always possible \n
    """
    global top_y, rows_since_monster, row_cx
    row_m = max(0, -(top_y + 50)) / 10  # Height of this row in meters
    level = clamp((row_m + diff_bonus) / 2500)  # 0.0 at the start, grows to 1.0 at 2500 m
    zone = zone_of(row_m * zone_scale)
    gap = random.randint(int(55 + level * 25), int(80 + level * 45))
    top_y -= gap
    rows_since_monster += 1

    width = int(PLATFORM_W * (1 - 0.2 * level))  # Platforms get smaller as you climb
    kind = "moving" if random.random() < 0.08 + 0.35 * level else "normal"
    # Never farther than one jump sideways from the row below (the screen wraps around)
    row_cx = (row_cx + random.uniform(-135, 135)) % BG_X
    platform = Platform(clamp(row_cx - width / 2, 0, BG_X - width), top_y, kind, width, zone)
    spring_chance = 0.5 if sky_event and sky_event["id"] == "spring" else 0.07 * daily("springs")
    if kind == "normal" and random.random() < spring_chance:
        platform.add_spring()
    platforms.append(platform)

    # A power-up bubble, or coins: one above the platform, or sometimes a little arc of three
    roll = random.random()
    cx = clamp(platform.rect.centerx, 30, BG_X - 30)
    if random.random() < 0.035 * (1 + 0.25 * upgrade_level("luck")) * daily("power"):
        powerups.append(PowerUp(cx, top_y - 36, random.choice(("jet", "shield", "magnet"))))
    elif roll < 0.15:
        coins.append(Coin(cx, top_y - 30))
    elif roll < 0.21:
        for i in (-1, 0, 1):
            coins.append(Coin(cx + i * 24, top_y - 32 - (1 - abs(i)) * 10))

    # Between the rows: a breaking platform as a trap, or a one-time cloud as a helper
    roll = random.random()
    if roll < 0.08 + 0.3 * level:
        platforms.append(Platform(random.randint(0, BG_X - PLATFORM_W), top_y + gap // 2, "break", PLATFORM_W, zone))
    elif roll > 0.9:
        platforms.append(Platform(random.randint(0, BG_X - 56), top_y + gap // 2, "cloud", 56, zone))

    # Monsters appear after 250 m
    if row_m + diff_bonus > 250 and rows_since_monster > 6 and random.random() < 0.05 + 0.08 * level:
        monsters.append(Monster(random.randint(0, BG_X - Monster.W), top_y + gap // 2 - 20))
        rows_since_monster = 0


def make_bot(skill, team, tag, taken):
    """A computer player with a random hopper and a name nobody else has"""
    name = random.choice([n for n in BOT_NAMES if n not in taken])
    taken.append(name)
    bot = Racer(0, BG_Y - 140, random.choice(CHARACTERS), name, BotBrain(skill + random.uniform(-0.07, 0.07)), team, tag)
    bot.tier = int(clamp((bot.brain.skill - 0.25) * 9, 0, 6))  # Rank badge shown before the match
    return bot


def start_game(new_mode):
    """Build a fresh world for a mode and put every hopper on the ground"""
    global mode, racers, me, platforms, coins, monsters, powerups, meteors, particles, popups
    global top_y, bonus, shake, flash, next_milestone, rows_since_monster, new_best
    global goal, zone_scale, diff_bonus, match_t, finish_order, result
    global sky_event, event_wait, wind_now, gravity_scale, zone_index, row_cx
    mode = new_mode
    platforms, coins, monsters, powerups, meteors, particles, popups = [], [], [], [], [], [], []
    row_cx = BG_X / 2
    bonus = 0
    shake = flash = 0.0
    next_milestone = 500
    rows_since_monster = 0
    new_best = False
    goal, zone_scale, diff_bonus = 0, 1.0, 0
    match_t = 0
    finish_order = []
    result = None
    sky_event = None
    event_wait = int(random.randint(700, 1100) / daily("events"))
    wind_now, gravity_scale = 0.0, 1.0
    zone_index = 0

    names = []
    if mode == "attract":  # Three bots play behind the menu
        racers = [make_bot(0.6 if i == 0 else 0.8, i, FFA_TAGS[i], names) for i in range(3)]
        me = racers[0]
    else:
        me = Racer(0, BG_Y - 140, my_character(), "You", None, 0, COIN_LIGHT)
        me.tier = rank_tier(save["rp"])
        me.shield += upgrade_level("shield")
        me.magnet += upgrade_level("magnet") * 22
        me.coin_mult *= (1 + 0.1 * upgrade_level("wallet")) * daily("coin")
        racers = [me]
        if mode == "1v1":
            goal = 500
            racers.append(make_bot(casual_skill("1v1"), 1, TEAM_RED, names))
        elif mode == "2v2":
            goal = 1000  # Both teammates added together
            skill = casual_skill("2v2")
            racers.append(make_bot(skill, 0, TEAM_BLUE, names))
            racers.append(make_bot(skill, 1, TEAM_RED, names))
            racers.append(make_bot(skill, 1, TEAM_RED, names))
        elif mode == "ranked":
            tier = rank_tier(save["rp"])
            goal = 500 + tier * 50
            skill = clamp(0.3 + 0.6 * save["rp"] / 1400, 0.3, 0.92)  # Higher rank = smarter bots
            for i in range(3):
                bot = make_bot(skill, i + 1, FFA_TAGS[i], names)
                bot.tier = int(clamp(tier + random.choice((-1, 0, 0, 1)), 0, 6))
                racers.append(bot)
        if mode != "solo":
            diff_bonus = 250 + (rank_tier(save["rp"]) * 100 if mode == "ranked" else 0)
            zone_scale = 2000 / (goal / 2 if mode == "2v2" else goal)  # All four zones fit in one match
    for i, r in enumerate(racers):  # Line up side by side
        r.x = BG_X * (i + 1) / (len(racers) + 1) - Racer.W / 2

    # Wide grassy ground so the first jump is easy
    ground = Platform(0, BG_Y - 30, "normal", BG_X, 0)
    platforms.append(ground)
    top_y = ground.rect.top
    while top_y > -110:  # Fill the screen with platforms
        add_platform_row()


def begin(new_mode):
    """Start playing a mode from the menu"""
    global match_tip
    match_tip = random.randrange(len(TIPS))
    start_game(new_mode)
    set_state("play" if new_mode == "solo" else "intro")


def go_menu():
    """Back to the main menu (coins from an unfinished Solo run are kept)"""
    if mode == "solo" and state in ("play", "paused", "dying"):
        finish_solo()
    refresh_daily()
    start_game("attract")
    set_state("menu")


def quit_game():
    if mode == "solo" and state in ("play", "paused", "dying"):
        finish_solo()
    save_game()
    pygame.quit()
    sys.exit()


def respawn(r):
    """Matches only: put a fallen hopper back on a solid platform near the bottom of its screen"""
    low, high = r.cam + CAMERA_LINE + 70, r.cam + BG_Y - 70
    spots = [p for p in platforms if p.kind in ("normal", "moving") and not p.gone and low <= p.rect.top <= high]
    if spots:
        spot = min(spots, key=lambda p: p.rect.top)
    else:
        spot = Platform(random.randint(40, BG_X - 40 - PLATFORM_W), r.cam + BG_Y - 170, "normal", PLATFORM_W,
                        zone_of(r.height * zone_scale))
        platforms.append(spot)
    r.x = spot.rect.centerx - r.W / 2
    r.vx = 0.0
    r.bounce(spot.rect.top, JUMP_POWER * r.jump)
    r.dead = False
    r.invuln = 120
    r.trail = []
    if r.brain:
        r.brain.target = None
    burst(r.cx, r.cy, [WHITE, r.char["light"]], 14, speed=3, size=3, life=25, gravity=0.0, glow=True)


def hurt(r):
    """A monster or meteor hit this hopper. A bubble shield saves it once"""
    global shake
    if r.invuln > 0 or r.jet_t > 0 or r.dead:
        return
    if r.shield > 0:
        r.shield -= 1
        r.invuln = 90
        r.vy = min(r.vy, -7)
        if is_human(r):
            play("pop")
            shake = max(shake, 5)
        burst(r.cx, r.cy, [(150, 230, 255), WHITE], 16, speed=4, size=3, life=25, gravity=0.02, glow=True)
        return
    r.dead = True
    r.vy = -7
    r.vx = 0
    burst(r.cx, r.cy, [r.char["body"], WHITE], 16, speed=4)
    if is_human(r):
        play("hurt")
        shake = 9
        if mode == "solo":
            set_state("dying")
    elif r.brain:
        r.chat_wait = 0
        r.say(random.choice(CHAT_HURT))


def fell(r):
    """This hopper dropped off the bottom of its screen"""
    global shake
    if mode == "solo" and is_human(r):
        game_over()
        return
    if is_human(r):
        play("fall")
        shake = max(shake, 7)
    r.dead = True
    r.respawn_t = 80  # Comes back after a short wait
    r.vx = r.vy = 0.0
    r.jet_t = 0


def land(r, p):
    """A hopper came down on a platform: bounce, spring, break or cloud"""
    global shake
    human = is_human(r)
    top = p.rect.top
    feet = (r.cx, top)
    if state in ("intro", "countdown"):
        r.bounce(top, -8)  # Small hops while waiting for the start
        return
    if p.kind == "break":
        p.broken = True  # Crumbles: no bounce!
        if human:
            play("break")
            shake = max(shake, 4)
        burst(*feet, [WOOD, WOOD_DARK], 14, speed=3, size=4, life=35, gravity=0.3)
        return
    p.bump = 4.0
    spring = p.spring_rect() if p.has_spring else None
    if spring and spring.inflate(16, 0).collidepoint(feet[0], spring.centery):
        r.bounce(top, SPRING_POWER * r.jump)
        p.spring_t = 20
        if human:
            play("spring")
            quest_progress("springs")
        burst(*feet, [SPRING_COLOR, WHITE], 18, speed=4, size=4, life=30, up=True, glow=True)
    else:
        r.bounce(top, JUMP_POWER * r.jump)
        if human:
            play("jump")
        if p.kind == "cloud":
            p.gone = True  # Clouds puff away after one bounce
            burst(p.rect.centerx, top + 6, [WHITE, (215, 228, 245)], 16, speed=2.5, size=6, life=28, gravity=-0.02)
        else:
            dust = ZONES[p.zone][3] if p.kind == "normal" else METAL_LIGHT
            burst(*feet, [dust, WHITE], 6, speed=2, size=3, life=18, gravity=0.05, up=True)
    if r.brain:
        r.brain.on_bounce(p)
    elif autopilot:
        autopilot.on_bounce(p)


def touch_things(r):
    """Coins, power-ups, monsters and meteors that this hopper is touching"""
    global bonus, shake
    human = is_human(r)
    rect = r.rect

    # Coins (a magnet pulls them in first)
    reach = 150 if r.magnet_t > 0 else r.magnet
    for coin in coins:
        dx, dy = r.cx - coin.x, r.cy - coin.y
        if coin.taken or abs(dy) > 160:
            continue
        if reach:
            d = math.hypot(dx, dy)
            if 0 < d < reach:
                coin.x += dx / d * 7
                coin.y += dy / d * 7
        if rect.colliderect(coin.rect):
            coin.taken = True
            r.coins += r.coin_mult
            if human:
                play("coin")
                quest_progress("coins")
                if mode == "solo":
                    bonus += 25
                    popups.append(FloatText(coin.x, coin.y - 10, "+25", COIN_LIGHT, font_small))
            burst(coin.x, coin.y, [COIN, COIN_LIGHT, WHITE], 10, speed=3, size=3, life=25, gravity=0.05, glow=True)

    # Power-ups
    for power in powerups:
        if power.taken or not rect.colliderect(power.rect):
            continue
        power.taken = True
        longer = 1 + 0.2 * upgrade_level("battery") if human else 1
        if power.kind == "jet":
            r.jet_t = int((90 if goal else 150) * longer)  # Shorter in matches, where it is a huge head start
        elif power.kind == "shield":
            r.shield = min(3, r.shield + 1)
        else:
            r.magnet_t = int(600 * longer)
        color = POWER_COLORS[power.kind]
        if human:
            play("power")
            quest_progress("power")
            popups.append(FloatText(BG_X // 2, 200, POWER_NAMES[power.kind], mix(color, WHITE, 0.4), font_mid,
                                    life=70, speed=0.5, in_world=False))
        burst(power.x, power.y, [color, WHITE], 16, speed=4, size=4, life=28, gravity=0.02, glow=True)

    # Monsters: stomp from above (or fly through with a jetpack), or get hit
    for m in monsters:
        if m.dead or not rect.colliderect(m.rect):
            continue
        if r.jet_t > 0 or (r.vy > 0 and rect.bottom - r.vy <= m.rect.top + 12):
            m.dead = True
            m.vy = -3
            if r.jet_t == 0:
                r.bounce(m.rect.top, STOMP_POWER * r.jump)
            if human:
                play("stomp")
                shake = max(shake, 5)
                quest_progress("stomp")
                if mode == "solo":
                    bonus += 100
                    popups.append(FloatText(m.x + m.W / 2, m.y - 10, "+100", (255, 160, 255), font_mid))
            burst(m.x + m.W / 2, m.y + m.H / 2, [MONSTER, MONSTER_DARK, WHITE], 18, speed=4, size=5, life=30)
        else:
            hurt(r)
            if r.dead:
                return

    for meteor in meteors:
        if rect.colliderect(meteor.rect):
            hurt(r)
            if r.dead:
                return


def head_bounces():
    """Hoppers can jump off each other's heads"""
    live = [r for r in racers if not (r.dead or r.gone or r.respawn_t or r.jet_t)]
    for a in live:
        if a.vy <= 1:
            continue
        for b in live:
            if a is b or a.vy <= b.vy or abs(a.x - b.x) > 26:
                continue
            if b.y - 6 <= a.y + a.H <= b.y + 12:
                a.bounce(b.y, JUMP_POWER * a.jump)
                b.squash = 1.0
                if a.brain:
                    a.brain.target = None  # Look for a new platform from up here
                if is_human(a):
                    play("jump")
                burst(a.cx, b.y, [WHITE, a.char["light"]], 8, speed=2.5, size=3, life=18, gravity=0.05, up=True)
                break


def chatter():
    """Bots say something when they pass you, or when you pass them"""
    for r in racers:
        if not r.brain or r.gone or r.dead or r.respawn_t:
            continue
        friend = r.team == me.team
        if r.height > me.height + 15 and not r.was_ahead:
            r.was_ahead = True
            if match_t > 200:
                r.say(random.choice(CHAT_MATE if friend else CHAT_PASS))
        elif r.height < me.height - 15 and r.was_ahead:
            r.was_ahead = False
            r.say(random.choice(CHAT_MATE if friend else CHAT_PASSED))


def start_event(info):
    """Begin a sky event"""
    global sky_event, flash
    sky_event = {"id": info["id"], "name": info["name"], "color": info["color"],
                 "t": info["time"], "max": info["time"], "dir": random.choice((-1, 1))}
    popups.append(FloatText(BG_X // 2, 210, info["name"], info["color"], font_big, life=100, speed=0.4, in_world=False))
    play("event")
    flash = 70
    if info["id"] == "spring":  # Springs pop up on the platforms above you
        for p in platforms:
            if p.kind == "normal" and not p.has_spring and p.rect.width < 200 and p.rect.top < me.y and random.random() < 0.6:
                p.add_spring()


def update_event():
    """Count down to the next sky event and run the one that is active"""
    global sky_event, event_wait, wind_now, gravity_scale
    gravity_goal, wind_goal = 1.0, 0.0
    if sky_event:
        sky_event["t"] -= 1
        kind, t = sky_event["id"], sky_event["t"]
        if kind == "coins" and t % 6 == 0:
            coins.append(Coin(random.randint(20, BG_X - 20), me.cam - 20, random.uniform(2.5, 4.5)))
        elif kind == "moon":
            gravity_goal = 0.6
        elif kind == "wind":
            wind_goal = sky_event["dir"] * 1.5
            if t % 2 == 0:  # Streaks that show the wind
                x = -10 if sky_event["dir"] > 0 else BG_X + 10
                particles.append(Particle(x, me.cam + random.uniform(0, BG_Y), sky_event["dir"] * random.uniform(9, 14), 0,
                                          (235, 245, 255), random.uniform(1.5, 3), 45, 0.0))
        elif kind == "meteor" and t % 34 == 0:
            victim = random.choice([r for r in racers if not r.gone])  # Meteors fall near anyone
            meteors.append(Meteor(random.randint(30, BG_X - 30), victim.cam - 380))
        if t <= 0:
            sky_event = None
            event_wait = int(random.randint(900, 1500) / daily("events"))
    elif state == "play":
        event_wait -= 1
        if event_wait <= 0 and me.height > 40:
            start_event(random.choice(SKY_EVENTS))
    gravity_scale = lerp(gravity_scale, gravity_goal, 0.05)
    wind_now = lerp(wind_now, wind_goal, 0.03)


def check_match():
    """Did somebody win?"""
    if mode == "2v2":
        if max(team_totals()) >= goal:
            end_match()
    else:
        for r in racers:
            if not r.finished and r.height >= goal:
                r.finished = True
                r.finish_t = match_t
                r.jet_t = 10 ** 6  # Flies away to celebrate
                finish_order.append(r)
                burst(r.cx, r.cy, [COIN_LIGHT, WHITE, TEAM_BLUE, TEAM_RED, GOOD], 30, speed=6, size=4, life=50, gravity=0.1)
                if r.brain:
                    r.chat_wait = 0
                    r.say("GG!")
        bots_left = [r for r in racers if r.brain and not r.finished]
        if me.finished or not bots_left or (mode == "1v1" and finish_order):
            end_match()
    if state == "play" and match_t > 60 * 240:  # Nobody made it in 4 minutes: highest hopper wins
        end_match()


def end_match():
    """Work out the result, pay the rewards and move the rank"""
    global result
    stats = save["stats"]
    old_rp = save["rp"]
    rp_change = 0
    totals = team_totals()
    for r in racers:
        r.final = r.height  # Hoppers keep moving while the result shows, so remember the height now
    if mode == "2v2":
        won = totals[0] >= totals[1]
        order = sorted(racers, key=lambda r: (r.team, -r.height))
        place = 1 if won else 2
        title = "VICTORY!" if won else "DEFEAT"
        prize = 50 if won else 12
    else:
        order = standings()
        place = order.index(me) + 1
        if mode == "1v1":
            won = place == 1
            title = "VICTORY!" if won else "DEFEAT"
            prize = 40 if won else 10
        else:
            won = place <= 2  # Top half counts as a win in ranked
            title = f"{ORDINALS[place - 1].upper()} PLACE!"
            prize = RANKED_COINS[place - 1]
            rp_change = RANKED_RP[place - 1]
            if rp_change > 0:
                rp_change = int(rp_change * daily("rp"))
            save["rp"] = max(0, old_rp + rp_change)
            if place == 1:
                stats["firsts_ranked"] = stats.get("firsts_ranked", 0) + 1
    prize = int(prize * daily("reward"))
    collected = int(me.coins)
    save["coins"] += prize + collected
    stats["games_" + mode] = stats.get("games_" + mode, 0) + 1
    key = ("wins_" if won else "losses_") + mode
    stats[key] = stats.get(key, 0) + 1
    result = {
        "title": title, "won": won, "place": place, "order": order, "totals": totals,
        "prize": prize, "collected": collected, "time": match_t,
        "rp_change": save["rp"] - old_rp, "tier_change": rank_tier(save["rp"]) - rank_tier(old_rp),
    }
    quest_progress("matches")
    if won:
        quest_progress("wins")
    quest_progress("climb", me.height)
    save_game()
    play("win" if won else "lose")
    if won:
        for _ in range(3):
            burst(random.randint(60, BG_X - 60), me.cam + random.randint(120, 320),
                  [COIN_LIGHT, WHITE, TEAM_BLUE, TEAM_RED, GOOD], 30, speed=6, size=4, life=60, gravity=0.1)
    set_state("finish")


def finish_solo():
    """End of a Solo run: keep the coins, check the best score and the quests"""
    global new_best
    save["coins"] += int(me.coins)
    if score() > save["high_score"]:
        save["high_score"] = score()
        new_best = True
    quest_progress("height", me.height)
    quest_progress("climb", me.height)
    stats = save["stats"]
    stats["games_solo"] = stats.get("games_solo", 0) + 1
    stats["best_height"] = max(stats.get("best_height", 0), me.height)
    save_game()


def game_over():
    global shake
    finish_solo()
    set_state("over")
    shake = 10
    play("fall")


def play_step(control=True):
    """One frame of gameplay for every hopper"""
    global match_t, next_milestone, zone_index
    if state == "play":
        match_t += 1
    keys = pygame.key.get_pressed()
    band_power = BAND_POWER.get(mode, 0)

    for r in racers:
        if r.gone:
            continue
        if r.respawn_t > 0:
            r.respawn_t -= 1
            if r.respawn_t == 0:
                respawn(r)
            continue
        direction = 0
        if control and not r.dead:
            if r.brain:
                # Bots try a bit harder when they are behind you, and relax when far ahead
                r.brain.band = clamp((me.height - r.height) / 300, -0.3, 0.3) * band_power
                direction = r.brain.control(r)
            elif autopilot:
                direction = autopilot.control(r)
            else:
                direction = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
        r.steer(direction)
        landed = r.update(platforms)
        if landed:
            land(r, landed)
        if not r.dead:
            touch_things(r)
        if r.y > r.cam + BG_Y:  # Fell off the bottom of its own screen
            fell(r)
        if r.finished and r.brain and match_t - r.finish_t > 100:
            r.gone = True
    if state == "over":
        return

    if state not in ("intro", "countdown"):
        head_bounces()

    # Keep building platforms above the highest hopper
    lead = min(r.cam for r in racers if not r.gone)
    while top_y > lead - 110:
        add_platform_row()

    if mode == "attract":
        return
    update_event()
    if len(racers) > 1 and state == "play":
        chatter()
        check_match()

    # Messages: new zone, and every 500 m in Solo
    zone = zone_of(me.height * zone_scale)
    if zone > zone_index:
        zone_index = zone
        popups.append(FloatText(BG_X // 2, 250, ZONES[zone][1], ZONES[zone][3], font_mid, life=110, speed=0.3, in_world=False))
    if mode == "solo" and me.height >= next_milestone:
        popups.append(FloatText(BG_X // 2, 170, f"{next_milestone} m!", COIN_LIGHT, font_big, life=90, speed=0.5, in_world=False))
        play("milestone")
        next_milestone += 500


def update_world():
    """Things that keep moving in every state (platforms, coins, particles...)"""
    global shake, flash, platforms, coins, monsters, powerups, meteors, particles, popups
    for group in (platforms, coins, monsters, powerups, meteors, particles, popups):
        for thing in group:
            thing.update()
    shake *= 0.85
    flash *= 0.88

    # Remove things that are below every hopper's screen (build new lists instead of removing while looping)
    floor = max(r.cam for r in racers if not r.gone) + BG_Y + 80
    platforms = [p for p in platforms if p.rect.top < floor and not p.gone and p.break_t < 90]
    coins = [c for c in coins if c.y < floor and not c.taken]
    monsters = [m for m in monsters if m.base_y < floor]
    powerups = [u for u in powerups if u.y < floor and not u.taken]
    meteors = [m for m in meteors if m.y < m.end_y]
    particles = [p for p in particles if p.life > 0]
    popups = [t for t in popups if t.life > 0]


def update_game():
    """Advance the game by one frame, depending on the state"""
    if state in ("play", "dying", "finish"):
        play_step()
        update_world()
        if state == "finish" and state_t > 120:
            set_state("results")
    elif state == "intro":
        play_step(False)
        update_world()
        if state_t > 190:
            set_state("countdown")
    elif state == "countdown":
        play_step(False)
        update_world()
        if state_t % 45 == 1 and state_t < 135:
            play("beep")
        if state_t >= 135:
            set_state("play")
            play("go")
            popups.append(FloatText(BG_X // 2, 230, "GO!", GOOD, font_title, life=45, speed=0.6, in_world=False))
    elif state in ("menu", "shop", "quests"):
        play_step()  # Bots play behind the menu
        update_world()
    elif state in ("over", "results"):
        update_world()
    for item in toasts:
        item[2] -= 1
    toasts[:] = [item for item in toasts if item[2] > 0]


######################畫面工具######################

mouse = (0, 0)  # Mouse position this frame
click = False  # True on the frame the left mouse button goes down
shop_tab = 0  # 0 = hoppers, 1 = upgrades
shop_msg = ["", WHITE, 0]  # Message at the bottom of the shop: [text, color, frames left]
gloss_cache = {}
preview_layer = pygame.Surface((80, 90), pygame.SRCALPHA)


def ui_button(rect, label, color, font=None, enabled=True, sub=None):
    """Draw a button and return True on the frame it is clicked"""
    global click
    rect = pygame.Rect(rect)
    hover = enabled and rect.collidepoint(mouse)
    base = color if enabled else (95, 95, 110)
    face = rect.move(0, -2) if hover else rect
    pygame.draw.rect(screen, mix(base, BLACK, 0.5), rect.move(0, 4), border_radius=14)
    pygame.draw.rect(screen, mix(base, WHITE, 0.15) if hover else base, face, border_radius=14)
    size = (face.width - 8, max(4, face.height // 2 - 2))
    if size not in gloss_cache:  # Shiny top half
        gloss_cache[size] = pygame.Surface(size, pygame.SRCALPHA)
        pygame.draw.rect(gloss_cache[size], (255, 255, 255, 40), (0, 0, *size), border_radius=10)
    screen.blit(gloss_cache[size], (face.x + 4, face.y + 3))
    pygame.draw.rect(screen, mix(base, WHITE, 0.45), face, 2, border_radius=14)
    text_color = WHITE if enabled else (190, 190, 200)
    if sub:
        draw_text(screen, label, font or font_mid, (face.centerx, face.centery - 9), text_color)
        draw_text(screen, sub, font_tiny, (face.centerx, face.centery + 14), mix(base, WHITE, 0.8), shadow=False)
    else:
        draw_text(screen, label, font or font_mid, face.center, text_color)
    if hover and click:
        click = False
        play("click")
        return True
    return False


def draw_preview(surf, char, cx, bottom, scale=1.0, offset=0):
    """A hopper for the menus: it hops in place"""
    phase = ((ticks + offset) % 54) / 54
    hop = math.sin(phase * math.pi) * 12
    vy = -math.cos(phase * math.pi) * 6
    squash = clamp(1 - phase * 6)
    blink = (ticks + offset * 7) % 170 < 8
    if scale == 1.0:
        draw_hopper(surf, char, cx, bottom - hop, vy, squash, 1, blink, False, ticks)
        return
    preview_layer.fill((0, 0, 0, 0))
    draw_hopper(preview_layer, char, 40, 84 - hop, vy, squash, 1, blink, False, ticks)
    big = pygame.transform.smoothscale(preview_layer, (int(80 * scale), int(90 * scale)))
    surf.blit(big, (int(cx - 40 * scale), int(bottom - 84 * scale)))


def draw_bar(rect, fraction, color):
    """Progress bar"""
    rect = pygame.Rect(rect)
    pygame.draw.rect(screen, (15, 15, 35), rect.inflate(4, 4), border_radius=rect.height)
    if fraction > 0:
        fill = pygame.Rect(rect.x, rect.y, max(rect.height, int(rect.width * clamp(fraction))), rect.height)
        pygame.draw.rect(screen, color, fill, border_radius=rect.height)
        pygame.draw.line(screen, mix(color, WHITE, 0.5), (fill.x + 4, fill.y + 2), (fill.right - 5, fill.y + 2), 1)


def draw_rank_progress(cx, y, width=200):
    """Rank badge, tier name and the bar to the next tier"""
    rp = save["rp"]
    tier = rank_tier(rp)
    name, color = RANKS[tier][1], RANKS[tier][2]
    draw_rank_badge(screen, cx - width // 2 + 12, y + 8, tier, 13)
    if tier + 1 < len(RANKS):
        low, high = RANKS[tier][0], RANKS[tier + 1][0]
        draw_text(screen, f"{name}   {rp} / {high} RP", font_tiny, (cx + 14, y), color)
        draw_bar((cx - width // 2 + 34, y + 12, width - 40, 8), (rp - low) / (high - low), color)
    else:
        draw_text(screen, f"{name}   {rp} RP", font_tiny, (cx + 14, y + 6), color)


def draw_finish_line(cam):
    """Checkered banner at the goal height"""
    y = CAMERA_LINE - goal * 10 - cam
    if not -40 < y < BG_Y + 40:
        return
    for i in range(BG_X // 10):
        for row in (0, 1):
            pygame.draw.rect(world, WHITE if (i + row) % 2 == 0 else (25, 25, 35), (i * 10, y - 8 + row * 8, 10, 8))
    pygame.draw.rect(world, COIN, (0, y - 10, BG_X, 2))
    pygame.draw.rect(world, COIN, (0, y + 8, BG_X, 2))
    draw_text(world, "FINISH", font_small, (BG_X // 2, y - 24), COIN_LIGHT, outline=INK)


def draw_world():
    """Everything in the game world goes on the "world" surface"""
    cam = me.cam
    draw_background(me.height * zone_scale, -cam)
    if goal and mode in ("1v1", "ranked"):
        draw_finish_line(cam)
    for p in platforms:
        if -40 < p.rect.y - cam < BG_Y + 40:
            p.draw(world, cam)
    for group in (coins, powerups, monsters):
        for thing in group:
            if -50 < thing.y - cam < BG_Y + 50:
                thing.draw(world, cam)
    for r in racers:
        if r is not me:
            r.draw(world, cam)
    me.draw(world, cam)
    for p in particles:
        p.draw(world, cam)
    for m in meteors:
        m.draw(world, cam)
    if len(racers) > 1:
        for r in racers:
            r.draw_tag(world, cam)
    for t in popups:
        if t.in_world:
            t.draw(world, cam)
    world.blit(vignette, (0, 0))


######################遊戲中畫面######################


def draw_power_status():
    """Shields and running power-ups, under the score"""
    x, y = 26, 92
    for _ in range(me.shield):
        pygame.draw.circle(screen, POWER_COLORS["shield"], (x, y), 11)
        draw_power_icon(screen, "shield", x, y)
        x += 26
    for kind, left, full in (("jet", me.jet_t, 150), ("magnet", me.magnet_t, 600)):
        if 0 < left < 10 ** 5:
            pygame.draw.circle(screen, POWER_COLORS[kind], (x, y), 11)
            draw_power_icon(screen, kind, x, y)
            draw_bar((x + 16, y - 3, 40, 6), left / full, POWER_COLORS[kind])
            x += 66


def draw_event_banner():
    if not sky_event:
        return
    box = pygame.Rect(BG_X // 2 - 82, 64 if mode == "2v2" else 8, 164, 34)
    draw_panel(screen, box, 185, sky_event["color"], 12)
    draw_text(screen, sky_event["name"], font_tiny, (box.centerx, box.y + 12), sky_event["color"], shadow=False)
    draw_bar((box.x + 14, box.bottom - 10, box.width - 28, 4), sky_event["t"] / sky_event["max"], sky_event["color"])


def draw_race_track():
    """Thin track on the right side: everyone's height from the start (bottom) to the goal (top)"""
    x, y0, y1 = BG_X - 13, 120, 480
    pygame.draw.rect(screen, (15, 15, 35), (x - 5, y0 - 8, 10, y1 - y0 + 16), border_radius=5)
    pygame.draw.rect(screen, (95, 100, 135), (x - 1, y0, 2, y1 - y0))
    for i in range(2):
        for j in range(2):
            pygame.draw.rect(screen, WHITE if (i + j) % 2 == 0 else (25, 25, 35), (x - 4 + i * 4, y0 - 8 + j * 4, 4, 4))
    for r in sorted(racers, key=lambda r: r is me):  # You are drawn last, on top
        y = int(lerp(y1, y0, clamp(r.height / goal)))
        if r is me:
            pygame.draw.circle(screen, WHITE, (x, y), 7)
            pygame.draw.circle(screen, me.char["body"], (x, y), 5)
        else:
            pygame.draw.circle(screen, INK, (x, y), 6)
            pygame.draw.circle(screen, r.tag, (x, y), 4)


def draw_offscreen_arrows():
    """Point at hoppers that are above or below the screen"""
    above = below = 0  # Labels stack up, so two names never cover each other
    for r in racers:
        if r is me or r.gone or r.respawn_t > 0:
            continue
        sy = r.y - me.cam
        x = int(clamp(r.cx, 44, BG_X - 60))
        gap = abs(r.height - me.height)
        if sy < -Racer.H:
            pygame.draw.polygon(screen, r.tag, [(x, 100), (x - 7, 110), (x + 7, 110)])
            draw_text(screen, f"{r.name} +{gap}m", font_tiny, (x, 120 + above * 16), r.tag)
            above += 1
        elif sy > BG_Y:
            pygame.draw.polygon(screen, r.tag, [(x, BG_Y - 8), (x - 7, BG_Y - 18), (x + 7, BG_Y - 18)])
            draw_text(screen, f"{r.name} -{gap}m", font_tiny, (x, BG_Y - 28 - below * 16), r.tag)
            below += 1


def draw_hud():
    if mode == "solo":
        draw_text(screen, str(score()), font_big, (14, 6), anchor="topleft", outline=INK)
        draw_text(screen, f"{me.height} m", font_small, (16, 50), anchor="topleft")
        draw_text(screen, f"BEST {save['high_score']}", font_small, (BG_X - 14, 12), anchor="topright")
        draw_coin_icon(screen, BG_X - 22, 48, 7)
        draw_text(screen, str(int(me.coins)), font_small, (BG_X - 34, 48), COIN_LIGHT, anchor="midright")
    else:
        if mode == "2v2":
            totals = team_totals()
            for i, (color, label) in enumerate(((TEAM_BLUE, "YOUR TEAM"), (TEAM_RED, "RIVALS"))):
                draw_text(screen, f"{label}  {totals[i]} m", font_tiny, (16 + i * 192, 6), color, anchor="topleft")
                draw_bar((16 + i * 192, 28, 176, 10), totals[i] / goal, color)
            draw_text(screen, f"{fmt_time(match_t)}  -  first team to {goal} m", font_tiny, (BG_X // 2, 52))
        else:
            place = standings().index(me) + 1
            draw_text(screen, ORDINALS[place - 1], font_big, (14, 6), PLACE_COLORS[place - 1], anchor="topleft", outline=INK)
            draw_text(screen, f"{min(me.height, goal)} / {goal} m", font_small, (16, 50), anchor="topleft")
            draw_text(screen, fmt_time(match_t), font_small, (BG_X - 14, 12), anchor="topright")
            draw_race_track()
        draw_coin_icon(screen, BG_X - 22, BG_Y - 18, 7)
        draw_text(screen, str(int(me.coins)), font_small, (BG_X - 34, BG_Y - 18), COIN_LIGHT, anchor="midright")
        draw_offscreen_arrows()
        if me.respawn_t > 0 and state == "play":
            draw_text(screen, "Oops! Jumping back in...", font_small, (BG_X // 2, BG_Y // 2), outline=INK)
    draw_power_status()
    draw_event_banner()


def draw_countdown():
    number = str(3 - state_t // 45)
    k = (state_t % 45) / 45
    img = pygame.transform.rotozoom(text_image(number, font_title, COIN_LIGHT), 0, 2.2 - 1.0 * ease(k))
    edge = pygame.transform.rotozoom(text_image(number, font_title, (60, 30, 90)), 0, 2.2 - 1.0 * ease(k))
    rect = img.get_rect(center=(BG_X // 2, 220))
    for dx, dy in OUTLINE_OFFSETS:
        screen.blit(edge, rect.move(dx * 2, dy * 2))
    screen.blit(img, rect)
    draw_text(screen, MODE_INFO[mode][1].format(goal=goal), font_small, (BG_X // 2, 310), outline=INK)


def draw_finish_banner():
    """Big result text while the match winds down"""
    pulse = 1 + 0.06 * math.sin(ticks * 0.2)
    color = GOOD if result["won"] else BAD
    img = pygame.transform.rotozoom(text_image(result["title"], font_big, color), 0, pulse * ease(state_t / 20))
    edge = pygame.transform.rotozoom(text_image(result["title"], font_big, INK), 0, pulse * ease(state_t / 20))
    rect = img.get_rect(center=(BG_X // 2, 200))
    for dx, dy in OUTLINE_OFFSETS:
        screen.blit(edge, rect.move(dx, dy))
    screen.blit(img, rect)


def draw_game_over():
    box = pygame.Rect(45, 130, BG_X - 90, 340)
    draw_panel(screen, box, 215)
    draw_text(screen, "GAME OVER", font_big, (BG_X // 2, box.top + 42), BAD, outline=(60, 20, 30))
    draw_text(screen, str(score()), font_title, (BG_X // 2, box.top + 108), WHITE, outline=INK)
    draw_text(screen, f"Height {me.height} m   Bonus +{bonus}", font_small, (BG_X // 2, box.top + 156))
    if new_best:
        pulse = 1 + 0.08 * math.sin(ticks * 0.15)
        img = pygame.transform.rotozoom(text_image("NEW BEST!", font_mid, COIN_LIGHT), 0, pulse)
        screen.blit(img, img.get_rect(center=(BG_X // 2, box.top + 194)))
    else:
        draw_text(screen, f"Best {save['high_score']}", font_mid, (BG_X // 2, box.top + 194))
    draw_coin_icon(screen, BG_X // 2 - 62, box.top + 234, 9)
    draw_text(screen, f"+{int(me.coins)} coins", font_small, (BG_X // 2 - 46, box.top + 234), COIN_LIGHT, anchor="midleft")
    if ui_button((box.x + 16, box.bottom - 66, 170, 48), "RETRY", (70, 190, 110), sub="SPACE"):
        begin("solo")
    elif ui_button((box.right - 116, box.bottom - 66, 100, 48), "MENU", (90, 100, 140), font_small):
        go_menu()


def draw_pause():
    screen.blit(dim, (0, 0))
    draw_text(screen, "PAUSED", font_title, (BG_X // 2, BG_Y // 2 - 70), WHITE, outline=INK)
    if ui_button((100, BG_Y // 2 - 10, 200, 50), "RESUME", (70, 190, 110), sub="P"):
        set_state("play")
    elif ui_button((100, BG_Y // 2 + 56, 200, 50), "QUIT TO MENU", (200, 90, 100), font_small):
        go_menu()


def draw_racer_card(r, rect, searching=False):
    """Name card on the "versus" screen and nowhere else"""
    draw_panel(screen, rect, 190, r.tag, 14)
    if searching:
        draw_text(screen, "Searching" + "." * (1 + (ticks // 12) % 3), font_small, rect.center, (190, 200, 225))
        return
    draw_preview(screen, r.char, rect.x + 36, rect.bottom - 14, 1.25, id(r) % 50)
    draw_text(screen, r.name, font_small, (rect.x + 70, rect.y + 14), r.tag, anchor="topleft")
    draw_rank_badge(screen, rect.x + 80, rect.y + 56, r.tier, 9)
    draw_text(screen, RANKS[r.tier][1], font_tiny, (rect.x + 96, rect.y + 58), anchor="midleft")


def draw_intro():
    """Matchmaking screen: who is playing, and how to win"""
    screen.blit(dim, (0, 0))
    screen.blit(dim, (0, 0))  # Twice, so the text is easy to read
    title, rule = MODE_INFO[mode]
    draw_text(screen, title, font_big if mode != "2v2" else font_mid, (BG_X // 2, 64), COIN_LIGHT, outline=(60, 30, 90))
    draw_text(screen, rule.format(goal=goal), font_small, (BG_X // 2, 108))
    if mode == "1v1":
        slots = [(20, 210), (205, 210)]
    elif mode == "2v2":
        slots = [(20, 165), (20, 265), (205, 165), (205, 265)]
    else:
        slots = [(20, 165), (205, 165), (20, 265), (205, 265)]
    for i, r in enumerate(racers):
        x, y = slots[i]
        side = -1 if x < 100 else 1
        slide = int((1 - ease((state_t - i * 5) / 22)) * 220) * side  # Cards slide in from the sides
        draw_racer_card(r, pygame.Rect(x + slide, y, 175, 88), r.brain is not None and state_t < 45 + i * 22)
    if mode != "ranked":
        draw_text(screen, "VS", font_big, (BG_X // 2, 254 if mode == "1v1" else 260), WHITE, outline=(200, 60, 80))
    else:
        draw_text(screen, "FREE FOR ALL", font_small, (BG_X // 2, 372), COIN_LIGHT)
    if today_event.get("reward") or today_event.get("rp") or today_event.get("coin"):
        draw_text(screen, f"{today_event['name']}: {today_event['desc']}", font_tiny, (BG_X // 2, 410), COIN_LIGHT)
    for i, line in enumerate(wrap_text(TIPS[match_tip], font_small, 340)):
        draw_text(screen, line, font_small, (BG_X // 2, 452 + i * 22), (210, 220, 245))
    draw_text(screen, "SPACE to skip", font_tiny, (BG_X // 2, 560), (170, 180, 210))


def draw_results():
    """Final table, rewards and rank after a match"""
    screen.blit(dim, (0, 0))
    box = pygame.Rect(24, 50, BG_X - 48, 500)
    draw_panel(screen, box, 200)
    draw_text(screen, result["title"], font_big, (BG_X // 2, box.y + 40), GOOD if result["won"] else BAD, outline=INK)
    y = box.y + 78
    if mode == "2v2":
        blue, red = result["totals"]
        draw_text(screen, f"Your team {blue} m", font_small, (BG_X // 2 - 8, y + 4), TEAM_BLUE, anchor="midright")
        draw_text(screen, f"Rivals {red} m", font_small, (BG_X // 2 + 8, y + 4), TEAM_RED, anchor="midleft")
        y += 22
    for i, r in enumerate(result["order"]):
        row = pygame.Rect(box.x + 14, y, box.width - 28, 44)
        draw_panel(screen, row, 150 if r is me else 70, COIN if r is me else r.tag, 10)
        if mode != "2v2":
            draw_text(screen, ORDINALS[i], font_small, (row.x + 12, row.centery), PLACE_COLORS[i], anchor="midleft")
        draw_hopper(screen, r.char, row.x + 76, row.bottom - 6, t=ticks)
        draw_text(screen, r.name, font_small, (row.x + 104, row.centery), r.tag, anchor="midleft")
        if r.finished:
            detail = fmt_time(r.finish_t)
        else:
            detail = f"{r.final} m"
        draw_text(screen, detail, font_small, (row.right - 12, row.centery), anchor="midright")
        y += 49

    # Rewards
    y += 14
    extra = f"  (+{result['collected']} picked up)" if result["collected"] else ""
    label = f"+{result['prize']} coins{extra}"
    width = font_small.size(label)[0]
    draw_coin_icon(screen, BG_X // 2 - width // 2 - 10, y, 9)
    draw_text(screen, label, font_small, (BG_X // 2 + 8, y), COIN_LIGHT)
    if mode == "ranked":
        change = result["rp_change"]
        draw_text(screen, f"{'+' if change >= 0 else ''}{change} RP", font_mid, (BG_X // 2, y + 32), GOOD if change >= 0 else BAD)
        draw_rank_progress(BG_X // 2, y + 58, 220)
        if result["tier_change"]:
            text = "RANK UP!" if result["tier_change"] > 0 else "Rank down"
            draw_text(screen, text, font_small, (box.right - 60, y + 32), COIN_LIGHT if result["tier_change"] > 0 else BAD)

    if ui_button((box.x + 16, box.bottom - 62, 190, 46), "PLAY AGAIN", (70, 190, 110), font_small, sub="SPACE"):
        begin(mode)
    elif ui_button((box.right - 126, box.bottom - 62, 110, 46), "MENU", (90, 100, 140), font_small):
        go_menu()


######################選單畫面######################


def draw_menu():
    bob = math.sin(ticks * 0.05) * 5
    draw_text(screen, "SKY HOPPER", font_title, (BG_X // 2, 50 + bob), COIN_LIGHT, outline=(60, 30, 90))

    # Player card: hopper, coins, best score and rank
    card = pygame.Rect(20, 92, 360, 96)
    draw_panel(screen, card)
    char = my_character()
    draw_preview(screen, char, card.x + 50, card.bottom - 12, 1.6)
    draw_text(screen, char["name"], font_mid, (card.x + 100, card.y + 8), anchor="topleft")
    draw_coin_icon(screen, card.x + 110, card.y + 54, 9)
    draw_text(screen, str(save["coins"]), font_small, (card.x + 126, card.y + 54), COIN_LIGHT, anchor="midleft")
    draw_text(screen, f"BEST {save['high_score']}", font_tiny, (card.x + 102, card.y + 78), anchor="midleft")
    tier = rank_tier(save["rp"])
    draw_rank_badge(screen, card.right - 54, card.y + 32, tier, 18)
    draw_text(screen, RANKS[tier][1], font_small, (card.right - 54, card.y + 66), RANKS[tier][2])
    draw_text(screen, f"{save['rp']} RP", font_tiny, (card.right - 54, card.y + 84))

    # Today's event
    strip = pygame.Rect(20, 196, 360, 44)
    draw_panel(screen, strip, 150, COIN, 14)
    draw_text(screen, f"TODAY: {today_event['name']}", font_small, (strip.centerx, strip.y + 13), COIN_LIGHT)
    draw_text(screen, today_event["desc"], font_tiny, (strip.centerx, strip.y + 32), shadow=False)

    stats = save["stats"]
    quests_done = sum(q["done"] for q in save["daily"]["quests"])
    if ui_button((20, 250, 360, 52), "SOLO CLIMB", (70, 190, 110)):
        begin("solo")
    elif ui_button((20, 312, 175, 52), "1 v 1", (70, 130, 230),
                   sub=f"{stats.get('wins_1v1', 0)} W   {stats.get('losses_1v1', 0)} L"):
        begin("1v1")
    elif ui_button((205, 312, 175, 52), "2 v 2", (150, 100, 230),
                   sub=f"{stats.get('wins_2v2', 0)} W   {stats.get('losses_2v2', 0)} L"):
        begin("2v2")
    elif ui_button((20, 374, 360, 54), "RANKED", (235, 150, 50), sub=f"{RANKS[tier][1]}  -  4 hopper race"):
        begin("ranked")
    elif ui_button((20, 440, 175, 50), "SHOP", (230, 95, 140)):
        set_state("shop")
    elif ui_button((205, 440, 175, 50), "QUESTS", (60, 175, 170), sub=f"{quests_done} / 3 done"):
        set_state("quests")
    draw_text(screen, "Arrows / A D move    P pause    M music    F11 full", font_tiny, (BG_X // 2, 512), (215, 225, 245))


def shop_say(text, color):
    shop_msg[0], shop_msg[1], shop_msg[2] = text, color, 110


def buy(price):
    """Pay for something if there are enough coins"""
    if save["coins"] < price:
        shop_say(f"Not enough coins! You need {price - save['coins']} more", BAD)
        play("error")
        return False
    save["coins"] -= price
    play("buy")
    return True


def draw_shop():
    global shop_tab, click
    draw_text(screen, "SHOP", font_big, (BG_X // 2, 34), COIN_LIGHT, outline=(60, 30, 90))
    if ui_button((12, 14, 58, 38), "<", (90, 100, 140)):
        set_state("menu")
    draw_panel(screen, (292, 16, 96, 34), 180, COIN, 14)
    draw_coin_icon(screen, 310, 33, 8)
    draw_text(screen, str(save["coins"]), font_small, (324, 33), COIN_LIGHT, anchor="midleft")
    for i, label in enumerate(("HOPPERS", "UPGRADES")):
        if ui_button((20 + i * 185, 62, 175, 36), label, (70, 130, 230) if shop_tab == i else (60, 65, 95), font_small):
            shop_tab = i

    if shop_tab == 0:
        for i, char in enumerate(CHARACTERS):
            rect = pygame.Rect(20 + (i % 2) * 185, 112 + (i // 2) * 108, 175, 102)
            owned = char["id"] in save["owned"]
            equipped = save["character"] == char["id"]
            hover = rect.collidepoint(mouse)
            draw_panel(screen, rect, 200 if hover else 160, COIN if equipped else WHITE, 14)
            if equipped:
                pygame.draw.rect(screen, COIN, rect, 2, border_radius=14)
            draw_preview(screen, char, rect.x + 34, rect.y + 66, 1.25, i * 9)
            draw_text(screen, char["name"], font_small, (rect.x + 66, rect.y + 7), anchor="topleft")
            for j, line in enumerate(wrap_text(char["perk"], font_tiny, 104)[:3]):
                draw_text(screen, line, font_tiny, (rect.x + 66, rect.y + 30 + j * 15), (200, 210, 235), anchor="topleft", shadow=False)
            price = character_price(char)
            if equipped:
                draw_text(screen, "EQUIPPED", font_tiny, (rect.centerx, rect.bottom - 13), COIN_LIGHT, shadow=False)
            elif owned:
                draw_text(screen, "TAP TO EQUIP", font_tiny, (rect.centerx, rect.bottom - 13), GOOD, shadow=False)
            else:
                draw_coin_icon(screen, rect.x + 22, rect.bottom - 13, 7)
                draw_text(screen, str(price), font_small, (rect.x + 34, rect.bottom - 13),
                          COIN_LIGHT if save["coins"] >= price else BAD, anchor="midleft")
            if hover and click:
                click = False
                if owned:
                    if not equipped:
                        save["character"] = char["id"]
                        play("click")
                        shop_say(f"{char['name']} is ready to hop!", GOOD)
                        save_game()
                elif buy(price):
                    save["owned"].append(char["id"])
                    save["character"] = char["id"]
                    shop_say(f"You unlocked {char['name']}!", COIN_LIGHT)
                    save_game()
    else:
        for i, up in enumerate(UPGRADES):
            rect = pygame.Rect(20, 112 + i * 86, 360, 80)
            level = upgrade_level(up["id"])
            draw_panel(screen, rect, 160, WHITE, 14)
            icon = (rect.x + 36, rect.centery)
            pygame.draw.circle(screen, (45, 50, 85), icon, 24)
            pygame.draw.circle(screen, COIN if level else (120, 125, 150), icon, 24, 2)
            if up["id"] == "wallet":
                draw_coin_icon(screen, icon[0], icon[1], 11)
            elif up["id"] == "battery":
                pygame.draw.rect(screen, WHITE, (icon[0] - 10, icon[1] - 6, 20, 12), 2, border_radius=2)
                pygame.draw.rect(screen, WHITE, (icon[0] + 10, icon[1] - 3, 3, 6))
                pygame.draw.rect(screen, GOOD, (icon[0] - 7, icon[1] - 3, 10, 6))
            elif up["id"] == "luck":
                pygame.draw.polygon(screen, COIN_LIGHT, star_points(icon[0], icon[1], 12, 5))
            else:
                draw_power_icon(screen, up["id"], icon[0], icon[1])
            draw_text(screen, up["name"], font_small, (rect.x + 72, rect.y + 7), anchor="topleft")
            for j, line in enumerate(wrap_text(up["desc"], font_tiny, 176)[:2]):
                draw_text(screen, line, font_tiny, (rect.x + 72, rect.y + 30 + j * 15), (200, 210, 235), anchor="topleft", shadow=False)
            for k in range(up["max"]):  # Level pips
                pygame.draw.rect(screen, COIN if k < level else (50, 55, 85), (rect.x + 72 + k * 20, rect.bottom - 14, 16, 7), border_radius=3)
            spot = (rect.right - 96, rect.y + 18, 84, 44)
            if level >= up["max"]:
                ui_button(spot, "MAX", (95, 95, 110), font_small, enabled=False)
            else:
                price = upgrade_price(up)
                afford = save["coins"] >= price
                if ui_button(spot, str(price), (70, 190, 110) if afford else (150, 95, 105), font_small, sub="coins") and buy(price):
                    save["upgrades"][up["id"]] = level + 1
                    shop_say(f"{up['name']} is now level {level + 1}!", COIN_LIGHT)
                    save_game()

    if daily("sale") < 1:
        draw_text(screen, f"{today_event['name']}: 20% off today!", font_tiny, (BG_X // 2, 104), COIN_LIGHT)
    if shop_msg[2] > 0:
        shop_msg[2] -= 1
        draw_text(screen, shop_msg[0], font_small, (BG_X // 2, 572), shop_msg[1], outline=INK)


def draw_quests():
    draw_text(screen, "DAILY QUESTS", font_mid, (BG_X // 2 + 16, 34), COIN_LIGHT, outline=(60, 30, 90))
    if ui_button((12, 14, 58, 38), "<", (90, 100, 140)):
        set_state("menu")

    strip = pygame.Rect(20, 66, 360, 62)
    draw_panel(screen, strip, 160, COIN, 14)
    draw_text(screen, "TODAY'S EVENT", font_tiny, (strip.centerx, strip.y + 12), COIN, shadow=False)
    draw_text(screen, today_event["name"], font_small, (strip.centerx, strip.y + 30), COIN_LIGHT)
    draw_text(screen, today_event["desc"], font_tiny, (strip.centerx, strip.y + 49), shadow=False)

    for i, quest in enumerate(save["daily"]["quests"]):
        info = QUEST_BY_ID[quest["id"]]
        rect = pygame.Rect(20, 138 + i * 80, 360, 72)
        draw_panel(screen, rect, 160, GOOD if quest["done"] else WHITE, 14)
        draw_text(screen, info["text"].format(n=info["n"]), font_small, (rect.x + 14, rect.y + 9), anchor="topleft")
        draw_bar((rect.x + 16, rect.y + 44, 216, 12), quest["p"] / info["n"], GOOD if quest["done"] else TEAM_BLUE)
        draw_text(screen, f"{quest['p']} / {info['n']}", font_tiny, (rect.x + 124, rect.y + 50), shadow=False)
        if quest["done"]:
            draw_text(screen, "DONE!", font_small, (rect.right - 58, rect.centery), GOOD)
        else:
            draw_coin_icon(screen, rect.right - 84, rect.centery, 9)
            draw_text(screen, f"+{info['reward']}", font_small, (rect.right - 70, rect.centery), COIN_LIGHT, anchor="midleft")

    # Your record so far
    stats = save["stats"]
    box = pygame.Rect(20, 384, 360, 164)
    draw_panel(screen, box, 160, WHITE, 14)
    draw_text(screen, "YOUR RECORD", font_tiny, (box.centerx, box.y + 13), COIN, shadow=False)
    lines = [
        ("1 v 1", f"{stats.get('wins_1v1', 0)} wins   {stats.get('losses_1v1', 0)} losses"),
        ("2 v 2", f"{stats.get('wins_2v2', 0)} wins   {stats.get('losses_2v2', 0)} losses"),
        ("Ranked", f"{stats.get('games_ranked', 0)} played   {stats.get('firsts_ranked', 0)} first places"),
        ("Solo", f"best {save['high_score']} points   {stats.get('best_height', 0)} m"),
    ]
    for i, (name, text) in enumerate(lines):
        draw_text(screen, name, font_small, (box.x + 16, box.y + 36 + i * 22), TEAM_BLUE, anchor="midleft")
        draw_text(screen, text, font_tiny, (box.x + 96, box.y + 37 + i * 22), anchor="midleft", shadow=False)
    draw_rank_progress(box.centerx, box.bottom - 30, 240)
    draw_text(screen, f"Login streak: day {save['daily']['streak']}   -   new quests every day", font_tiny,
              (BG_X // 2, 568), (215, 225, 245))


def draw_toasts():
    """Messages like "Daily bonus!" slide in from the bottom of the screen"""
    for i, (text, color, left) in enumerate(toasts[:3]):
        slide = ease(min(200 - left, left) / 14)
        img = text_image(text, font_tiny, color)
        box = img.get_rect(center=(BG_X // 2, int(BG_Y + 20 - slide * (66 + i * 32)))).inflate(26, 12)
        draw_panel(screen, box, 215, color, 12)
        screen.blit(img, img.get_rect(center=box.center))


def draw_frame():
    draw_world()

    # Shake the world when something big happens
    offset = (0, 0)
    if shake > 0.5:
        offset = (random.uniform(-shake, shake), random.uniform(-shake, shake))
    screen.fill(BLACK)
    screen.blit(world, offset)
    if flash > 2:  # White flash when a sky event starts
        flash_layer.set_alpha(int(flash))
        screen.blit(flash_layer, (0, 0))

    # Text and menus on top
    for t in popups:
        if not t.in_world:
            t.draw(screen)
    if state in ("menu", "shop", "quests"):
        screen.blit(dim, (0, 0))
        if state == "menu":
            draw_menu()
        elif state == "shop":
            draw_shop()
        else:
            draw_quests()
    elif state == "intro":
        draw_intro()
    else:
        draw_hud()
        if state == "countdown":
            draw_countdown()
        elif state == "over":
            draw_game_over()
        elif state == "paused":
            draw_pause()
        elif state == "finish":
            draw_finish_banner()
        elif state == "results":
            draw_results()
    draw_toasts()


######################輸入######################


def handle_key(key):
    global shop_tab
    if key == pygame.K_F11:
        try:
            pygame.display.toggle_fullscreen()
        except pygame.error:
            pass
    elif key == pygame.K_m:
        save["music"] = not save["music"]
        set_music(save["music"])
        save_game()
        toast("Music on" if save["music"] else "Music off")
    elif key == pygame.K_ESCAPE:
        if state == "menu":
            quit_game()
        elif state == "play":
            set_state("paused")
        elif state in ("shop", "quests"):
            set_state("menu")
        else:
            go_menu()
    elif state == "menu":
        if key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_1):
            begin("solo")
        elif key == pygame.K_2:
            begin("1v1")
        elif key == pygame.K_3:
            begin("2v2")
        elif key in (pygame.K_4, pygame.K_r):
            begin("ranked")
        elif key == pygame.K_s:
            set_state("shop")
        elif key == pygame.K_q:
            set_state("quests")
    elif state == "shop" and key == pygame.K_TAB:
        shop_tab = 1 - shop_tab
    elif state == "intro" and key in (pygame.K_SPACE, pygame.K_RETURN):
        set_state("countdown")
    elif key == pygame.K_p and state in ("play", "paused"):
        set_state("paused" if state == "play" else "play")
    elif key in (pygame.K_SPACE, pygame.K_RETURN):
        if state == "over":
            begin("solo")
        elif state == "results":
            begin(mode)


def handle_events():
    global mouse, click
    mouse = pygame.mouse.get_pos()
    click = False
    for ev in pygame.event.get():
        if ev.type == pygame.QUIT:
            quit_game()
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            mouse = ev.pos
            click = True
        elif ev.type == pygame.KEYDOWN:
            handle_key(ev.key)


######################主程式######################


def main():
    global ticks, state_t
    icon = pygame.Surface((40, 40), pygame.SRCALPHA)
    draw_hopper(icon, my_character(), 20, 37)
    pygame.display.set_icon(icon)

    refresh_daily()  # Login bonus and today's quests
    start_game("attract")  # Bots play behind the menu
    set_music(save["music"])

    while True:
        FPS.tick(60)  # Cap framerate at 60
        ticks += 1
        state_t += 1
        handle_events()
        update_game()
        draw_frame()
        pygame.display.update()  # Update the display


if __name__ == "__main__":
    main()
