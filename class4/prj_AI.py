
######################載入套件/ import packages######################

import pygame
import sys
import os
import random
import io
import math
import wave
from array import array

######################遊戲常數/ game constants######################

bg_x = 800
bg_y = 600
hud_h = 44  # Height of the top info bar

bricks_col = 11
brick_w = 58
brick_h = 18
bricks_gap = 2
bricks_x0 = (bg_x - (bricks_col * (brick_w + bricks_gap) - bricks_gap)) // 2  # Center the grid
bricks_y0 = hud_h + 30

max_lives = 5
max_balls = 8
shield_y = bg_y - 14  # Where the shield barrier sits

GAME_DIR = os.path.dirname(os.path.abspath(__file__))
LEADERBOARD_FILE = os.path.join(GAME_DIR, "leaderboard.txt")
OLD_HIGH_SCORE_FILE = os.path.join(GAME_DIR, "highscore.txt")
SETTINGS_FILE = os.path.join(GAME_DIR, "settings.txt")
STATS_FILE = os.path.join(GAME_DIR, "stats.txt")

# Saved settings (numbers only, 0/1 for on/off)
default_settings = {"volume": 8, "muted": 0, "difficulty": "normal", "shake": 1, "fps": 0}
# Lifetime stats (play_time is in frames)
default_stats = {"games": 0, "bricks": 0, "bosses": 0, "powerups": 0, "best_combo": 0, "best_level": 1, "play_time": 0}

# Difficulty: name shown, starting lives, ball speed multiplier, description
DIFFICULTIES = {
    "easy": ("Easy", 5, 0.85, "5 lives, slower ball"),
    "normal": ("Normal", 3, 1.0, "3 lives, normal speed"),
    "hard": ("Hard", 2, 1.15, "2 lives, faster ball"),
}

brick_colors = [
    (255, 95, 109),
    (255, 160, 80),
    (255, 210, 80),
    (100, 220, 150),
    (80, 190, 235),
    (125, 140, 255),
    (190, 115, 245),
    (245, 120, 205),
    (120, 210, 205),
]

tough_colors = {3: (110, 122, 170), 2: (150, 162, 205), 1: (190, 200, 235)}

brick_points = {"normal": 10, "tough": 25, "explosive": 30, "spawn": 20}

# Level maps: 1 = normal, 2/3 = tough (hits needed), X = explosive,
# S = spawner (adds a brick), U = steel (unbreakable), m = moving brick, . = empty
# The last value says whether the level has a boss
LEVELS = [
    ("Warm Up", [
        "11111111111",
        "11111111111",
        "111X111X111",
        "11111111111",
        "1111S1S1111",
        "11111111111",
    ], False),
    ("Pyramid", [
        ".....2.....",
        "....121....",
        "...11X11...",
        "..1121211..",
        ".11S111S11.",
        "21111X11112",
    ], False),
    ("Fortress", [
        "33333333333",
        "2.........2",
        "2.1X111X1.2",
        "2.1111111.2",
        "2.11S1S11.2",
        "2UUUU.UUUU2",
    ], False),
    ("BOSS: Block King", [
        "...........",
        "...........",
        "...........",
        "...........",
        "..2.2.2.2..",
        "U.1.1X1.1.U",
    ], True),
    ("Checkers", [
        "21212121212",
        "1X1X1X1X1X1",
        "21212121212",
        "...........",
        "U.U.U.U.U.U",
        "1S1.111.1S1",
    ], False),
    ("Conveyor", [
        "22222222222",
        "...........",
        "m...m...m..",
        "..m...m...m",
        "...........",
        "1X1S1X1S1X1",
    ], False),
    ("Diamond", [
        ".....3.....",
        "....323....",
        "...32X23...",
        "..321X123..",
        "...32X23...",
        "....323....",
        ".....3.....",
    ], False),
    ("BOSS: Block King Returns", [
        "...........",
        "...........",
        "...........",
        "...........",
        "2.2.2.2.2.2",
        ".X.3...3.X.",
        "m...m...m..",
    ], True),
]

# Power-ups: label, color, drop weight
POWERUPS = {
    "wide": ("W", (80, 190, 235), 3),
    "multi": ("M", (190, 115, 245), 3),
    "slow": ("S", (100, 220, 150), 2),
    "fire": ("F", (255, 140, 60), 2),
    "laser": ("L", (255, 70, 70), 2),
    "catch": ("C", (255, 210, 80), 2),
    "shield": ("=", (120, 210, 205), 2),
    "life": ("+", (245, 120, 205), 1),
    "shrink": ("-", (130, 130, 150), 2),  # Bad one - avoid it!
}
POWERUP_NAMES = {
    "wide": "WIDE PADDLE", "multi": "MULTI-BALL", "slow": "SLOW BALL", "fire": "FIREBALL",
    "laser": "LASERS", "catch": "CATCH", "shield": "SHIELD", "life": "EXTRA LIFE", "shrink": "SHRINK!",
}
EFFECT_DURATIONS = {"wide": 600, "slow": 480, "fire": 420, "laser": 480, "catch": 600, "shrink": 480}  # In frames (60 per second)
powerup_drop_chance = 0.17

# Keys that work on menu screens
MENU_KEYS = (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s, pygame.K_LEFT, pygame.K_a,
             pygame.K_RIGHT, pygame.K_d, pygame.K_SPACE, pygame.K_RETURN)

######################繪圖工具/ graphics helpers######################

_surface_cache = {}


def cached(key, build):
    """
    Build a surface once and reuse it (drawing gradients every frame is slow)
    """
    if key not in _surface_cache:
        if len(_surface_cache) > 1500:
            _surface_cache.clear()
        _surface_cache[key] = build()
    return _surface_cache[key]


def lighten(color, amount):
    return tuple(int(c + (255 - c) * amount) for c in color)


def darken(color, factor):
    return tuple(int(c * factor) for c in color)


def mix(a, b, t):
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))


def get_glow(radius, color):
    """
    Soft round light on black. Blit it with BLEND_ADD so it brightens what's under it
    """
    def build():
        surf = pygame.Surface((radius * 2, radius * 2))
        for r in range(radius, 0, -1):
            pygame.draw.circle(surf, darken(color, (1 - r / radius) ** 2), (radius, radius), r)
        return surf
    return cached(("glow", radius, color), build)


def add_glow(surface, center, radius, color):
    """Add a round glow centered on a point"""
    radius = max(2, int(radius))
    surface.blit(get_glow(radius, color), (int(center[0]) - radius, int(center[1]) - radius), special_flags=pygame.BLEND_ADD)


def add_wide_glow(surface, rect, pad, color):
    """Add a glow stretched around a rectangle"""
    w = (rect.width + pad * 2) // 8 * 8 + 8  # Rounded so the cache stays small
    h = rect.height + pad * 2
    glow = cached(("wide_glow", w, h, color), lambda: pygame.transform.smoothscale(get_glow(32, color), (w, h)))
    surface.blit(glow, glow.get_rect(center=rect.center), special_flags=pygame.BLEND_ADD)


