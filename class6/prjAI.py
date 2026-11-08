######################載入套件######################

import pygame  # Import pygame for games
import sys  # Import system tools
import random  # Import random for platforms
import math  # Import math for waves and angles
import os  # Import os to find the high score file
from array import array  # Used to build sound effects without sound files

######################遊戲常數######################

BG_X = 400  # Window width
BG_Y = 600  # Window height
CAMERA_LINE = 250  # While climbing, the player is kept at this height
PLATFORM_W = 64  # Platform width
PLATFORM_H = 12  # Platform height

GRAVITY = 0.5
JUMP_POWER = -12.5  # Normal jump (max height about 156 px)
SPRING_POWER = -21  # Spring jump
STOMP_POWER = -14  # Jump after stomping a monster

HIGHSCORE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prjAI_highscore.txt")

# Colors (RGB)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
PLAYER_COLOR = (95, 220, 120)
PLAYER_DARK = (40, 140, 70)
PLAYER_LIGHT = (175, 245, 180)
GRASS = (90, 200, 90)
GRASS_LIGHT = (160, 240, 140)
DIRT = (135, 95, 60)
DIRT_DARK = (90, 60, 40)
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

# Sky colors at different heights (meters): (height, top color, bottom color)
SKY_STOPS = [
    (0, (100, 175, 255), (205, 235, 255)),
    (400, (80, 140, 235), (255, 215, 175)),
    (1000, (225, 105, 90), (255, 185, 115)),
    (1700, (65, 40, 110), (195, 85, 115)),
    (2600, (8, 8, 30), (35, 25, 75)),
]

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


def sky_colors(height):
    """Return (top color, bottom color) of the sky for a height"""
    for i in range(len(SKY_STOPS) - 1):
        h0, top0, bottom0 = SKY_STOPS[i]
        h1, top1, bottom1 = SKY_STOPS[i + 1]
        if height < h1:
            t = (height - h0) / (h1 - h0)
            return mix(top0, top1, t), mix(bottom0, bottom1, t)
    return SKY_STOPS[-1][1], SKY_STOPS[-1][2]


def rotated_rect_points(cx, cy, w, h, angle):
    """Corners of a rectangle turned by an angle (used for broken platforms)"""
    c, s = math.cos(angle), math.sin(angle)
    points = []
    for dx, dy in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)):
        points.append((cx + dx * c - dy * s, cy + dx * s + dy * c))
    return points


def draw_text(surf, text, font, pos, color=WHITE, anchor="center", outline=None, shadow=True):
    """Draw text with an optional outline and soft shadow"""
    img = font.render(text, True, color)
    rect = img.get_rect(**{anchor: pos})
    if outline:
        edge = font.render(text, True, outline)
        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2), (-2, -2), (2, 2), (-2, 2), (2, -2)):
            surf.blit(edge, rect.move(dx, dy))
    elif shadow:
        dark = font.render(text, True, BLACK)
        dark.set_alpha(110)
        surf.blit(dark, rect.move(2, 3))
    surf.blit(img, rect)
    return rect


def draw_panel(surf, rect, alpha=150):
    """See-through dark box with rounded corners"""
    panel = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(panel, (10, 10, 25, alpha), panel.get_rect(), border_radius=18)
    pygame.draw.rect(panel, (255, 255, 255, 60), panel.get_rect(), 2, border_radius=18)
    surf.blit(panel, rect)


######################初始化設定######################

pygame.mixer.pre_init(22050, -16, 1, 512)
pygame.init()  # Initialize pygame
FPS = pygame.time.Clock()  # Create the frame clock

pygame.display.set_caption("Sky Hopper")  # Window title
screen = pygame.display.set_mode((BG_X, BG_Y))  # Create the window
world = pygame.Surface((BG_X, BG_Y))  # The game is drawn here first, so it can shake


def load_font(size):
    return pygame.font.SysFont("arialrounded,verdana,arial", size, bold=True)


font_title = load_font(54)
font_big = load_font(40)
font_mid = load_font(26)
font_small = load_font(18)

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