def get_block(w, h, color, radius):
    """
    Glossy rounded block with a gradient (bricks, paddle, capsules)
    """
    def build():
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        top = lighten(color, 0.3)
        bottom = darken(color, 0.62)
        for y in range(h):
            pygame.draw.line(surf, mix(top, bottom, y / max(1, h - 1)), (0, y), (w, y))
        shine = pygame.Surface((max(1, w - 4), max(1, h // 2 - 1)), pygame.SRCALPHA)
        shine.fill((255, 255, 255, 50))
        surf.blit(shine, (2, 2))
        # Cut off the corners to make it rounded
        mask = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=radius)
        surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        pygame.draw.rect(surf, darken(color, 0.4), surf.get_rect(), width=1, border_radius=radius)
        if w > radius * 2 + 2:
            pygame.draw.line(surf, lighten(color, 0.65), (radius, 1), (w - radius - 1, 1))
        return surf
    return cached(("block", w, h, color, radius), build)


def get_shadow(w, h, radius):
    def build():
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(surf, (0, 0, 8, 120), surf.get_rect(), border_radius=radius)
        return surf
    return cached(("shadow", w, h, radius), build)


def get_sphere(radius, color):
    """
    A shaded 3D-looking ball with the light coming from the top left
    """
    def build():
        size = radius * 2 + 2
        center = radius + 1
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        dark = darken(color, 0.5)
        light = lighten(color, 0.85)
        for r in range(radius, 0, -1):
            t = 1 - r / radius
            shade = mix(dark, color, t * 2) if t < 0.5 else mix(color, light, (t - 0.5) * 2)
            shift = t * radius * 0.35
            pygame.draw.circle(surf, shade, (center - shift, center - shift), r)
        return surf
    return cached(("sphere", radius, color), build)


def draw_sphere(surface, center, radius, color):
    sprite = get_sphere(radius, color)
    surface.blit(sprite, (int(center[0]) - radius - 1, int(center[1]) - radius - 1))

######################物件類別/ object class######################

class Brick:
    def __init__(self, x, y, color, brick_type="normal", hp=1, move_amp=0, move_phase=0.0):
        """
        Initiaize the brick \n
        x, y: / Top left coordinates \n
        color: / Brick color \n
        brick_type: normal, tough, explosive, spawn or steel \n
        hp: / Hits needed to break it \n
        move_amp: / How far it slides left and right (0 = doesn't move)
        """
        self.rect = pygame.Rect(x, y, brick_w, brick_h)
        self.color = color
        self.brick_type = brick_type
        self.hp = hp
        self.max_hp = hp
        self.hit = False
        self.flash = 0  # Frames of white flash after being hit
        self.home_x = x
        self.move_amp = move_amp
        self.move_phase = move_phase
        self.appear = 30  # Entrance animation progress (30 = in place)

    @property
    def breakable(self):
        return self.brick_type != "steel"

    def take_hit(self):
        """
        Damage the brick \n
        return: True if the brick broke
        """
        self.flash = 6
        if not self.breakable:
            return False
        self.hp -= 1
        if self.hp <= 0:
            self.hit = True
            return True
        return False

    def update(self, level_frame):
        if self.flash > 0:
            self.flash -= 1
        if self.appear < 30:
            self.appear += 1
        if self.move_amp and not self.hit:
            self.rect.x = self.home_x + round(math.sin(level_frame * 0.03 + self.move_phase) * self.move_amp)

    def draw(self, display_area, frame):
        """
        Draw the brick \n
        display_area: / The surface to draw on \n
        frame: / Frame counter for animations
        """
        if self.hit or self.appear <= 0:
            return

        # Bricks drop in from above at the start of a level
        drop = -260 * (1 - self.appear / 30) ** 3
        rect = self.rect.move(0, round(drop))

        color = self.color
        if self.brick_type == "tough":
            color = tough_colors.get(self.hp, self.color)
        if self.flash > 0:
            blend = self.flash / 6
            color = tuple(int(c + (255 - c) * blend) for c in color)

        display_area.blit(get_shadow(rect.width, rect.height, 5), rect.move(2, 4))

        if self.brick_type in ("explosive", "spawn"):
            pulse = 2 + round(1.5 * (1 + math.sin(frame * 0.1 + self.home_x)))  # 2..5
            add_wide_glow(display_area, rect, 14, darken(self.color, pulse / 10))

        display_area.blit(get_block(rect.width, rect.height, color, 5), rect)

        center = rect.center
        if self.brick_type == "explosive":
            pygame.draw.circle(display_area, (255, 245, 210), (center[0], center[1] + 1), 4)
            pygame.draw.line(display_area, (255, 245, 210), (center[0] + 2, center[1] - 6), (center[0] + 5, center[1] - 8), 2)
        elif self.brick_type == "spawn":
            pygame.draw.line(display_area, (235, 255, 235), (center[0] - 4, center[1]), (center[0] + 4, center[1]), 2)
            pygame.draw.line(display_area, (235, 255, 235), (center[0], center[1] - 4), (center[0], center[1] + 4), 2)
        elif self.brick_type == "steel":
            for corner in ((rect.x + 6, rect.y + 6), (rect.right - 7, rect.y + 6),
                           (rect.x + 6, rect.bottom - 7), (rect.right - 7, rect.bottom - 7)):
                pygame.draw.circle(display_area, (170, 175, 195), corner, 2)
        elif self.brick_type == "tough":
            # Dots show hits left, cracks show damage
            for i in range(self.hp):
                pygame.draw.circle(display_area, (40, 45, 80), (center[0] - (self.hp - 1) * 5 + i * 10, center[1]), 2)
            if self.hp < self.max_hp:
                x, y = rect.x, rect.y
                pygame.draw.lines(display_area, (60, 65, 100), False, [(x + 10, y + 2), (x + 16, y + 9), (x + 13, y + 16)], 1)
                if self.hp < self.max_hp - 1:
                    pygame.draw.lines(display_area, (60, 65, 100), False, [(x + 46, y + 3), (x + 40, y + 10), (x + 45, y + 16)], 1)

        if self.move_amp:
            # Little arrows on moving bricks
            cy = center[1]
            pygame.draw.polygon(display_area, (30, 35, 60), [(rect.x + 4, cy), (rect.x + 9, cy - 4), (rect.x + 9, cy + 4)])
            pygame.draw.polygon(display_area, (30, 35, 60), [(rect.right - 4, cy), (rect.right - 9, cy - 4), (rect.right - 9, cy + 4)])


class Boss:
    def __init__(self, level):
        """
        A big moving block with lots of HP that drops bombs \n
        level: / Current level (higher = tougher boss)
        """
        self.rect = pygame.Rect(0, 0, 180, 44)
        self.x = bg_x / 2
        self.base_y = bricks_y0 + 30
        self.max_hp = 20 + 4 * level
        self.hp = self.max_hp
        self.speed = 1.6 + 0.1 * level
        self.level = level
        self.direction = 1
        self.flash = 0
        self.bomb_timer = 150
        self.enter = 0  # Entrance animation (60 = in place)
        self.alive = True
        self.rect.center = (round(self.x), self.base_y - 200)

    def update(self, frame):
        """
        Move the boss \n
        return: True when it wants to drop a bomb
        """
        if self.flash > 0:
            self.flash -= 1
        if self.enter < 60:
            self.enter += 1
            self.rect.centery = round(self.base_y - 200 * (1 - self.enter / 60) ** 3)
            return False

        self.x += self.direction * self.speed
        half = self.rect.width / 2
        if self.x - half < 10:
            self.x = 10 + half
            self.direction = 1
        elif self.x + half > bg_x - 10:
            self.x = bg_x - 10 - half
            self.direction = -1
        self.rect.centerx = round(self.x)
        self.rect.centery = self.base_y + round(6 * math.sin(frame * 0.05))

        self.bomb_timer -= 1
        if self.bomb_timer <= 0:
            self.bomb_timer = random.randint(90, 150) - min(self.level * 3, 50)
            return True
        return False

    def take_hit(self, damage):
        """
        return: True if the boss was defeated
        """
        self.hp -= damage
        self.flash = 6
        if self.hp <= 0:
            self.alive = False
            return True
        return False

    def draw(self, display_area, target_x):
        """
        Draw the boss (its eyes follow target_x)
        """
        if not self.alive:
            return
        anger = round((1 - self.hp / self.max_hp) * 8) / 8  # Rounded so the cache stays small
        color = (int(190 + 65 * anger), int(115 - 45 * anger), int(245 - 175 * anger))  # Purple -> red as it gets hurt
        if self.flash > 0:
            color = lighten(color, self.flash / 6)

        add_wide_glow(display_area, self.rect, 30, darken(color, 0.55))
        display_area.blit(get_shadow(self.rect.width, self.rect.height, 12), self.rect.move(3, 6))
        display_area.blit(get_block(self.rect.width, self.rect.height, color, 12), self.rect)
        pygame.draw.rect(display_area, lighten(color, 0.6), self.rect, width=2, border_radius=12)

        cx, cy = self.rect.center
        for side in (-1, 1):
            eye = (cx + side * 40, cy - 3)
            draw_sphere(display_area, eye, 10, (235, 235, 245))
            look = max(-4, min(4, (target_x - eye[0]) / 40))
            pupil = (int(eye[0] + look), eye[1] + 2)
            add_glow(display_area, pupil, 9, (90, 20, 20))
            pygame.draw.circle(display_area, (20, 20, 35), pupil, 4)
            pygame.draw.circle(display_area, (255, 255, 255), (pupil[0] - 1, pupil[1] - 2), 1)
            # Angry eyebrows
            pygame.draw.line(display_area, (30, 20, 40), (eye[0] - side * 12, eye[1] - 14), (eye[0] + side * 8, eye[1] - 9), 4)
        mouth = [(cx - 22, cy + 13), (cx - 11, cy + 9), (cx, cy + 13), (cx + 11, cy + 9), (cx + 22, cy + 13)]
        pygame.draw.lines(display_area, (30, 20, 40), False, mouth, 3)

        # HP bar
        bar_back = pygame.Rect(self.rect.x, self.rect.y - 16, self.rect.width, 8)
        display_area.blit(get_block(bar_back.width, bar_back.height, (40, 40, 60), 4), bar_back)
        bar_w = int(bar_back.width * self.hp / self.max_hp) // 2 * 2
        if bar_w >= 8:
            display_area.blit(get_block(bar_w, bar_back.height, (255, 70, 80), 4), bar_back)


class Bomb:
    def __init__(self, x, y):
        """
        Dropped by the boss - catching one shrinks your paddle!
        """
        self.x = x
        self.y = y
        self.dead = False

    @property
    def rect(self):
        return pygame.Rect(self.x - 7, self.y - 7, 14, 14)

    def update(self):
        self.y += 3.2

    def draw(self, display_area, frame):
        pulse = frame // 6 % 2 == 0
        add_glow(display_area, (self.x, self.y), 20, (150, 20, 35) if pulse else (90, 15, 25))
        draw_sphere(display_area, (self.x, self.y), 8, (220, 40, 60) if pulse else (255, 110, 110))
        pygame.draw.line(display_area, (200, 170, 120), (self.x + 2, self.y - 7), (self.x + 4, self.y - 12), 2)
        add_glow(display_area, (self.x + 4, self.y - 12), 6, (255, 200, 80) if pulse else (200, 120, 40))


class Laser:
    def __init__(self, x, y):
        """
        A laser shot fired from the paddle
        """
        self.rect = pygame.Rect(x - 2, y - 14, 4, 14)
        self.dead = False

    def update(self):
        self.rect.y -= 10
        if self.rect.bottom < hud_h:
            self.dead = True

    def draw(self, display_area):
        add_wide_glow(display_area, self.rect, 8, (200, 40, 40))
        pygame.draw.rect(display_area, (255, 220, 220), self.rect, border_radius=2)


class Paddle:
    def __init__(self):
        """
        Initiaize the paddle (follows the mouse or arrow keys)
        """
        self.base_w = 100
        self.width = float(self.base_w)
        self.target_w = self.base_w  # Width it grows/shrinks toward
        self.rect = pygame.Rect(0, bg_y - 50, self.base_w, 14)
        self.x = bg_x / 2
        self.vel = 0
        self.bump = 0  # Dips down a little when the ball hits it

    def update(self, target_x):
        """
        Move toward target_x and animate the width
        """
        if self.bump > 0:
            self.bump -= 1
        self.width += (self.target_w - self.width) * 0.18
        self.rect.width = round(self.width)
        half = self.rect.width / 2
        new_x = max(half, min(bg_x - half, target_x))
        self.vel = new_x - self.x
        self.x = new_x
        self.rect.centerx = round(self.x)

    def draw(self, display_area, effects):
        """
        Draw the paddle \n
        effects: / Active power-ups (changes the look)
        """
        if "fire" in effects:
            glow_color = (255, 140, 60)
        elif "shrink" in effects:
            glow_color = (130, 130, 150)
        elif "catch" in effects:
            glow_color = (255, 210, 80)
        else:
            glow_color = (80, 190, 235)
        rect = self.rect.move(0, self.bump // 2)
        add_wide_glow(display_area, rect, 18, darken(glow_color, 0.45))
        display_area.blit(get_shadow(rect.width, rect.height, 7), rect.move(2, 5))

        if "laser" in effects:
            # Laser cannons on each end
            for gun_x in (rect.x + 6, rect.right - 10):
                display_area.blit(get_block(4, 10, (255, 70, 70), 2), (gun_x, rect.y - 8))
                add_glow(display_area, (gun_x + 2, rect.y - 8), 6, (160, 30, 30))

        display_area.blit(get_block(rect.width, rect.height, (200, 210, 235), 7), rect)
        cap_w = 14
        cap = get_block(cap_w, rect.height, glow_color, 7)
        display_area.blit(cap, rect.topleft)
        display_area.blit(cap, (rect.right - cap_w, rect.y))
        for cap_x in (rect.x + cap_w // 2, rect.right - cap_w // 2):
            add_glow(display_area, (cap_x, rect.centery), 12, darken(glow_color, 0.5))


class Ball:
    def __init__(self, x, y, speed):
        """
        Initiaize the ball \n
        x, y: / Ball center coordinates \n
        speed: / Ball speed in pixels per frame
        """
        self.x = x
        self.y = y
        self.radius = 9
        self.speed = speed
        self.vx = 0.0
        self.vy = 0.0
        self.stuck = True  # Sitting on the paddle, waiting to launch
        self.stick_offset = 0  # Where on the paddle it's stuck
        self.catch_timer = None  # Frames until a caught ball launches itself
        self.dead = False
        self.fire = False
        self.trail = []

    def set_angle(self, angle):
        """
        Point the ball in a direction \n
        angle: / Radians from straight up (positive = right)
        """
        self.vx = self.speed * math.sin(angle)
        self.vy = -self.speed * math.cos(angle)
        # Never let the ball go too flat or it takes forever to come back
        min_vy = self.speed * 0.3
        if abs(self.vy) < min_vy:
            self.vy = math.copysign(min_vy, self.vy or -1)
            self.vx = math.copysign(math.sqrt(self.speed ** 2 - min_vy ** 2), self.vx)

    def angle(self):
        return math.atan2(self.vx, -self.vy)

    def update_trail(self):
        self.trail.append((self.x, self.y))
        if len(self.trail) > 10:
            self.trail.pop(0)

    def draw(self, display_area):
        """
        Draw the ball with a glow and a trail
        """
        color = (255, 120, 50) if self.fire else (255, 215, 0)
        for i, (tx, ty) in enumerate(self.trail):
            fade = round((i + 1) / (len(self.trail) + 1) * 5) / 5
            add_glow(display_area, (tx, ty), self.radius * (0.6 + fade), darken(color, fade * 0.55))

        add_glow(display_area, (self.x, self.y), self.radius * 4, darken(color, 0.5))
        draw_sphere(display_area, (self.x, self.y), self.radius, color)


class PowerUp:
    def __init__(self, x, y, kind):
        """
        A falling capsule the player can catch \n
        kind: / Key from POWERUPS
        """
        self.kind = kind
        self.rect = pygame.Rect(0, 0, 40, 18)
        self.rect.center = (x, y)
        self.y = float(y)

    def update(self):
        self.y += 2.4
        self.rect.centery = round(self.y)

    def draw(self, display_area, font, frame):
        label, color, _ = POWERUPS[self.kind]
        pulse = 3 + round(1.5 * (1 + math.sin(frame * 0.2)))  # 3..6
        add_wide_glow(display_area, self.rect, 14, darken(color, pulse / 10))
        display_area.blit(get_block(self.rect.width, self.rect.height, color, 9), self.rect)
        pygame.draw.rect(display_area, lighten(color, 0.7), self.rect, width=1, border_radius=9)
        text = font.render(label, True, (20, 24, 45))
        display_area.blit(text, text.get_rect(center=self.rect.center))


class Spark:
    def __init__(self, x, y, color, speed_x, speed_y, lifetime):
        self.x = x
        self.y = y
        self.color = color
        self.speed_x = speed_x
        self.speed_y = speed_y
        self.lifetime = lifetime
        self.max_lifetime = lifetime

    def update(self):
        self.x += self.speed_x
        self.y += self.speed_y
        self.speed_y += 0.12
        self.lifetime -= 1

    def draw(self, display_area):
        fade = math.ceil(self.lifetime / self.max_lifetime * 4) / 4  # Rounded so the cache stays small
        add_glow(display_area, (self.x, self.y), 7, darken(self.color, fade * 0.8))
        pygame.draw.circle(display_area, lighten(darken(self.color, fade), 0.4 * fade), (int(self.x), int(self.y)), 1)


class Debris:
    def __init__(self, x, y, color):
        """
        A chunk of broken brick that falls with gravity
        """
        self.x = x
        self.y = y
        self.w = random.randint(6, 12)
        self.h = random.randint(4, 8)
        self.color = color
        self.speed_x = random.uniform(-2.5, 2.5)
        self.speed_y = random.uniform(-3, 0)
        self.angle = random.uniform(0, math.pi * 2)
        self.spin = random.uniform(-0.3, 0.3)
        self.lifetime = random.randint(30, 50)
        self.max_lifetime = self.lifetime

    def update(self):
        self.x += self.speed_x
        self.y += self.speed_y
        self.speed_y += 0.3
        self.angle += self.spin
        self.lifetime -= 1

    def draw(self, display_area):
        fade = self.lifetime / self.max_lifetime
        cos, sin = math.cos(self.angle), math.sin(self.angle)
        corners = []
        for dx, dy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            px, py = dx * self.w / 2, dy * self.h / 2
            corners.append((self.x + px * cos - py * sin, self.y + px * sin + py * cos))
        pygame.draw.polygon(display_area, darken(self.color, 0.4 + 0.6 * fade), corners)
        pygame.draw.line(display_area, lighten(darken(self.color, fade), 0.4), corners[0], corners[1])


class Shockwave:
    def __init__(self, x, y, color, size=70):
        self.x = x
        self.y = y
        self.color = color
        self.size = size
        self.age = 0
        self.duration = 22

    def update(self):
        self.age += 1

    def draw(self, display_area):
        progress = self.age / self.duration
        radius = int(8 + progress * self.size)
        strength = 1 - progress
        # Bright flash in the middle at the start
        if progress < 0.5:
            add_glow(display_area, (self.x, self.y), (radius + 20) // 4 * 4, darken(self.color, round((0.5 - progress) * 8) / 8 * 1.6))
        # Glowing ring (added on top of the picture, so it lights it up)
        ring = pygame.Surface((radius * 2 + 4, radius * 2 + 4))
        pygame.draw.circle(ring, darken(self.color, strength), (radius + 2, radius + 2), radius, width=max(2, 6 - int(progress * 4)))
        display_area.blit(ring, (self.x - radius - 2, self.y - radius - 2), special_flags=pygame.BLEND_ADD)


class FloatingText:
    def __init__(self, x, y, text, color, font, lifetime=45):
        """
        Text that floats up and fades (for points, power-up names...)
        """
        self.x = x
        self.y = y
        self.surface = font.render(text, True, color)
        self.lifetime = lifetime
        self.max_lifetime = lifetime

    def update(self):
        self.y -= 0.8
        self.lifetime -= 1

    def draw(self, display_area):
        self.surface.set_alpha(int(255 * self.lifetime / self.max_lifetime))
        display_area.blit(self.surface, self.surface.get_rect(center=(int(self.x), int(self.y))))


######################介面元件/ GUI widgets######################

class Button:
    def __init__(self, text, center, size, action, color=(60, 95, 190), font=None):
        """
        A clickable button that lights up when hovered \n
        text: / Label on the button \n
        center: / Center position \n
        size: / (width, height) \n
        action: / Function to call when pressed \n
        font: / Font to use (None = the normal font)
        """
        self.text = text
        self.rect = pygame.Rect(0, 0, size[0], size[1])
        self.rect.center = center
        self.action = action
        self.color = color
        self.font = font
        self.enabled = True
        self.glow = 0.0  # Hover animation (0 = idle, 1 = fully lit)

    def update(self, focused):
        target = 1.0 if focused and self.enabled else 0.0
        self.glow += (target - self.glow) * 0.25

    def press(self, pos=None):
        """
        return: True if something happened
        """
        if not self.enabled:
            return False
        self.action()
        return True

    def adjust(self, step):
        """Left/Right keys - plain buttons don't use them"""
        return False

    def draw_base(self, display_area):
        """
        Draw the glossy block \n
        return: The (slightly grown) rect it was drawn in
        """
        level = round(self.glow * 4) / 4  # Rounded so the cache stays small
        grow = int(level * 4) * 2
        rect = self.rect.inflate(grow, grow // 2)
        if self.enabled:
            color = mix(self.color, lighten(self.color, 0.2), level)
        else:
            color = (42, 46, 66)
        if level > 0:
            add_wide_glow(display_area, rect, 16, darken(self.color, 0.6 * level))
        display_area.blit(get_shadow(rect.width, rect.height, 12), rect.move(0, 4))
        display_area.blit(get_block(rect.width, rect.height, color, 12), rect)
        return rect

    def draw(self, display_area, font, frame):
        rect = self.draw_base(display_area)
        text_color = (255, 255, 255) if self.enabled else (110, 115, 140)
        draw_center_text(display_area, self.text, self.font or font, text_color, rect.centery, x=rect.centerx)


class OptionRow(Button):
    def __init__(self, label, center, size, get_value, change, slider_max=None):
        """
        A settings row: label on the left, value with < > arrows on the right \n
        get_value: / Function returning the value (text, or a number for sliders) \n
        change: / Function taking +1 or -1 \n
        slider_max: / If set, the value is drawn as a bar out of this many steps
        """
        super().__init__(label, center, size, lambda: change(1), (40, 58, 120))
        self.get_value = get_value
        self.change = change
        self.slider_max = slider_max

    def press(self, pos=None):
        # Clicking the left arrow goes down, anywhere else goes up
        if pos and self.rect.right - 230 < pos[0] < self.rect.right - 115:
            self.change(-1)
        else:
            self.change(1)
        return True

    def adjust(self, step):
        self.change(step)
        return True

    def draw(self, display_area, font, frame):
        rect = self.draw_base(display_area)
        shadow = font.render(self.text, True, (5, 6, 15))
        label = font.render(self.text, True, (255, 255, 255))
        display_area.blit(shadow, shadow.get_rect(midleft=(rect.left + 26, rect.centery + 2)))
        display_area.blit(label, label.get_rect(midleft=(rect.left + 24, rect.centery)))

        arrow_color = (255, 215, 0) if self.glow > 0.5 else (140, 155, 200)
        value_x = rect.right - 115
        draw_center_text(display_area, "<", font, arrow_color, rect.centery, x=rect.right - 205)
        draw_center_text(display_area, ">", font, arrow_color, rect.centery, x=rect.right - 25)

        value = self.get_value()
        if self.slider_max:
            # A row of little bars, lit up to the current value
            for i in range(self.slider_max):
                bar = pygame.Rect(0, 0, 11, 8 + i * 1.4)
                bar.midbottom = (value_x - 78 + i * 15 + 6, rect.centery + 10)
                color = mix((100, 220, 150), (255, 210, 80), i / self.slider_max) if i < value else (30, 36, 62)
                pygame.draw.rect(display_area, color, bar, border_radius=2)
        else:
            draw_center_text(display_area, str(value), font, (150, 220, 255), rect.centery, x=value_x)


class LevelCard(Button):
    def __init__(self, level, center, action):
        """
        A level select card with a tiny picture of the level \n
        level: / Level number (1, 2, 3...)
        """
        super().__init__(f"LEVEL {level}", center, (170, 130), action, (45, 62, 125))
        self.level = level

    def draw(self, display_area, font, frame):
        name, _, boss = level_info(self.level)
        self.color = (120, 40, 70) if boss else (45, 62, 125)
        rect = self.draw_base(display_area)
        if not self.enabled:
            draw_center_text(display_area, self.text, font, (110, 115, 140), rect.top + 24, x=rect.centerx)
            draw_center_text(display_area, "?", font_cache(64), (80, 86, 115), rect.centery + 6, x=rect.centerx)
            draw_center_text(display_area, "LOCKED", font_cache(20), (110, 115, 140), rect.bottom - 16, x=rect.centerx)
            return

        draw_center_text(display_area, self.text, font, (255, 255, 255), rect.top + 22, x=rect.centerx)
        draw_center_text(display_area, name.replace("BOSS: ", ""), font_cache(20), (200, 210, 240), rect.top + 44, x=rect.centerx)
        preview = get_level_preview(self.level)
        display_area.blit(preview, preview.get_rect(center=(rect.centerx, rect.centery + 16)))
        if boss:
            tag_color = (255, 95, 109) if frame // 20 % 2 == 0 else (255, 160, 170)
            draw_center_text(display_area, "BOSS", font_cache(20), tag_color, rect.bottom - 14, x=rect.centerx)


class SoundBank:
    def __init__(self):
        """
        Generate all sound effects in code (no sound files needed)
        """
        self.muted = False
        self.volume = 1.0
        self.sounds = {}
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            self.build()
        except pygame.error as error:
            print(f"Sound is unavailable: {error}")

    def build(self):
        noise = random.Random(83)
        square = lambda f, t: 1 if math.sin(2 * math.pi * f * t) > 0 else -1
        self.sounds["bounce"] = make_sound(0.05, lambda t, d: math.sin(2 * math.pi * 660 * t) * fade(t, d), 0.25)
        self.sounds["launch"] = make_sound(0.09, lambda t, d: sweep(t, d, 300, 800) * fade(t, d), 0.25)
        # Brick sounds rise in pitch as your combo grows
        for k in range(8):
            freq = 523.25 * 2 ** (k * 2 / 12)
            self.sounds[f"brick{k}"] = make_sound(
                0.09,
                lambda t, d, f=freq: (math.sin(2 * math.pi * f * t) + 0.3 * math.sin(4 * math.pi * f * t)) * fade(t, d),
                0.25,
            )
        self.sounds["tough"] = make_sound(0.06, lambda t, d: square(330, t) * 0.5 * fade(t, d), 0.18)
        self.sounds["boss_hit"] = make_sound(0.08, lambda t, d: square(160, t) * 0.6 * fade(t, d), 0.22)
        self.sounds["steel"] = make_sound(
            0.16,
            lambda t, d: (math.sin(2 * math.pi * 1250 * t) + 0.7 * math.sin(2 * math.pi * 1870 * t)) * (1 - t / d) ** 3,
            0.18,
        )
        self.sounds["explode"] = make_sound(
            0.38,
            lambda t, d: (math.sin(2 * math.pi * (75 - 35 * t) * t) * 0.7 + noise.uniform(-1, 1) * 0.3) * fade(t, d),
            0.7,
        )
        self.sounds["laser"] = make_sound(0.07, lambda t, d: sweep(t, d, 1600, 500) * fade(t, d), 0.1)
        self.sounds["bomb"] = make_sound(0.12, lambda t, d: sweep(t, d, 300, 140) * fade(t, d), 0.2)
        self.sounds["powerup"] = make_sound(0.24, lambda t, d: sweep(t, d, 400, 1400) * (1 - t / d), 0.25)
        self.sounds["bad"] = make_sound(0.3, lambda t, d: square(sweep_freq(t, d, 300, 90), t) * 0.4 * (1 - t / d), 0.2)
        self.sounds["lose"] = make_sound(0.55, lambda t, d: sweep(t, d, 520, 110) * (1 - t / d), 0.3)
        notes = [523.25, 659.25, 783.99, 1046.5]
        self.sounds["clear"] = make_sound(
            0.6,
            lambda t, d: math.sin(2 * math.pi * notes[min(int(t / 0.12), 3)] * t) * (1 - t / d),
            0.25,
        )
        self.sounds["type"] = make_sound(0.03, lambda t, d: math.sin(2 * math.pi * 900 * t) * fade(t, d), 0.15)
        self.sounds["click"] = make_sound(0.06, lambda t, d: sweep(t, d, 700, 1300) * fade(t, d), 0.2)

    def play(self, name):
        if not self.muted and name in self.sounds:
            self.sounds[name].set_volume(self.volume)
            self.sounds[name].play()

######################定義函式區/ define functions######################

def fade(t, duration):
    """Volume envelope that fades out quickly"""
    return (1 - t / duration) ** 2


def sweep(t, duration, f0, f1):
    """Sine wave that slides from frequency f0 to f1"""
    return math.sin(2 * math.pi * (f0 * t + (f1 - f0) * t * t / (2 * duration)))


def sweep_freq(t, duration, f0, f1):
    """Frequency partway through a slide (for square-wave sweeps)"""
    return f0 + (f1 - f0) * t / duration


def make_sound(duration, wave_func, volume):
    """
    Turn a wave function into a pygame Sound \n
    wave_func(t, duration): / Returns a value between -1 and 1
    """
    sample_rate = 22050
    samples = array("h")
    for index in range(int(sample_rate * duration)):
        t = index / sample_rate
        value = max(-1.0, min(1.0, wave_func(t, duration)))
        samples.append(int(value * volume * 32767))

    sound_file = io.BytesIO()
    with wave.open(sound_file, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(samples.tobytes())
    sound_file.seek(0)
    return pygame.mixer.Sound(file=sound_file)


def circle_hits_rect(cx, cy, radius, rect):
    """
    Check if a circle overlaps a rectangle
    """
    nearest_x = max(rect.left, min(cx, rect.right))
    nearest_y = max(rect.top, min(cy, rect.bottom))
    return (cx - nearest_x) ** 2 + (cy - nearest_y) ** 2 < radius * radius


def bounce_off_rect(ball, rect):
    """
    Bounce the ball off whichever side of the rectangle it hit
    """
    r = ball.radius
    overlap_x = min(ball.x + r - rect.left, rect.right - (ball.x - r))
    overlap_y = min(ball.y + r - rect.top, rect.bottom - (ball.y - r))
    if overlap_x < overlap_y:
        if ball.x < rect.centerx:
            ball.vx = -abs(ball.vx)
            ball.x = rect.left - r
        else:
            ball.vx = abs(ball.vx)
            ball.x = rect.right + r
    else:
        if ball.y < rect.centery:
            ball.vy = -abs(ball.vy)
            ball.y = rect.top - r
        else:
            ball.vy = abs(ball.vy)
            ball.y = rect.bottom + r


def level_info(level):
    """
    return: (name, layout, has_boss) for a level number (levels loop forever)
    """
    return LEVELS[(level - 1) % len(LEVELS)]


def build_level(level):
    """
    Build the brick list for a level number (levels loop and get harder) \n
    return: Brick list
    """
    _, layout, _ = level_info(level)
    new_bricks = []
    for row, line in enumerate(layout):
        for col, char in enumerate(line):
            if char == ".":
                continue
            x = bricks_x0 + col * (brick_w + bricks_gap)
            y = bricks_y0 + row * (brick_h + bricks_gap)
            color = brick_colors[row % len(brick_colors)]
            if char in "23":
                brick = Brick(x, y, color, "tough", int(char))
            elif char == "X":
                brick = Brick(x, y, (255, 80, 40), "explosive")
            elif char == "S":
                brick = Brick(x, y, (60, 220, 100), "spawn")
            elif char == "U":
                brick = Brick(x, y, (105, 110, 128), "steel")
            elif char == "m":
                brick = Brick(x, y, color, move_amp=60, move_phase=math.pi * (row % 2))
            else:
                brick = Brick(x, y, color)
            brick.appear = -(row * 4 + col * 2)  # Stagger the drop-in animation
            new_bricks.append(brick)

    # After every level has been beaten once, some normal bricks become tough
    loop = (level - 1) // len(LEVELS)
    for brick in new_bricks:
        if loop > 0 and brick.brick_type == "normal" and random.random() < 0.15 * loop:
            brick.brick_type = "tough"
            brick.hp = brick.max_hp = min(3, 1 + loop)
    return new_bricks


def create_background(width, height, seed=0, boss=False):
    """
    Create a deep space background with glowing nebula clouds \n
    seed: / Different seeds give different clouds \n
    boss: / Boss levels get angry red clouds
    """
    background = pygame.Surface((width, height))
    for y in range(height):
        pygame.draw.line(background, mix((5, 6, 18), (14, 12, 36), y / height), (0, y), (width, y))

    # Nebula: work out the colors on a tiny image, then blow it up so it's soft and blurry
    rng = random.Random(seed)
    if boss:
        palette = [(150, 25, 50), (110, 25, 120), (170, 60, 30)]
    else:
        palette = [(100, 45, 160), (35, 75, 180), (20, 125, 140), (150, 45, 110), (55, 40, 150)]
    small_w, small_h = 160, 120
    blobs = [(rng.uniform(0, small_w), rng.uniform(0, small_h), rng.uniform(22, 55), rng.choice(palette), rng.uniform(0.25, 0.5))
             for _ in range(6)]
    phase = rng.uniform(0, 10)
    nebula = pygame.Surface((small_w, small_h))
    for y in range(small_h):
        for x in range(small_w):
            # Wavy pattern so the clouds look wispy, not like perfect circles
            wisp = 0.55 + 0.25 * math.sin(x * 0.13 + phase) * math.sin(y * 0.11 - phase) + 0.2 * math.sin((x + y) * 0.05 + phase)
            r = g = b = 0.0
            for bx, by, size, color, strength in blobs:
                d2 = ((x - bx) ** 2 + (y - by) ** 2) / (size * size)
                if d2 < 4:
                    k = math.exp(-d2 * 1.5) * strength * wisp
                    r += color[0] * k
                    g += color[1] * k
                    b += color[2] * k
            nebula.set_at((x, y), (min(255, int(r)), min(255, int(g)), min(255, int(b))))
    background.blit(pygame.transform.smoothscale(nebula, (width, height)), (0, 0), special_flags=pygame.BLEND_ADD)

    # Faint grid
    grid = pygame.Surface((width, height))
    for x in range(24, width, 40):
        pygame.draw.line(grid, (8, 12, 26), (x, 0), (x, height), 1)
    for y in range(24, height, 40):
        pygame.draw.line(grid, (8, 12, 26), (0, y), (width, y), 1)
    background.blit(grid, (0, 0), special_flags=pygame.BLEND_ADD)

    # Distant stars that don't move
    for _ in range(120):
        shade = rng.randrange(30, 90)
        background.set_at((rng.randrange(width), rng.randrange(height)), (shade, shade, shade + 20))

    return background


def create_vignette(width, height):
    """
    Darkens the edges of the screen so your eye goes to the middle
    """
    small = pygame.Surface((80, 60), pygame.SRCALPHA)
    for y in range(60):
        for x in range(80):
            dx = (x - 39.5) / 40
            dy = (y - 29.5) / 30
            distance = math.sqrt(dx * dx + dy * dy)
            alpha = max(0.0, min(1.0, (distance - 0.6) / 0.7)) ** 1.5 * 190
            small.set_at((x, y), (0, 0, 0, int(alpha)))
    return pygame.transform.smoothscale(small, (width, height))


def load_leaderboard():
    """
    return: Top 5 list of (name, score, level), best first
    """
    entries = []
    try:
        with open(LEADERBOARD_FILE) as file:
            for line in file:
                parts = line.split()
                if len(parts) == 3:
                    entries.append((parts[0], int(parts[1]), int(parts[2])))
    except (OSError, ValueError):
        pass

    # Bring over the score from the old single high score file
    if not entries:
        try:
            with open(OLD_HIGH_SCORE_FILE) as file:
                old_score = int(file.read().strip() or 0)
            if old_score > 0:
                entries.append(("YOU", old_score, 1))
        except (OSError, ValueError):
            pass

    entries.sort(key=lambda entry: -entry[1])
    return entries[:5]


def save_leaderboard(entries):
    try:
        with open(LEADERBOARD_FILE, "w") as file:
            for name, score, level in entries:
                file.write(f"{name} {score} {level}\n")
    except OSError as error:
        print(f"Could not save leaderboard: {error}")


def draw_center_text(display_area, text, font, color, y, x=None):
    """
    Draw text centered (with a soft shadow) \n
    text: String to draw \n
    font: Font object \n
    color: Text color \n
    y: Center Y coordinate
    """
    x = bg_x // 2 if x is None else x
    shadow = font.render(text, True, (5, 6, 15))
    display_area.blit(shadow, shadow.get_rect(center=(x + 2, y + 3)))
    surface = font.render(text, True, color)
    display_area.blit(surface, surface.get_rect(center=(x, y)))


def get_text_glow(text, font, color):
    """
    A blurry copy of some text, used as a neon glow behind it
    """
    def build():
        sharp = font.render(text, True, color, (0, 0, 0))
        w, h = sharp.get_size()
        padded = pygame.Surface((w + 40, h + 40))
        padded.blit(sharp, (20, 20))
        # Shrinking then growing an image blurs it
        small = pygame.transform.smoothscale(padded, (max(1, (w + 40) // 8), max(1, (h + 40) // 8)))
        return pygame.transform.smoothscale(small, padded.get_size())
    return cached(("text_glow", text, font.get_height(), color), build)


def draw_glow_text(display_area, text, font, color, y, x=None):
    """
    Draw text centered with a neon glow
    """
    x = bg_x // 2 if x is None else x
    glow = get_text_glow(text, font, color)
    for _ in range(2):
        display_area.blit(glow, glow.get_rect(center=(x, y)), special_flags=pygame.BLEND_ADD)
    draw_center_text(display_area, text, font, color, y, x)

_font_cache = {}


def font_cache(size):
    """The default font at a size (made once, then reused)"""
    if size not in _font_cache:
        _font_cache[size] = pygame.font.Font(None, size)
    return _font_cache[size]


def draw_side_text(display_area, text, font, color, y, x, align="left"):
    """
    Draw text lined up on its left or right edge (with a soft shadow) \n
    align: / "left" means x is the left edge, "right" means x is the right edge
    """
    shadow = font.render(text, True, (5, 6, 15))
    surface = font.render(text, True, color)
    rect = surface.get_rect(midleft=(x, y)) if align == "left" else surface.get_rect(midright=(x, y))
    display_area.blit(shadow, rect.move(2, 2))
    display_area.blit(surface, rect)


def get_panel(w, h):
    """
    Dark glassy box that menus and results are drawn on
    """
    def build():
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        for y in range(h):
            pygame.draw.line(surf, (*mix((24, 32, 68), (10, 13, 32), y / h), 230), (0, y), (w, y))
        mask = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=18)
        surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        pygame.draw.rect(surf, (90, 150, 230, 170), surf.get_rect(), width=2, border_radius=18)
        pygame.draw.line(surf, (255, 255, 255, 45), (18, 3), (w - 18, 3))
        return surf
    return cached(("panel", w, h), build)


def draw_panel(display_area, rect):
    add_wide_glow(display_area, rect, 18, (12, 26, 55))
    display_area.blit(get_panel(rect.width, rect.height), rect)


def get_level_preview(level):
    """
    A tiny picture of a level's brick layout (for level select)
    """
    def build():
        _, layout, boss = level_info(level)
        surf = pygame.Surface((bricks_col * 9, 7 * 5), pygame.SRCALPHA)
        special = {"X": (255, 80, 40), "S": (60, 220, 100), "U": (105, 110, 128)}
        for row, line in enumerate(layout):
            for col, char in enumerate(line):
                if char == ".":
                    continue
                if char in "23":
                    color = tough_colors[int(char)]
                else:
                    color = special.get(char, brick_colors[row % len(brick_colors)])
                pygame.draw.rect(surf, color, (col * 9, row * 5, 8, 4), border_radius=1)
        if boss:
            pygame.draw.rect(surf, (190, 115, 245), (28, 0, 43, 14), border_radius=4)
            pygame.draw.rect(surf, (255, 95, 109), (40, 5, 6, 4))
            pygame.draw.rect(surf, (255, 95, 109), (53, 5, 6, 4))
        return surf
    return cached(("preview", level), build)


def load_dict(path, defaults):
    """
    Read "key value" lines into a copy of defaults (bad or unknown lines are skipped)
    """
    data = dict(defaults)
    try:
        with open(path) as file:
            for line in file:
                parts = line.split()
                if len(parts) != 2 or parts[0] not in data:
                    continue
                key, value = parts
                if isinstance(data[key], int):
                    try:
                        data[key] = int(value)
                    except ValueError:
                        pass
                else:
                    data[key] = value
    except OSError:
        pass
    return data


def save_dict(path, data):
    try:
        with open(path, "w") as file:
            for key, value in data.items():
                file.write(f"{key} {value}\n")
    except OSError as error:
        print(f"Could not save {os.path.basename(path)}: {error}")


def format_time(frames):
    seconds = frames // 60
    hours, minutes = seconds // 3600, seconds // 60 % 60
    if hours:
        return f"{hours}h {minutes:02d}m"
    return f"{minutes}m {seconds % 60:02d}s"

######################遊戲類別/ game class######################

class Game:
    def __init__(self, screen):
        self.screen = screen
        self.canvas = pygame.Surface((bg_x, bg_y))  # Drawn first, then shaken onto the screen
        self.clock = pygame.time.Clock()
        self.backgrounds = {"title": create_background(bg_x, bg_y, seed=99)}
        self.background = self.backgrounds["title"]
        self.vignette = create_vignette(bg_x, bg_y)
        self.sounds = SoundBank()

        # Full-screen flash for big moments (explosions, losing a life...)
        self.flash_amount = 0
        self.flash_overlays = {}
        for name, color in (("white", (255, 255, 255)), ("red", (255, 40, 60))):
            overlay = pygame.Surface((bg_x, bg_y))
            overlay.fill(color)
            self.flash_overlays[name] = overlay
        self.flash_color = "white"

        # Glassy top bar
        self.hud_panel = pygame.Surface((bg_x, hud_h + 8), pygame.SRCALPHA)
        for y in range(hud_h):
            pygame.draw.line(self.hud_panel, (*mix((28, 36, 74), (10, 14, 34), y / hud_h), 235), (0, y), (bg_x, y))
        pygame.draw.line(self.hud_panel, (255, 255, 255, 30), (0, 0), (bg_x, 0))
        for i in range(8):
            pygame.draw.line(self.hud_panel, (90, 150, 230, 140 - i * 18), (0, hud_h + i), (bg_x, hud_h + i))

        self.font = pygame.font.Font(None, 32)
        self.big_font = pygame.font.Font(None, 96)
        self.mid_font = pygame.font.Font(None, 56)
        self.small_font = pygame.font.Font(None, 24)
        self.tiny_font = pygame.font.Font(None, 20)

        self.dim = pygame.Surface((bg_x, bg_y), pygame.SRCALPHA)
        self.dim.fill((5, 8, 20, 170))

        # Moving starfield: [x, y, speed, brightness, twinkle phase]
        self.stars = [[random.uniform(0, bg_x), random.uniform(0, bg_y), random.uniform(0.15, 0.8),
                       random.randint(60, 160), random.uniform(0, 6.3)] for _ in range(80)]

        self.settings = load_dict(SETTINGS_FILE, default_settings)
        if self.settings["difficulty"] not in DIFFICULTIES:
            self.settings["difficulty"] = "normal"
        self.settings["volume"] = max(0, min(10, self.settings["volume"]))
        self.sounds.volume = self.settings["volume"] / 10
        self.sounds.muted = bool(self.settings["muted"])
        self.stats = load_dict(STATS_FILE, default_stats)

        self.leaderboard = load_leaderboard()
        self.high_score = self.leaderboard[0][1] if self.leaderboard else 0
        self.paddle = Paddle()
        self.control_x = bg_x / 2
        self.frame = 0
        self.shake = 0
        self.sparks = []
        self.shockwaves = []
        self.texts = []
        self.new_game(count=False)
        # Menu screens: title, levels, help, scores, stats, settings
        # Game screens: playing, paused, level_clear, game_over
        self.state = "title"
        self.last_state = "title"
        self.focus = 0  # Which button is selected
        self.settings_return = "title"  # Where the settings Back button goes
        self.build_menus()

    ######## game flow ########

    def new_game(self, start_level=1, count=True):
        """
        start_level: / Level to begin on (from level select) 

        count: / Add it to the games played stat
        """
        if count:
            self.stats["games"] += 1
        self.score = 0
        self.lives = DIFFICULTIES[self.settings["difficulty"]][1]
        self.level = start_level
        self.start_high_score = self.high_score
        self.entering_name = False
        self.new_entry_rank = None
        self.load_level()
        self.state = "playing"

    def load_level(self):
        self.bricks = build_level(self.level)
        self.stats["best_level"] = max(self.stats["best_level"], self.level)
        self.level_bricks = 0
        self.level_best_combo = 0
        has_boss = level_info(self.level)[2]
        self.boss = Boss(self.level) if has_boss else None
        # Each level in the loop gets its own nebula background
        key = (self.level - 1) % len(LEVELS)
        if key not in self.backgrounds:
            self.backgrounds[key] = create_background(bg_x, bg_y, seed=key, boss=has_boss)
        self.background = self.backgrounds[key]
        self.powerups = []
        self.level_frame = 0
        self.banner_timer = 150
        self.intro_timer = 75  # Wait for the bricks to drop in before launching
        self.reset_round()

    def reset_round(self):
        """Put one ball back on the paddle and clear power-ups"""
        self.balls = [Ball(self.paddle.rect.centerx, self.paddle.rect.top - 9, self.level_speed())]
        self.effects = {}
        self.shield = False
        self.lasers = []
        self.bombs = []
        self.laser_timer = 0
        self.update_paddle_width()
        self.combo = 0

    def level_speed(self):
        return min(5 + 0.45 * (self.level - 1), 9.5) * DIFFICULTIES[self.settings["difficulty"]][2]

    def max_speed(self):
        return self.level_speed() + 3

    def update_paddle_width(self):
        if "wide" in self.effects:
            self.paddle.target_w = 160
        elif "shrink" in self.effects:
            self.paddle.target_w = 64
        else:
            self.paddle.target_w = self.paddle.base_w

    def screen_flash(self, amount, color="white"):
        if amount >= self.flash_amount:
            self.flash_amount = amount
            self.flash_color = color

    def lose_life(self):
        self.lives -= 1
        self.shake = 14
        self.screen_flash(110, "red")
        self.sounds.play("lose")
        self.powerups = []
        if self.lives <= 0:
            self.state = "game_over"
            self.state_timer = 45  # Short delay so a stray click doesn't restart
            on_board = len(self.leaderboard) < 5 or self.score > self.leaderboard[-1][1]
            self.entering_name = self.score > 0 and on_board
            self.player_name = ""
            self.save_stats()
        else:
            self.reset_round()
            self.texts.append(FloatingText(bg_x // 2, bg_y // 2, "-1 LIFE", (255, 95, 109), self.mid_font))

    def level_clear(self):
        self.state = "level_clear"
        self.state_timer = 150
        self.bonus = 100 * self.level + 50 * self.lives
        self.score += self.bonus
        self.high_score = max(self.high_score, self.score)
        self.sounds.play("clear")
        self.save_stats()
        self.screen_flash(80)
        for _ in range(60):
            self.sparks.append(Spark(random.uniform(100, bg_x - 100), random.uniform(100, 300), random.choice(brick_colors),
                                     random.uniform(-3, 3), random.uniform(-4, 1), random.randint(30, 60)))

    def submit_name(self):
        """Save the player's name and score to the leaderboard"""
        name = self.player_name or "???"
        entry = (name, self.score, self.level)
        self.leaderboard.append(entry)
        self.leaderboard.sort(key=lambda e: -e[1])
        self.leaderboard = self.leaderboard[:5]
        self.new_entry_rank = self.leaderboard.index(entry) if entry in self.leaderboard else None
        save_leaderboard(self.leaderboard)
        self.entering_name = False
        self.state_timer = 20
        self.sounds.play("powerup")

    def save_stats(self):
        save_dict(STATS_FILE, self.stats)

    def quit(self):
        if self.state == "game_over" and self.entering_name:
            self.submit_name()
        self.save_stats()
        pygame.quit()
        sys.exit()

    ######## input ########

    def handle_events(self):
        for event in pygame.event.get():
            widgets = self.current_widgets()  # Can change after each click
            if event.type == pygame.QUIT:
                self.quit()
            elif event.type == pygame.MOUSEMOTION:
                self.control_x = event.pos[0]
                for i, widget in enumerate(widgets):
                    if widget.enabled and widget.rect.collidepoint(event.pos) and i != self.focus:
                        self.focus = i
                        self.sounds.play("type")
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if widgets:
                    for i, widget in enumerate(widgets):
                        if widget.rect.collidepoint(event.pos):
                            self.focus = i
                            if widget.press(event.pos):
                                self.sounds.play("click")
                            break
                else:
                    self.press_action()
            elif event.type == pygame.KEYDOWN:
                if self.state == "game_over" and self.entering_name:
                    self.type_name(event)
                elif event.key in (pygame.K_p, pygame.K_ESCAPE):
                    self.back(event.key)
                elif widgets and event.key in MENU_KEYS:
                    self.menu_key(event.key, widgets)
                elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    self.press_action()
                elif event.key == pygame.K_r and self.state == "paused":
                    self.new_game()
                elif event.key == pygame.K_q and self.state == "paused":
                    self.to_title()
                elif event.key == pygame.K_m:
                    self.toggle_mute()

        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.control_x -= 10
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.control_x += 10
        self.control_x = max(0, min(bg_x, self.control_x))

    def menu_key(self, key, widgets):
        """Arrow keys move between buttons, Enter / Space presses one"""
        if key in (pygame.K_UP, pygame.K_w):
            self.move_focus(-1, widgets)
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.move_focus(1, widgets)
        elif key in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d):
            step = -1 if key in (pygame.K_LEFT, pygame.K_a) else 1
            # Settings rows change their value, other screens just move along
            if not widgets[self.focus].adjust(step):
                self.move_focus(step, widgets)
        elif widgets[self.focus].press():
            self.sounds.play("click")

    def move_focus(self, step, widgets):
        for _ in range(len(widgets)):
            self.focus = (self.focus + step) % len(widgets)
            if widgets[self.focus].enabled:
                break
        self.sounds.play("type")

    def back(self, key):
        """P / Esc: pause, unpause, or go back one screen"""
        if self.state == "playing":
            self.state = "paused"
        elif self.state == "paused":
            self.state = "playing"
        elif key != pygame.K_ESCAPE:
            return
        elif self.state == "title":
            self.quit()
        elif self.state == "settings":
            self.close_settings()
        elif self.state in ("levels", "help", "scores", "stats"):
            self.go("title")
        elif self.state == "game_over" and self.state_timer <= 0:
            self.to_title()

    def type_name(self, event):
        """Typing your name for the leaderboard (3 letters)"""
        if event.key == pygame.K_RETURN:
            if self.player_name:
                self.submit_name()
        elif event.key == pygame.K_BACKSPACE:
            self.player_name = self.player_name[:-1]
            self.sounds.play("type")
        elif event.unicode.isalnum() and event.unicode.isascii() and len(self.player_name) < 3:
            self.player_name += event.unicode.upper()
            self.sounds.play("type")

    def press_action(self):
        """Click / Space during the game (menus use their buttons instead)"""
        if self.state == "playing":
            if self.intro_timer <= 0:
                self.launch_balls()
        elif self.state == "level_clear" and self.state_timer < 110:
            self.state_timer = 0  # Skip ahead to the next level

    ######## menus ########

    def go(self, state):
        self.state = state
        self.focus = 0

    def to_title(self):
        self.save_stats()
        self.go("title")

    def open_settings(self):
        self.settings_return = self.state
        self.go("settings")

    def close_settings(self):
        save_dict(SETTINGS_FILE, self.settings)
        self.go(self.settings_return)

    def open_levels(self):
        unlocked = min(len(LEVELS), self.stats["best_level"])
        for card in self.menus["levels"][:-1]:
            card.enabled = card.level <= unlocked
        self.go("levels")

    def toggle_mute(self):
        self.sounds.muted = not self.sounds.muted
        self.settings["muted"] = int(self.sounds.muted)
        save_dict(SETTINGS_FILE, self.settings)

    def change_volume(self, step):
        self.settings["volume"] = max(0, min(10, self.settings["volume"] + step))
        self.sounds.volume = self.settings["volume"] / 10
        self.sounds.play("bounce")  # So you can hear the new volume

    def change_difficulty(self, step):
        names = list(DIFFICULTIES)
        index = (names.index(self.settings["difficulty"]) + step) % len(names)
        self.settings["difficulty"] = names[index]

    def toggle_setting(self, key):
        self.settings[key] = 1 - self.settings[key]

    def current_widgets(self):
        if self.state == "game_over" and (self.entering_name or self.state_timer > 0):
            return []
        widgets = self.menus.get(self.state, [])
        self.focus = min(self.focus, max(0, len(widgets) - 1))
        return widgets

    def build_menus(self):
        """Make the buttons for every screen"""
        on_off = lambda key: lambda: "On" if self.settings[key] else "Off"
        back = lambda y: Button("Back", (bg_x // 2, y), (200, 46), lambda: self.go("title"), (70, 78, 110))

        self.menus = {
            "title": [
                Button("PLAY", (bg_x // 2, 228), (320, 62), self.new_game, (40, 150, 95), self.mid_font),
                Button("Level Select", (285, 312), (220, 46), self.open_levels),
                Button("How to Play", (515, 312), (220, 46), lambda: self.go("help")),
                Button("Leaderboard", (285, 368), (220, 46), lambda: self.go("scores")),
                Button("Stats", (515, 368), (220, 46), lambda: self.go("stats")),
                Button("Settings", (285, 424), (220, 46), self.open_settings),
                Button("Quit", (515, 424), (220, 46), self.quit, (150, 50, 70)),
            ],
            "help": [back(560)],
            "scores": [back(540)],
            "stats": [back(530)],
            "settings": [
                OptionRow("Volume", (bg_x // 2, 165), (520, 48), lambda: self.settings["volume"], self.change_volume, 10),
                OptionRow("Sound", (bg_x // 2, 223), (520, 48), lambda: "Off" if self.sounds.muted else "On",
                          lambda step: self.toggle_mute()),
                OptionRow("Difficulty", (bg_x // 2, 281), (520, 48),
                          lambda: DIFFICULTIES[self.settings["difficulty"]][0], self.change_difficulty),
                OptionRow("Screen Shake", (bg_x // 2, 339), (520, 48), on_off("shake"), lambda step: self.toggle_setting("shake")),
                OptionRow("Show FPS", (bg_x // 2, 397), (520, 48), on_off("fps"), lambda step: self.toggle_setting("fps")),
                Button("Back", (bg_x // 2, 530), (200, 46), self.close_settings, (70, 78, 110)),
            ],
            "paused": [
                Button("Resume", (bg_x // 2, 262), (260, 48), lambda: self.go("playing"), (40, 150, 95)),
                Button("Restart", (bg_x // 2, 320), (260, 48), self.new_game),
                Button("Settings", (bg_x // 2, 378), (260, 48), self.open_settings),
                Button("Main Menu", (bg_x // 2, 436), (260, 48), self.to_title, (150, 50, 70)),
            ],
            "game_over": [
                Button("Play Again", (300, 545), (190, 46), self.new_game, (40, 150, 95)),
                Button("Main Menu", (500, 545), (190, 46), self.to_title),
            ],
        }

        # Level select: 4 x 2 grid of cards (the first time through the levels)
        cards = []
        for i in range(len(LEVELS)):
            center = (118 + i % 4 * 188, 240 + i // 4 * 150)
            cards.append(LevelCard(i + 1, center, lambda n=i + 1: self.new_game(n)))
        self.menus["levels"] = cards + [back(540)]

    def launch_balls(self):
        for ball in self.balls:
            if ball.stuck:
                self.launch_ball(ball)

    def launch_ball(self, ball):
        # Where it sits on the paddle aims it, and moving the paddle tilts it
        tilt = max(-25, min(25, self.paddle.vel * 1.5))
        if ball.stick_offset:
            base = ball.stick_offset / (self.paddle.rect.width / 2) * 60
        else:
            base = random.uniform(-12, 12)
        ball.set_angle(math.radians(max(-60, min(60, base + tilt))))
        ball.stuck = False
        ball.catch_timer = None
        ball.stick_offset = 0
        self.sounds.play("launch")

    ######## update ########

    def update(self):
        self.paddle.update(self.control_x)
        self.level_frame += 1
        self.stats["play_time"] += 1
        if self.banner_timer > 0:
            self.banner_timer -= 1
        if self.intro_timer > 0:
            self.intro_timer -= 1

        for brick in self.bricks:
            brick.update(self.level_frame)

        if self.boss and self.boss.alive and self.boss.update(self.frame):
            self.bombs.append(Bomb(self.boss.rect.centerx, self.boss.rect.bottom))
            self.sounds.play("bomb")

        for name in list(self.effects):
            self.effects[name] -= 1
            if self.effects[name] <= 0:
                del self.effects[name]
                self.update_paddle_width()

        if "laser" in self.effects:
            self.laser_timer -= 1
            if self.laser_timer <= 0:
                self.laser_timer = 18
                for gun_x in (self.paddle.rect.x + 8, self.paddle.rect.right - 8):
                    self.lasers.append(Laser(gun_x, self.paddle.rect.top - 6))
                self.sounds.play("laser")

        for ball in self.balls:
            if ball.stuck:
                half = self.paddle.rect.width / 2 - 4
                ball.stick_offset = max(-half, min(half, ball.stick_offset))
                ball.x = self.paddle.rect.centerx + ball.stick_offset
                ball.y = self.paddle.rect.top - ball.radius
                ball.trail.clear()
                if ball.catch_timer is not None:
                    ball.catch_timer -= 1
                    if ball.catch_timer <= 0:
                        self.launch_ball(ball)
            else:
                self.move_ball(ball)
                ball.update_trail()

        self.balls = [ball for ball in self.balls if not ball.dead]
        if not self.balls:
            self.lose_life()
            return

        self.update_lasers()
        self.update_bombs()

        for powerup in self.powerups:
            powerup.update()
            if powerup.rect.colliderect(self.paddle.rect):
                self.apply_powerup(powerup.kind)
                powerup.y = bg_y + 100  # Mark for removal
        self.powerups = [p for p in self.powerups if p.y < bg_y + 20]

        boss_done = self.boss is None or not self.boss.alive
        if boss_done and not any(brick.breakable and not brick.hit for brick in self.bricks):
            self.level_clear()

    def update_lasers(self):
        for laser in self.lasers:
            laser.update()
            if laser.dead:
                continue
            for brick in self.bricks:
                if not brick.hit and laser.rect.colliderect(brick.rect):
                    laser.dead = True
                    if not brick.breakable:
                        brick.take_hit()
                        self.sounds.play("steel")
                    elif brick.take_hit():
                        self.destroy_brick(brick)
                    else:
                        self.sounds.play("tough")
                    self.burst(laser.rect.midtop, (255, 120, 120), 4, 2)
                    break
            if not laser.dead and self.boss and self.boss.alive and laser.rect.colliderect(self.boss.rect):
                laser.dead = True
                self.hit_boss(1, laser.rect.midtop)
        self.lasers = [laser for laser in self.lasers if not laser.dead]

    def update_bombs(self):
        for bomb in self.bombs:
            bomb.update()
            if bomb.rect.colliderect(self.paddle.rect):
                bomb.dead = True
                self.effects.pop("wide", None)
                self.effects["shrink"] = 240
                self.update_paddle_width()
                self.shake = max(self.shake, 10)
                self.screen_flash(70, "red")
                self.sounds.play("explode")
                self.burst((bomb.x, bomb.y), (255, 80, 80), 20, 4)
                self.texts.append(FloatingText(self.paddle.rect.centerx, self.paddle.rect.top - 30, "OUCH!", (255, 95, 109), self.font))
            elif bomb.y > bg_y + 10:
                bomb.dead = True
        self.bombs = [bomb for bomb in self.bombs if not bomb.dead]

    def update_effects(self):
        """Particles, stars and text keep animating on every screen"""
        for group in (self.sparks, self.shockwaves, self.texts):
            for item in group:
                item.update()
        self.sparks = [s for s in self.sparks if s.lifetime > 0]
        self.shockwaves = [s for s in self.shockwaves if s.age < s.duration]
        self.texts = [t for t in self.texts if t.lifetime > 0]
        self.flash_amount = max(0, self.flash_amount - 9)
        for star in self.stars:
            star[1] += star[2]
            if star[1] > bg_y:
                star[0] = random.uniform(0, bg_x)
                star[1] = 0

    def move_ball(self, ball):
        """
        Move the ball in small steps so it can't skip through bricks
        """
        factor = 0.6 if "slow" in self.effects else 1.0
        ball.fire = "fire" in self.effects
        steps = max(1, math.ceil(math.hypot(ball.vx, ball.vy) * factor / 4))
        r = ball.radius

        for _ in range(steps):
            ball.x += ball.vx * factor / steps
            ball.y += ball.vy * factor / steps

            # Window edges
            if ball.x - r < 0:
                ball.x = r
                ball.vx = abs(ball.vx)
                self.sounds.play("bounce")
            elif ball.x + r > bg_x:
                ball.x = bg_x - r
                ball.vx = -abs(ball.vx)
                self.sounds.play("bounce")
            if ball.y - r < hud_h:
                ball.y = hud_h + r
                ball.vy = abs(ball.vy)
                self.sounds.play("bounce")

            # Shield saves the ball once
            if self.shield and ball.vy > 0 and ball.y + r > shield_y:
                ball.y = shield_y - r
                ball.vy = -abs(ball.vy)
                self.shield = False
                self.sounds.play("steel")
                for x in range(0, bg_x, 40):
                    self.burst((x, shield_y), (120, 210, 205), 2, 2)

            if ball.y - r > bg_y:
                ball.dead = True
                return

            # Paddle
            if ball.vy > 0 and circle_hits_rect(ball.x, ball.y, r, self.paddle.rect):
                self.bounce_off_paddle(ball)
                if ball.stuck:
                    return
                continue

            # Bricks (one per step)
            for brick in self.bricks:
                if not brick.hit and circle_hits_rect(ball.x, ball.y, r, brick.rect):
                    self.ball_hits_brick(ball, brick)
                    break

            # Boss
            if self.boss and self.boss.alive and circle_hits_rect(ball.x, ball.y, r, self.boss.rect):
                bounce_off_rect(ball, self.boss.rect)
                self.hit_boss(3 if ball.fire else 1, (ball.x, ball.y))

    def bounce_off_paddle(self, ball):
        """
        Where the ball lands on the paddle decides the bounce angle
        """
        pad = self.paddle.rect
        offset = (ball.x - pad.centerx) / (pad.width / 2)
        offset = max(-1.0, min(1.0, offset))
        ball.speed = min(ball.speed + 0.06, self.max_speed())  # Rallies slowly speed up
        ball.set_angle(math.radians(offset * 60))
        ball.y = pad.top - ball.radius
        self.combo = 0
        self.paddle.bump = 6
        self.sounds.play("bounce")
        self.burst((ball.x, pad.top), (180, 220, 255), 5, 2)

        if "catch" in self.effects:
            ball.stuck = True
            ball.stick_offset = ball.x - pad.centerx
            ball.catch_timer = 90  # Launches by itself after 1.5 seconds

    def ball_hits_brick(self, ball, brick):
        if not brick.breakable:
            bounce_off_rect(ball, brick.rect)
            brick.take_hit()
            self.sounds.play("steel")
            self.burst((ball.x, ball.y), (200, 205, 220), 5, 2)
            return

        if ball.fire:
            brick.hp = 1  # Fireball smashes through anything breakable
        else:
            bounce_off_rect(ball, brick.rect)

        if brick.take_hit():
            self.destroy_brick(brick)
        else:
            self.sounds.play("tough")
            self.add_score(5, brick.rect.center, small=True)
            self.burst(brick.rect.center, tough_colors.get(brick.hp, brick.color), 6, 2)

    def hit_boss(self, damage, position):
        self.add_score(15 * damage, position, small=True)
        self.sounds.play("boss_hit")
        self.burst(position, (190, 115, 245), 8, 3)
        self.shake = max(self.shake, 3)
        if self.boss.take_hit(damage):
            self.boss_defeated()

    def boss_defeated(self):
        rect = self.boss.rect
        for point in (rect.center, rect.topleft, rect.topright, rect.bottomleft, rect.bottomright):
            self.shockwaves.append(Shockwave(point[0], point[1], (255, 135, 65), 110))
            self.burst(point, random.choice(brick_colors), 25, 5)
        for _ in range(30):
            self.sparks.append(Debris(random.uniform(rect.left, rect.right), random.uniform(rect.top, rect.bottom), (190, 115, 245)))
        self.shake = 28
        self.screen_flash(200)
        self.sounds.play("explode")
        self.bombs = []
        self.stats["bosses"] += 1
        points = 250 * self.level
        self.score += points
        self.high_score = max(self.high_score, self.score)
        self.texts.append(FloatingText(bg_x // 2, bg_y // 2 - 40, "BOSS DEFEATED!", (255, 215, 0), self.mid_font, 90))
        self.texts.append(FloatingText(bg_x // 2, bg_y // 2 + 10, f"+{points}", (255, 240, 150), self.font, 90))

    def destroy_brick(self, brick):
        """
        Break a brick: points, combo, effects, power-up drops and chain explosions
        """
        brick.hit = True
        self.combo += 1
        self.level_bricks += 1
        self.level_best_combo = max(self.level_best_combo, self.combo)
        self.stats["bricks"] += 1
        self.stats["best_combo"] = max(self.stats["best_combo"], self.combo)
        multiplier = 1 + min(self.combo // 4, 4)
        self.add_score(brick_points.get(brick.brick_type, 10) * multiplier, brick.rect.center)
        self.sounds.play(f"brick{min(self.combo - 1, 7)}")
        self.burst(brick.rect.center, brick.color, 10, 3)
        for _ in range(4):
            self.sparks.append(Debris(brick.rect.centerx, brick.rect.centery, brick.color))

        if brick.brick_type == "explosive":
            self.explode(brick)
        elif brick.brick_type == "spawn":
            self.add_brick()

        if random.random() < powerup_drop_chance and len(self.powerups) < 3:
            kinds = list(POWERUPS)
            weights = [POWERUPS[k][2] for k in kinds]
            kind = random.choices(kinds, weights)[0]
            self.powerups.append(PowerUp(brick.rect.centerx, brick.rect.centery, kind))

    def explode(self, brick):
        """
        Destroy every breakable brick touching the explosive one (can chain!)
        """
        self.shockwaves.append(Shockwave(brick.rect.centerx, brick.rect.centery, (255, 135, 65)))
        self.burst(brick.rect.center, (255, 180, 80), 25, 4)
        self.shake = max(self.shake, 12)
        self.screen_flash(55)
        self.sounds.play("explode")
        reach_x = brick_w + bricks_gap + 1
        reach_y = brick_h + bricks_gap + 1
        for other in list(self.bricks):
            if other.hit or not other.breakable:
                continue
            if abs(other.rect.centerx - brick.rect.centerx) <= reach_x and abs(other.rect.centery - brick.rect.centery) <= reach_y:
                self.destroy_brick(other)

    def add_brick(self):
        """
        Spawner bricks add a normal brick at a random empty spot
        """
        positions = []
        for col in range(bricks_col):
            for row in range(9):
                x = bricks_x0 + col * (brick_w + bricks_gap)
                y = bricks_y0 + row * (brick_h + bricks_gap)
                spot = pygame.Rect(x, y, brick_w, brick_h)
                if any(not b.hit and spot.colliderect(b.rect) for b in self.bricks):
                    continue
                if any(spot.inflate(ball.radius * 2, ball.radius * 2).collidepoint(ball.x, ball.y) for ball in self.balls):
                    continue
                if self.boss and self.boss.alive and spot.top < self.boss.base_y + 40:
                    continue
                positions.append((x, y))

        if positions:
            x, y = random.choice(positions)
            new_brick = Brick(x, y, random.choice(brick_colors))
            new_brick.flash = 6
            self.bricks.append(new_brick)

    def apply_powerup(self, kind):
        _, color, _ = POWERUPS[kind]
        self.texts.append(FloatingText(self.paddle.rect.centerx, self.paddle.rect.top - 30, POWERUP_NAMES[kind], color, self.font))
        self.burst(self.paddle.rect.center, color, 15, 3)
        self.sounds.play("bad" if kind == "shrink" else "powerup")
        self.stats["powerups"] += 1

        if kind in EFFECT_DURATIONS:
            self.effects[kind] = EFFECT_DURATIONS[kind]
        # Wide and shrink cancel each other out
        if kind == "wide":
            self.effects.pop("shrink", None)
        elif kind == "shrink":
            self.effects.pop("wide", None)
        elif kind == "life":
            self.lives = min(self.lives + 1, max_lives)
        elif kind == "shield":
            self.shield = True
        elif kind == "multi":
            self.launch_balls()
            source = self.balls[0]
            for delta in (-25, 25):
                if len(self.balls) >= max_balls:
                    break
                new_ball = Ball(source.x, source.y, source.speed)
                new_ball.stuck = False
                new_ball.set_angle(source.angle() + math.radians(delta))
                self.balls.append(new_ball)
        self.update_paddle_width()

    def add_score(self, points, position, small=False):
        self.score += points
        self.high_score = max(self.high_score, self.score)
        color = (180, 190, 220) if small else (255, 240, 150)
        self.texts.append(FloatingText(position[0], position[1], f"+{points}", color, self.small_font))

    def burst(self, position, color, count, power):
        for _ in range(count):
            self.sparks.append(Spark(position[0], position[1], color, random.uniform(-power, power),
                                     random.uniform(-power, power / 3), random.randint(15, 28)))

    ######## drawing ########

    def draw(self):
        canvas = self.canvas
        menu_screen = self.on_menu_screen()
        canvas.blit(self.backgrounds["title"] if menu_screen else self.background, (0, 0))
        for x, y, speed, shade, phase in self.stars:
            twinkle = round((0.65 + 0.35 * math.sin(self.frame * 0.05 + phase)) * 8) / 8  # Rounded so the cache stays small
            color = darken((shade, shade + 10, min(255, shade + 50)), twinkle)
            if speed > 0.6:
                # Close, bright stars get a little glow
                add_glow(canvas, (x, y), 5, darken(color, round(twinkle * 4) / 8))
                pygame.draw.circle(canvas, lighten(color, 0.3), (int(x), int(y)), 1)
            else:
                canvas.set_at((int(x), int(y)), color)

        if not menu_screen:
            for brick in self.bricks:
                brick.draw(canvas, self.frame)
            if self.boss:
                target_x = self.balls[0].x if self.balls else bg_x / 2
                self.boss.draw(canvas, target_x)
            for bomb in self.bombs:
                bomb.draw(canvas, self.frame)
            for laser in self.lasers:
                laser.draw(canvas)
            for powerup in self.powerups:
                powerup.draw(canvas, self.font, self.frame)
            if self.shield:
                pulse = 4 + round(2 * (1 + math.sin(self.frame * 0.15)))  # 4..8
                add_wide_glow(canvas, pygame.Rect(0, shield_y - 2, bg_x, 4), 10, darken((120, 210, 205), pulse / 10))
                pygame.draw.line(canvas, (200, 255, 250), (0, shield_y), (bg_x, shield_y), 2)
            self.paddle.draw(canvas, self.effects)
            for ball in self.balls:
                ball.draw(canvas)

        for group in (self.sparks, self.shockwaves, self.texts):
            for item in group:
                item.draw(canvas)
        canvas.blit(self.vignette, (0, 0))

        # Screen shake
        offset = (0, 0)
        if self.shake > 0:
            if self.settings["shake"]:
                power = self.shake // 2 + 1
                offset = (random.randint(-power, power), random.randint(-power, power))
            self.shake -= 1
        self.screen.fill((0, 0, 0))
        self.screen.blit(canvas, offset)

        if self.flash_amount > 0:
            overlay = self.flash_overlays[self.flash_color]
            overlay.set_alpha(self.flash_amount)
            self.screen.blit(overlay, (0, 0))

        if menu_screen:
            screens = {"title": self.draw_title, "levels": self.draw_level_select, "help": self.draw_help,
                       "scores": self.draw_scores, "stats": self.draw_stats, "settings": self.draw_settings}
            screens[self.state]()
        else:
            self.draw_hud()
            if self.state == "playing":
                self.draw_hints()
            elif self.state == "paused":
                self.draw_pause()
            elif self.state == "settings":
                self.screen.blit(self.dim, (0, 0))
                self.draw_settings()
            elif self.state == "level_clear":
                self.draw_level_clear()
            elif self.state == "game_over":
                self.draw_game_over()

        for widget in self.current_widgets():
            widget.draw(self.screen, self.font, self.frame)

        if self.settings["fps"]:
            fps = self.tiny_font.render(f"FPS {self.clock.get_fps():.0f}", True, (150, 220, 150))
            self.screen.blit(fps, (8, bg_y - 20))

        pygame.display.flip()

    def on_menu_screen(self):
        """Menu screens use the title background and hide the game"""
        if self.state == "settings":
            return self.settings_return == "title"
        return self.state in ("title", "levels", "help", "scores", "stats")

    def draw_hud(self):
        self.screen.blit(self.hud_panel, (0, 0))

        # Small labels above big numbers
        for label, value, x, color in (("SCORE", self.score, 16, (255, 255, 255)),
                                       ("BEST", self.high_score, 190, (255, 215, 0)),
                                       ("LEVEL", self.level, 370, (150, 200, 255))):
            self.screen.blit(self.tiny_font.render(label, True, (120, 140, 190)), (x, 5))
            shadow = self.font.render(str(value), True, (5, 6, 15))
            self.screen.blit(shadow, (x + 1, 20))
            self.screen.blit(self.font.render(str(value), True, color), (x, 18))

        for i in range(self.lives):
            center = (bg_x - 22 - i * 26, hud_h // 2)
            add_glow(self.screen, center, 14, (90, 70, 0))
            draw_sphere(self.screen, center, 8, (255, 215, 0))

        # Active power-up timers
        for i, (name, time_left) in enumerate(self.effects.items()):
            _, color, _ = POWERUPS[name]
            rect = pygame.Rect(10 + i * 100, hud_h + 8, 92, 18)
            self.screen.blit(get_block(rect.width, rect.height, (30, 38, 70), 6), rect)
            bar_w = int(rect.width * min(1, time_left / EFFECT_DURATIONS[name])) // 2 * 2
            if bar_w >= 12:
                self.screen.blit(get_block(bar_w, rect.height, darken(color, 0.85), 6), rect)
            draw_center_text(self.screen, name.upper(), self.tiny_font, (255, 255, 255), rect.centery, x=rect.centerx)

        multiplier = 1 + min(self.combo // 4, 4)
        if multiplier > 1:
            draw_glow_text(self.screen, f"COMBO x{multiplier}", self.font, brick_colors[multiplier], hud_h + 20, x=bg_x - 80)

        if self.sounds.muted:
            self.screen.blit(self.small_font.render("MUTED", True, (150, 150, 170)), (bg_x - 70, bg_y - 22))

    def draw_hints(self):
        if self.banner_timer > 0:
            name = level_info(self.level)[0]
            color = (255, 95, 109) if self.boss else (255, 255, 255)
            title = self.mid_font.render(f"LEVEL {self.level}: {name}", True, color)
            title.set_alpha(min(255, self.banner_timer * 4))
            self.screen.blit(title, title.get_rect(center=(bg_x // 2, bg_y // 2 + 40)))
        if self.intro_timer <= 0 and any(ball.stuck and ball.catch_timer is None for ball in self.balls):
            alpha = 150 + int(100 * math.sin(self.frame * 0.08))
            hint = self.font.render("Click or press SPACE to launch", True, (200, 210, 240))
            hint.set_alpha(alpha)
            self.screen.blit(hint, hint.get_rect(center=(bg_x // 2, bg_y - 90)))

    def draw_leaderboard(self, top, highlight=None):
        """
        Draw the top 5 table \n
        top: / Y position of the heading \n
        highlight: / Row to flash (the new entry)
        """
        draw_glow_text(self.screen, "TOP 5", self.mid_font, (255, 215, 0), top)
        if not self.leaderboard:
            draw_center_text(self.screen, "No scores yet - be the first!", self.font, (180, 190, 220), top + 60)
            return
        for i, (name, score, level) in enumerate(self.leaderboard):
            y = top + 50 + i * 34
            color = (255, 255, 255)
            if i == highlight and self.frame // 15 % 2 == 0:
                color = (100, 230, 150)
            for text, x in ((f"{i + 1}.", 250), (name, 330), (str(score), 470), (f"Lv {level}", 570)):
                draw_center_text(self.screen, text, self.font, color, y, x=x)

    def draw_title(self):
        title = "BRICK BLAST"
        letters = [self.big_font.render(ch, True, brick_colors[i % len(brick_colors)]) for i, ch in enumerate(title)]
        total_w = sum(letter.get_width() for letter in letters)
        x = (bg_x - total_w) // 2
        for i, letter in enumerate(letters):
            y = 90 + int(8 * math.sin(self.frame * 0.06 + i * 0.5))
            color = brick_colors[i % len(brick_colors)]
            glow = get_text_glow(title[i], self.big_font, color)
            for _ in range(2):
                self.screen.blit(glow, glow.get_rect(center=(x + letter.get_width() // 2, y + letter.get_height() // 2)),
                                 special_flags=pygame.BLEND_ADD)
            shadow = self.big_font.render(title[i], True, (5, 6, 15))
            self.screen.blit(shadow, (x + 3, y + 5))
            self.screen.blit(letter, (x, y))
            x += letter.get_width()

        difficulty = DIFFICULTIES[self.settings["difficulty"]][0]
        draw_center_text(self.screen, f"Best: {self.high_score}      Difficulty: {difficulty}",
                         self.small_font, (170, 185, 225), 490)
        draw_center_text(self.screen, "Mouse, or arrow keys + Enter      Esc: quit", self.tiny_font, (110, 125, 160), bg_y - 18)

    def draw_header(self, text, color=(150, 200, 255)):
        draw_glow_text(self.screen, text, self.mid_font, color, 70)

    def draw_help(self):
        self.draw_header("HOW TO PLAY")
        draw_center_text(self.screen, "BRICKS", self.small_font, (255, 215, 0), 232)
        draw_center_text(self.screen, "POWER-UPS", self.small_font, (255, 215, 0), 318)
        self.draw_how_to_play()

    def draw_scores(self):
        self.draw_header("LEADERBOARD", (255, 215, 0))
        self.draw_leaderboard(150)

    def draw_level_select(self):
        self.draw_header("LEVEL SELECT")
        draw_center_text(self.screen, "Reach a level to unlock it here", self.small_font, (170, 185, 225), 122)

    def draw_stats(self):
        self.draw_header("STATS")
        panel = pygame.Rect(180, 120, 440, 340)
        draw_panel(self.screen, panel)
        rows = [
            ("Games played", str(self.stats["games"])),
            ("Bricks broken", str(self.stats["bricks"])),
            ("Bosses defeated", str(self.stats["bosses"])),
            ("Power-ups caught", str(self.stats["powerups"])),
            ("Best combo", str(self.stats["best_combo"])),
            ("Furthest level", str(self.stats["best_level"])),
            ("Time played", format_time(self.stats["play_time"])),
        ]
        for i, (label, value) in enumerate(rows):
            y = panel.top + 40 + i * 44
            if i:
                pygame.draw.line(self.screen, (40, 52, 95), (panel.left + 30, y - 22), (panel.right - 30, y - 22))
            draw_side_text(self.screen, label, self.font, (190, 200, 235), y, panel.left + 34)
            draw_side_text(self.screen, value, self.font, (255, 215, 0), y, panel.right - 34, "right")

    def draw_settings(self):
        self.draw_header("SETTINGS")
        _, lives, _, about = DIFFICULTIES[self.settings["difficulty"]]
        draw_center_text(self.screen, f"Difficulty: {about}", self.small_font, (170, 185, 225), 448)
        if self.settings_return == "paused":
            draw_center_text(self.screen, "Starting lives change on your next game", self.tiny_font, (130, 145, 185), 474)
        draw_center_text(self.screen, "Up/Down: choose      Left/Right: change      Esc: back",
                         self.tiny_font, (110, 125, 160), bg_y - 18)

    def draw_pause(self):
        self.screen.blit(self.dim, (0, 0))
        panel = pygame.Rect(0, 0, 340, 380)
        panel.center = (bg_x // 2, 320)
        draw_panel(self.screen, panel)
        draw_glow_text(self.screen, "PAUSED", self.mid_font, (150, 200, 255), panel.top + 48)
        draw_center_text(self.screen, f"Level {self.level}  -  Score {self.score}", self.small_font, (170, 185, 225),
                         panel.top + 88)
        draw_center_text(self.screen, "P / Esc: resume   R: restart   M: mute", self.tiny_font, (130, 145, 185),
                         panel.bottom - 22)

    def draw_level_clear(self):
        panel = pygame.Rect(0, 0, 460, 340)
        panel.center = (bg_x // 2, bg_y // 2 + 10)
        draw_panel(self.screen, panel)
        draw_glow_text(self.screen, f"LEVEL {self.level} CLEAR!", self.mid_font, (100, 230, 150), panel.top + 46)

        rows = [
            ("Bricks broken", str(self.level_bricks)),
            ("Best combo", str(self.level_best_combo)),
            ("Time", format_time(self.level_frame)),
            ("Lives left", str(self.lives)),
        ]
        # Rows slide in one after another
        shown = (150 - self.state_timer) // 8
        for i, (label, value) in enumerate(rows[:shown]):
            y = panel.top + 100 + i * 36
            draw_side_text(self.screen, label, self.font, (190, 200, 235), y, panel.left + 40)
            draw_side_text(self.screen, value, self.font, (255, 255, 255), y, panel.right - 40, "right")
        if shown > len(rows):
            draw_glow_text(self.screen, f"Bonus +{self.bonus}", self.mid_font, (255, 215, 0), panel.top + 262)

        next_name = level_info(self.level + 1)[0]
        draw_center_text(self.screen, f"Next: {next_name}", self.small_font, (150, 200, 255), panel.bottom - 30)
        if self.state_timer < 110 and self.frame // 20 % 2 == 0:
            draw_center_text(self.screen, "Click to continue", self.tiny_font, (170, 185, 225), panel.bottom + 22)

    def draw_how_to_play(self):
        # Brick legend
        samples = [
            (Brick(0, 0, brick_colors[0]), "Normal"),
            (Brick(0, 0, brick_colors[0], "tough", 3), "Tough"),
            (Brick(0, 0, (255, 80, 40), "explosive"), "Explosive"),
            (Brick(0, 0, (60, 220, 100), "spawn"), "Spawner"),
            (Brick(0, 0, (105, 110, 128), "steel"), "Steel"),
            (Brick(0, 0, brick_colors[4], move_amp=1), "Moving"),
        ]
        for i, (brick, label) in enumerate(samples):
            cx = 100 + i * 120
            brick.rect.center = (cx, 270)
            brick.draw(self.screen, self.frame)
            draw_center_text(self.screen, label, self.small_font, (200, 210, 240), 295, x=cx)

        # Power-up legend
        short_names = {"wide": "Wide", "multi": "Multi", "slow": "Slow", "fire": "Fire", "laser": "Laser",
                       "catch": "Catch", "shield": "Shield", "life": "Life", "shrink": "Shrink!"}
        for i, kind in enumerate(POWERUPS):
            cx = 80 + i * 80
            powerup = PowerUp(cx, 345, kind)
            powerup.draw(self.screen, self.font, self.frame)
            draw_center_text(self.screen, short_names[kind], self.tiny_font, (200, 210, 240), 372, x=cx)

        controls = [
            "Mouse or Left/Right keys: move paddle      Click or Space: launch ball",
            "P / Esc: pause menu      M: mute      Change sound and difficulty in Settings",
            "Break bricks without touching the paddle for a COMBO bonus!",
            "Every 4th level has a BOSS - dodge its bombs!",
        ]
        for i, line in enumerate(controls):
            draw_center_text(self.screen, line, self.small_font, (150, 165, 200), 430 + i * 28)

    def draw_game_over(self):
        self.screen.blit(self.dim, (0, 0))
        draw_glow_text(self.screen, "GAME OVER", self.big_font, (255, 60, 60), 120)
        draw_center_text(self.screen, f"Score: {self.score}", self.mid_font, (255, 255, 255), 190)
        draw_center_text(self.screen, f"Reached level {self.level}", self.font, (150, 200, 255), 232)

        if self.entering_name:
            if self.frame // 20 % 2 == 0:
                draw_glow_text(self.screen, "NEW HIGH SCORE!", self.mid_font, (100, 230, 150), 300)
            draw_center_text(self.screen, "Type your name:", self.font, (200, 210, 240), 355)
            for i in range(3):
                box = pygame.Rect(0, 0, 50, 60)
                box.center = (bg_x // 2 - 60 + i * 60, 420)
                active = i == len(self.player_name)
                border = (255, 215, 0) if active and self.frame // 15 % 2 == 0 else (73, 100, 155)
                pygame.draw.rect(self.screen, (20, 28, 52), box, border_radius=8)
                pygame.draw.rect(self.screen, border, box, width=3, border_radius=8)
                if i < len(self.player_name):
                    draw_center_text(self.screen, self.player_name[i], self.mid_font, (255, 255, 255), box.centery, x=box.centerx)
            draw_center_text(self.screen, "Press Enter to save", self.small_font, (150, 165, 200), 480)
        else:
            self.draw_leaderboard(290, self.new_entry_rank)

    ######## main loop ########

    def step(self):
        """Run one frame of the game"""
        self.frame += 1
        self.handle_events()
        if self.state != self.last_state:
            self.last_state = self.state
            self.focus = 0
        if self.state == "playing":
            self.update()
        elif self.state == "level_clear":
            self.state_timer -= 1
            if self.state_timer <= 0:
                self.level += 1
                self.load_level()
                self.state = "playing"
        elif self.state == "game_over" and self.state_timer > 0:
            self.state_timer -= 1
        if self.state != "paused" and not (self.state == "settings" and self.settings_return == "paused"):
            self.update_effects()
        for i, widget in enumerate(self.current_widgets()):
            widget.update(i == self.focus)
        pygame.mouse.set_visible(self.state != "playing")
        self.draw()

    def run(self):
        while True:
            self.clock.tick(60)  # set fps
            self.step()

######################主程式/ main program######################

def main():
    pygame.mixer.pre_init(22050, -16, 1, 512)  # Small buffer = less sound delay
    pygame.init()  # start pygame
    pygame.display.set_caption("Brick Blast")
    screen = pygame.display.set_mode((bg_x, bg_y))
    Game(screen).run()


if __name__ == "__main__":
    main()