SOUNDS = {
    "jump": make_sound([(300, 620, 0.12)], 0.12),
    "spring": make_sound([(250, 1300, 0.32)], 0.14),
    "break": make_sound([(0, 0, 0.22)], 0.22, "noise"),
    "coin": make_sound([(988, 988, 0.06), (1319, 1319, 0.2)], 0.3, "sine"),
    "stomp": make_sound([(650, 150, 0.16)], 0.16),
    "hurt": make_sound([(500, 80, 0.45)], 0.16),
    "fall": make_sound([(800, 120, 0.8)], 0.3, "sine"),
    "milestone": make_sound([(660, 660, 0.08), (880, 880, 0.08), (1320, 1320, 0.25)], 0.3, "sine"),
}


def play(name):
    sound = SOUNDS.get(name)
    if sound:
        sound.play()


######################最高分######################


def load_high_score():
    try:
        with open(HIGHSCORE_FILE) as f:
            return int(f.read().strip() or 0)
    except (OSError, ValueError):
        return 0


def save_high_score(value):
    try:
        with open(HIGHSCORE_FILE, "w") as f:
            f.write(str(value))
    except OSError:
        pass


######################物件類別######################


class Particle:
    def __init__(self, x, y, vx, vy, color, size, life, gravity=0.15):
        """A small dot that flies, shrinks and disappears"""
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.color = color
        self.size = size
        self.life = self.max_life = life
        self.gravity = gravity

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += self.gravity
        self.vx *= 0.98
        self.life -= 1

    def draw(self, surf):
        radius = self.size * self.life / self.max_life
        if radius >= 0.5:
            pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), max(1, round(radius)))


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

    def draw(self, surf):
        alpha = int(255 * clamp(self.life / 20))
        rect = self.image.get_rect(center=(int(self.x), int(self.y)))
        self.shadow.set_alpha(alpha // 2)
        self.image.set_alpha(alpha)
        surf.blit(self.shadow, rect.move(2, 2))
        surf.blit(self.image, rect)


class Player:
    W = 34
    H = 34

    def __init__(self, x, y):
        """Initialize the player at a top-left position"""
        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0  # Sideways speed (smooth speed up / slow down)
        self.vy = 0.0  # Vertical speed
        self.facing = 1  # 1 = looking right, -1 = looking left
        self.squash = 0.0  # Squish amount right after landing
        self.blink = 0
        self.blink_timer = random.randint(90, 200)
        self.trail = []  # Glow trail after a spring jump
        self.dead = False

    @property
    def rect(self):
        return pygame.Rect(round(self.x), round(self.y), self.W, self.H)

    def handle_input(self, direction):
        """direction: -1 left, 0 none, 1 right"""
        if direction:
            self.vx += direction * 0.9
            self.facing = direction
        self.vx *= 0.86  # Friction
        self.vx = clamp(self.vx, -7, 7)

    def update(self, platforms):
        """
        Move the player and return the platform it landed on (or None) \n
        The whole path since last frame is checked, so fast falls never skip a platform \n
        """
        # Sideways move with screen wrap
        self.x += self.vx
        if self.x + self.W < 0:
            self.x = BG_X
        elif self.x > BG_X:
            self.x = -self.W

        prev_bottom = self.y + self.H
        self.vy = min(self.vy + GRAVITY, 16)
        self.y += self.vy

        # Animations
        self.squash = max(0.0, self.squash - 0.08)
        self.blink_timer -= 1
        if self.blink_timer <= 0:
            self.blink = 8
            self.blink_timer = random.randint(120, 260)
        self.blink = max(0, self.blink - 1)
        if self.vy < -13:
            self.trail.append((self.x + self.W / 2, self.y + self.H / 2))
            self.trail = self.trail[-8:]
        elif self.trail:
            self.trail.pop(0)

        if self.dead or self.vy <= 0:  # Only land while falling
            return None
        bottom = self.y + self.H
        left, right = self.x + 4, self.x + self.W - 4  # Feet are a bit narrower than the body
        for platform in platforms:
            if platform.broken:
                continue
            if prev_bottom <= platform.rect.top <= bottom and right > platform.rect.left and left < platform.rect.right:
                return platform
        return None

    def bounce(self, top, power):
        """Stand on top of something and jump"""
        self.y = top - self.H
        self.vy = power
        self.squash = 1.0

    def draw(self, surf):
        # Glow trail
        for i, (tx, ty) in enumerate(self.trail):
            pygame.draw.circle(surf, mix(PLAYER_LIGHT, WHITE, 0.4), (int(tx), int(ty)), int(4 + i * 1.6))

        # Squash and stretch: tall when flying up, flat right after landing
        stretch = clamp(-self.vy / 30, -0.12, 0.2)
        sx = 1 - stretch * 0.6 + self.squash * 0.3
        sy = 1 + stretch - self.squash * 0.3
        w, h = int(self.W * sx), int(self.H * sy)
        body = pygame.Rect(0, 0, w, h)
        body.midbottom = (round(self.x + self.W / 2), round(self.y + self.H))

        # Feet, body, belly, shine
        for fx in (-8, 8):
            pygame.draw.ellipse(surf, PLAYER_DARK, (body.centerx + fx - 6, body.bottom - 3, 12, 7))
        pygame.draw.rect(surf, PLAYER_DARK, body.move(0, 2), border_radius=12)
        pygame.draw.rect(surf, PLAYER_COLOR, body, border_radius=12)
        belly = pygame.Rect(0, 0, max(4, w - 14), max(4, h // 2 - 2))
        belly.midbottom = (body.centerx, body.bottom - 4)
        pygame.draw.ellipse(surf, PLAYER_LIGHT, belly)
        pygame.draw.ellipse(surf, WHITE, (body.left + 5, body.top + 4, 8, 5))

        # Eyes
        eye_y = int(body.top + h * 0.35)
        look_y = int(clamp(self.vy / 5, -2, 2))
        for ex in (-7, 7):
            eye_x = body.centerx + ex + self.facing * 2
            if self.dead:
                pygame.draw.line(surf, BLACK, (eye_x - 3, eye_y - 3), (eye_x + 3, eye_y + 3), 2)
                pygame.draw.line(surf, BLACK, (eye_x - 3, eye_y + 3), (eye_x + 3, eye_y - 3), 2)
            elif self.blink > 0:
                pygame.draw.line(surf, BLACK, (eye_x - 4, eye_y), (eye_x + 4, eye_y), 2)
            else:
                pygame.draw.circle(surf, WHITE, (eye_x, eye_y), 5)
                pygame.draw.circle(surf, BLACK, (eye_x + self.facing * 2, eye_y + look_y), 3)

        # Mouth: "O" when flying fast, smile otherwise
        mouth_x = body.centerx + self.facing * 2
        if self.dead or self.vy < -13:
            pygame.draw.circle(surf, PLAYER_DARK, (mouth_x, eye_y + 9), 3)
        else:
            pygame.draw.arc(surf, PLAYER_DARK, (mouth_x - 5, eye_y + 3, 10, 8), math.pi * 1.1, math.pi * 1.9, 2)
        # Blush cheeks
        for cx in (-12, 12):
            pygame.draw.circle(surf, (255, 150, 150), (body.centerx + cx, eye_y + 7), 2)


class Platform:
    def __init__(self, x, y, kind="normal", width=PLATFORM_W):
        """
        Initialize the platform  \n
        kind: "normal", "moving" or "break"  \n
        """
        self.rect = pygame.Rect(int(x), int(y), width, PLATFORM_H)
        self.x = float(x)  # Exact horizontal position for smooth moving
        self.kind = kind
        self.broken = False
        self.break_t = 0  # Frames since breaking
        self.direction = random.choice([-1, 1])
        self.speed = random.uniform(1.0, 2.2)
        self.has_spring = False
        self.spring_x = 0
        self.spring_t = 0  # Frames the spring stays popped up
        self.tufts = [random.randint(4, width - 4) for _ in range(max(2, width // 22))]

    def add_spring(self):
        self.has_spring = True
        self.spring_x = random.randint(8, self.rect.width - 24)

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

    def draw(self, surf):
        r = self.rect
        if self.kind == "normal":
            pygame.draw.rect(surf, DIRT_DARK, r.move(0, 3), border_radius=6)
            pygame.draw.rect(surf, DIRT, r, border_radius=6)
            pygame.draw.rect(surf, GRASS, (r.x, r.y - 2, r.width, 7), border_radius=4)
            pygame.draw.line(surf, GRASS_LIGHT, (r.x + 4, r.y - 1), (r.right - 5, r.y - 1), 2)
            for tx in self.tufts:
                pygame.draw.line(surf, GRASS, (r.x + tx, r.y - 1), (r.x + tx - 2, r.y - 5), 2)
                pygame.draw.line(surf, GRASS, (r.x + tx, r.y - 1), (r.x + tx + 2, r.y - 4), 2)
        elif self.kind == "moving":
            pygame.draw.rect(surf, METAL_DARK, r.move(0, 3), border_radius=6)
            pygame.draw.rect(surf, METAL, r, border_radius=6)
            pygame.draw.line(surf, METAL_LIGHT, (r.x + 5, r.y + 2), (r.right - 6, r.y + 2), 2)
            for rx in (r.x + 6, r.right - 7):
                pygame.draw.circle(surf, METAL_DARK, (rx, r.centery + 1), 2)
            # Little arrows that show it slides
            for side in (-1, 1):
                ax = r.centerx + side * 8
                pygame.draw.lines(surf, METAL_LIGHT, False,
                                  [(ax - side * 3, r.centery - 2), (ax, r.centery + 1), (ax - side * 3, r.centery + 4)], 2)
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
            sr = self.spring_rect()
            height = 20 if self.spring_t > 0 else 11
            top = r.top - height
            coil = []
            for i in range(6):
                coil.append((sr.x + (3 if i % 2 == 0 else 13), r.top - i * height / 5))
            pygame.draw.lines(surf, (170, 170, 185), False, coil, 2)
            pygame.draw.rect(surf, SPRING_COLOR, (sr.x - 2, top - 3, 20, 5), border_radius=2)
            pygame.draw.line(surf, WHITE, (sr.x, top - 2), (sr.x + 8, top - 2), 1)


class Coin:
    def __init__(self, x, y):
        """A spinning coin worth bonus points"""
        self.x, self.y = x, y
        self.t = random.uniform(0, 6)

    @property
    def rect(self):
        return pygame.Rect(self.x - 11, self.y - 11, 22, 22)

    def update(self):
        self.t += 0.08

    def draw(self, surf):
        cy = self.y + math.sin(self.t * 1.5) * 3
        w = max(3, int(abs(math.cos(self.t)) * 18))
        rect = pygame.Rect(0, 0, w, 18)
        rect.center = (int(self.x), int(cy))
        pygame.draw.ellipse(surf, COIN_DARK, rect.move(0, 2))
        pygame.draw.ellipse(surf, COIN, rect)
        if w > 8:
            pygame.draw.ellipse(surf, COIN_LIGHT, rect.inflate(-w * 0.55, -9))


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

    def draw(self, surf):
        x, y = int(self.x), int(self.y)
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


######################背景######################


def make_cloud(scale):
    """Draw a fluffy cloud from overlapping circles"""
    w, h = int(120 * scale), int(60 * scale)
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    for _ in range(7):
        r = random.randint(int(14 * scale), int(24 * scale))
        x = random.randint(r, w - r)
        y = random.randint(max(r, h // 2 - 5), h - r)
        pygame.draw.circle(surf, (255, 255, 255, 235), (x, y), r)
    return surf


def make_glow(radius, color):
    """A soft glowing ball (sun / moon)"""
    surf = pygame.Surface((radius * 4, radius * 4), pygame.SRCALPHA)
    center = (radius * 2, radius * 2)
    for r, a in ((radius * 2, 25), (int(radius * 1.5), 50), (int(radius * 1.2), 90)):
        pygame.draw.circle(surf, (*color, a), center, r)
    pygame.draw.circle(surf, (*color, 255), center, radius)
    return surf


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

stars = [[random.uniform(0, BG_X), random.uniform(0, BG_Y), random.choice((1, 1, 2)), random.uniform(0, 6)] for _ in range(80)]
sun = make_glow(26, (255, 240, 170))
moon = make_glow(20, (235, 235, 215))
pygame.draw.circle(moon, (200, 200, 185), (36, 34), 4)
pygame.draw.circle(moon, (200, 200, 185), (46, 44), 3)
pygame.draw.circle(moon, (200, 200, 185), (38, 47), 2)
far_hills = [(x, math.sin(x * 0.015) * 25 + math.sin(x * 0.04 + 1) * 10) for x in range(0, BG_X + 21, 20)]
near_hills = [(x, math.sin(x * 0.02 + 2) * 18 + math.sin(x * 0.055) * 8) for x in range(0, BG_X + 21, 20)]


def draw_background(height):
    """Sky that changes with height, sun and moon, stars, hills and clouds"""
    top, bottom = sky_colors(height)
    gradient = pygame.Surface((1, 2), 0, 32)
    gradient.set_at((0, 0), top)
    gradient.set_at((0, 1), bottom)
    world.blit(pygame.transform.smoothscale(gradient, (BG_X, BG_Y)), (0, 0))

    # Sun (sets as you climb) and moon (rises at night)
    sun_alpha = 1 - clamp((height - 900) / 700)
    if sun_alpha > 0:
        sun.set_alpha(int(255 * sun_alpha))
        world.blit(sun, sun.get_rect(center=(310, 110 + scroll * 0.02)))
    moon_alpha = clamp((height - 1600) / 500)
    if moon_alpha > 0:
        moon.set_alpha(int(255 * moon_alpha))
        world.blit(moon, moon.get_rect(center=(90, 120)))

    # Stars fade in at night and twinkle
    star_alpha = clamp((height - 1300) / 900)
    if star_alpha > 0:
        for s in stars:
            y = (s[1] + scroll * 0.05) % BG_Y
            twinkle = 0.6 + 0.4 * math.sin(ticks * 0.05 + s[3])
            bg = mix(top, bottom, y / BG_Y)
            pygame.draw.circle(world, mix(bg, WHITE, star_alpha * twinkle), (int(s[0]), int(y)), s[2])

    # Hills at the start, they slide away as you climb
    for shape, base, speed, color in (
        (far_hills, BG_Y - 150, 0.15, mix(bottom, (70, 130, 120), 0.6)),
        (near_hills, BG_Y - 85, 0.3, mix(bottom, (70, 165, 85), 0.85)),
    ):
        y0 = base + scroll * speed
        if y0 - 40 < BG_Y:
            points = [(x, y0 + dy) for x, dy in shape] + [(BG_X, BG_Y), (0, BG_Y)]
            pygame.draw.polygon(world, color, points)

    # Clouds drift sideways and fade out high up
    cloud_alpha = 1 - clamp((height - 1300) / 800)
    for c in clouds:
        c["x"] += c["speed"]
        if c["x"] > BG_X + 20:
            c["x"] = -c["surf"].get_width() - 20
        if cloud_alpha > 0:
            y = (c["y"] + scroll * c["depth"]) % (BG_Y + 200) - 100
            c["surf"].set_alpha(int(220 * cloud_alpha))
            world.blit(c["surf"], (c["x"], y))


######################遊戲流程函式######################


def difficulty():
    """0.0 at the start, grows to 1.0 at 2500 m"""
    return clamp(height() / 2500)


def height():
    """Climbed height in meters"""
    return int(climb // 10)


def score():
    return height() + bonus


def burst(x, y, colors, count, speed=3.0, size=4, life=30, gravity=0.15, up=False):
    """Spray particles from a point"""
    for _ in range(count):
        angle = random.uniform(math.pi, math.tau) if up else random.uniform(0, math.tau)
        sp = random.uniform(0.4, 1.0) * speed
        particles.append(Particle(x, y, math.cos(angle) * sp, math.sin(angle) * sp,
                                  random.choice(colors), random.uniform(size * 0.6, size),
                                  random.randint(life // 2, life), gravity))


def add_platform_row():
    """
    Add one solid platform above the highest one (plus maybe coins, traps, monsters) \n
    Gaps always stay smaller than the max jump height, so the game is always possible \n
    """
    global top_y, rows_since_monster
    level = difficulty()
    gap = random.randint(int(55 + level * 25), int(80 + level * 45))
    top_y -= gap
    rows_since_monster += 1

    width = int(PLATFORM_W * (1 - 0.2 * level))  # Platforms get smaller as you climb
    kind = "moving" if random.random() < 0.08 + 0.35 * level else "normal"
    platform = Platform(random.randint(0, BG_X - width), top_y, kind, width)
    if kind == "normal" and random.random() < 0.07:
        platform.add_spring()
    platforms.append(platform)

    # Coins: one above the platform, or sometimes a little arc of three
    roll = random.random()
    cx = clamp(platform.rect.centerx, 30, BG_X - 30)
    if roll < 0.15:
        coins.append(Coin(cx, top_y - 30))
    elif roll < 0.21:
        for i in (-1, 0, 1):
            coins.append(Coin(cx + i * 24, top_y - 32 - (1 - abs(i)) * 10))

    # Fake breaking platform between rows as a trap
    if random.random() < 0.08 + 0.3 * level:
        platforms.append(Platform(random.randint(0, BG_X - PLATFORM_W), top_y + gap // 2, "break"))

    # Monsters appear after 250 m
    if height() > 250 and rows_since_monster > 6 and random.random() < 0.05 + 0.08 * level:
        monsters.append(Monster(random.randint(0, BG_X - Monster.W), top_y + gap // 2 - 20))
        rows_since_monster = 0


def reset_game():
    """Put everything back to the start"""
    global player, platforms, coins, monsters, particles, popups
    global top_y, climb, bonus, scroll, next_milestone, shake, rows_since_monster, new_best
    player = Player((BG_X - Player.W) // 2, BG_Y - 140)
    platforms, coins, monsters, particles, popups = [], [], [], [], []
    climb = 0
    bonus = 0
    scroll = 0
    shake = 0.0
    next_milestone = 500
    rows_since_monster = 0
    new_best = False

    # Wide grassy ground so the first jump is easy
    ground = Platform(0, BG_Y - 30, "normal", BG_X)
    platforms.append(ground)
    top_y = ground.rect.top
    while top_y > -50:  # Fill the screen with platforms
        add_platform_row()


def update_camera():
    """
    When the player goes above the camera line, move the world down instead \n
    Moves are whole pixels so platforms and the player never drift apart \n
    """
    global top_y, climb, scroll
    if player.y < CAMERA_LINE:
        move = math.ceil(CAMERA_LINE - player.y)
        player.y += move
        player.trail = [(tx, ty + move) for tx, ty in player.trail]
        climb += move
        scroll += move
        top_y += move
        for p in platforms:
            p.rect.y += move
        for c in coins:
            c.y += move
        for m in monsters:
            m.base_y += move
        for p in particles:
            p.y += move
        for t in popups:
            if t.in_world:
                t.y += move
        while top_y > -50:
            add_platform_row()


def cleanup():
    """Remove things that left the screen (build new lists instead of removing while looping)"""
    global platforms, coins, monsters, particles, popups
    platforms = [p for p in platforms if p.rect.top < BG_Y + 20]
    coins = [c for c in coins if c.y < BG_Y + 30]
    monsters = [m for m in monsters if m.base_y < BG_Y + 50]
    particles = [p for p in particles if p.life > 0]
    popups = [t for t in popups if t.life > 0]


def game_over():
    global state, high_score, new_best, shake
    state = "over"
    shake = 10
    play("fall")
    if score() > high_score:
        high_score = score()
        new_best = True
        save_high_score(high_score)


def play_step():
    """One frame of gameplay"""
    global bonus, shake, state, next_milestone

    keys = pygame.key.get_pressed()
    direction = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
    player.handle_input(direction)

    landed = player.update(platforms)
    if landed:
        feet = (player.x + Player.W / 2, landed.rect.top)
        if landed.kind == "break":
            landed.broken = True  # Crumbles: no bounce!
            play("break")
            burst(*feet, [WOOD, WOOD_DARK], 14, speed=3, size=4, life=35, gravity=0.3)
            shake = max(shake, 4)
        elif landed.has_spring and landed.spring_rect().inflate(16, 0).collidepoint(feet[0], landed.spring_rect().centery):
            player.bounce(landed.rect.top, SPRING_POWER)
            landed.spring_t = 20
            play("spring")
            burst(*feet, [SPRING_COLOR, WHITE], 18, speed=4, size=4, life=30, up=True)
        else:
            player.bounce(landed.rect.top, JUMP_POWER)
            play("jump")
            dust = GRASS_LIGHT if landed.kind == "normal" else METAL_LIGHT
            burst(*feet, [dust, WHITE], 6, speed=2, size=3, life=18, gravity=0.05, up=True)

    # Collect coins
    player_rect = player.rect
    for coin in coins[:]:
        if player_rect.colliderect(coin.rect):
            coins.remove(coin)
            bonus += 25
            play("coin")
            burst(coin.x, coin.y, [COIN, COIN_LIGHT, WHITE], 10, speed=3, size=3, life=25, gravity=0.05)
            popups.append(FloatText(coin.x, coin.y - 10, "+25", COIN_LIGHT, font_small))

    # Monsters: stomp from above, or get hit
    for m in monsters:
        if m.dead or not player_rect.colliderect(m.rect):
            continue
        if player.vy > 0 and player_rect.bottom - player.vy <= m.rect.top + 12:
            m.dead = True
            m.vy = -3
            player.bounce(m.rect.top, STOMP_POWER)
            bonus += 100
            play("stomp")
            shake = max(shake, 5)
            burst(m.x + m.W / 2, m.y + m.H / 2, [MONSTER, MONSTER_DARK, WHITE], 18, speed=4, size=5, life=30)
            popups.append(FloatText(m.x + m.W / 2, m.y - 10, "+100", (255, 160, 255), font_mid))
        else:
            player.dead = True
            player.vy = -7
            player.vx = 0
            state = "dying"
            play("hurt")
            shake = 9
            burst(player.x + Player.W / 2, player.y + Player.H / 2, [PLAYER_COLOR, WHITE], 16, speed=4)
            return

    update_camera()

    # Milestone message every 500 m
    if height() >= next_milestone:
        popups.append(FloatText(BG_X // 2, 170, f"{next_milestone} m!", COIN_LIGHT, font_big, life=90, speed=0.5, in_world=False))
        play("milestone")
        next_milestone += 500

    if player.y > BG_Y:  # Fell off the bottom
        game_over()


def update_world():
    """Things that keep moving in every state (platforms, coins, particles...)"""
    global shake
    for p in platforms:
        p.update()
    for c in coins:
        c.update()
    for m in monsters:
        m.update()
    for p in particles:
        p.update()
    for t in popups:
        t.update()
    shake *= 0.85
    cleanup()


######################畫面函式######################

# Small sample objects for the instructions on the start screen
legend = [
    (Platform(0, 0, "normal", 44), "Normal"),
    (Platform(0, 0, "moving", 44), "Slides side to side"),
    (Platform(0, 0, "break", 44), "Breaks, no bounce!"),
    (Platform(0, 0, "normal", 44), "Spring = super jump"),
]
legend[3][0].add_spring()
legend[3][0].spring_x = 14
legend_coin = Coin(0, 0)
legend_monster = Monster(0, 0)


def draw_hud():
    draw_text(screen, str(score()), font_big, (14, 6), anchor="topleft", outline=(30, 30, 60))
    draw_text(screen, f"{height()} m", font_small, (16, 50), anchor="topleft")
    draw_text(screen, f"BEST {high_score}", font_small, (BG_X - 14, 12), anchor="topright")


def draw_start_screen():
    bob = math.sin(ticks * 0.05) * 6
    draw_text(screen, "SKY HOPPER", font_title, (BG_X // 2, 85 + bob), COIN_LIGHT, outline=(60, 30, 90))
    draw_text(screen, "Climb as high as you can!", font_small, (BG_X // 2, 135))

    box = pygame.Rect(40, 155, BG_X - 80, 250)
    draw_panel(screen, box)
    y = box.top + 26
    for sample, label in legend:
        sample.rect.topleft = (box.left + 24, y)
        sample.draw(screen)
        draw_text(screen, label, font_small, (box.left + 88, y + 5), anchor="midleft", shadow=False)
        y += 36
    legend_coin.x, legend_coin.y = box.left + 46, y + 4
    legend_coin.update()
    legend_coin.draw(screen)
    draw_text(screen, "Coin = +25 points", font_small, (box.left + 88, y + 5), anchor="midleft", shadow=False)
    y += 40
    legend_monster.x, legend_monster.base_y = box.left + 26, y - 12
    legend_monster.update()
    legend_monster.x = box.left + 26  # Keep it still in the menu
    legend_monster.draw(screen)
    draw_text(screen, "Stomp it, don't touch it!", font_small, (box.left + 88, y + 5), anchor="midleft", shadow=False)

    draw_text(screen, "Arrows / A D to move  -  P to pause", font_small, (BG_X // 2, box.bottom + 18))
    if (ticks // 30) % 2 == 0:
        draw_text(screen, "Press SPACE to start", font_mid, (BG_X // 2, box.bottom + 50), WHITE, outline=(30, 30, 60))


def draw_game_over():
    box = pygame.Rect(45, 150, BG_X - 90, 290)
    draw_panel(screen, box, 175)
    draw_text(screen, "GAME OVER", font_big, (BG_X // 2, box.top + 42), (255, 120, 120), outline=(60, 20, 30))
    draw_text(screen, str(score()), font_title, (BG_X // 2, box.top + 110), WHITE, outline=(30, 30, 60))
    draw_text(screen, f"Height {height()} m   Bonus +{bonus}", font_small, (BG_X // 2, box.top + 158))
    if new_best:
        pulse = 1 + 0.08 * math.sin(ticks * 0.15)
        img = font_mid.render("NEW BEST!", True, COIN_LIGHT)
        img = pygame.transform.rotozoom(img, 0, pulse)
        screen.blit(img, img.get_rect(center=(BG_X // 2, box.top + 198)))
    else:
        draw_text(screen, f"Best {high_score}", font_mid, (BG_X // 2, box.top + 198))
    if (ticks // 30) % 2 == 0:
        draw_text(screen, "SPACE to play again", font_mid, (BG_X // 2, box.top + 250))


def draw_pause():
    dim = pygame.Surface((BG_X, BG_Y), pygame.SRCALPHA)
    dim.fill((0, 0, 20, 140))
    screen.blit(dim, (0, 0))
    draw_text(screen, "PAUSED", font_title, (BG_X // 2, BG_Y // 2 - 20), WHITE, outline=(30, 30, 60))
    draw_text(screen, "Press P to keep playing", font_mid, (BG_X // 2, BG_Y // 2 + 35))


def draw_frame():
    # Everything in the game world goes on the "world" surface
    draw_background(height())
    for p in platforms:
        p.draw(world)
    for c in coins:
        c.draw(world)
    for m in monsters:
        m.draw(world)
    for p in particles:
        p.draw(world)
    player.draw(world)
    for t in popups:
        if t.in_world:
            t.draw(world)

    # Shake the world when something big happens
    offset = (0, 0)
    if shake > 0.5:
        offset = (random.uniform(-shake, shake), random.uniform(-shake, shake))
    screen.fill(BLACK)
    screen.blit(world, offset)

    # Text and menus on top
    for t in popups:
        if not t.in_world:
            t.draw(screen)
    if state == "start":
        draw_start_screen()
    else:
        draw_hud()
    if state == "over":
        draw_game_over()
    elif state == "paused":
        draw_pause()


######################主程式######################

high_score = load_high_score()
state = "start"  # "start", "play", "paused", "dying" or "over"
ticks = 0
reset_game()

while True:
    FPS.tick(60)  # Cap framerate at 60
    ticks += 1

    # Handle events
    for event in pygame.event.get():
        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
            pygame.quit()
            sys.exit()
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_SPACE, pygame.K_RETURN) and state in ("start", "over"):
                reset_game()
                state = "play"
            elif event.key == pygame.K_p and state in ("play", "paused"):
                state = "paused" if state == "play" else "play"

    if state == "play":
        play_step()
        update_world()
    elif state == "dying":
        player.update(platforms)  # Falls through everything
        update_world()
        if player.y > BG_Y:
            game_over()
    elif state == "start":
        # Demo: the player happily bounces on the ground behind the menu
        landed = player.update(platforms)
        if landed:
            player.bounce(landed.rect.top, -8)  # Small hops so it stays under the menu
        update_world()
    elif state == "over":
        update_world()

    draw_frame()
    pygame.display.update()  # Update the display
