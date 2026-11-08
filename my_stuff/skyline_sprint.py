######################載入套件/ import packages######################

import pygame
import sys
import os
import math
import random
import io
import wave
from array import array
from collections import deque

######################遊戲常數/ game constants######################

bg_x = 800
bg_y = 600

GAME_DIR = os.path.dirname(os.path.abspath(__file__))
BEST_FILE = os.path.join(GAME_DIR, "skyline_best.txt")

gravity = 0.72
jump_power = 13.2      # Normal jump (about 120 px high)
air_jump_power = 11    # Double jump
kick_power = 12.5      # Wall kick goes up...
kick_push = 4.5        # ...and pushes you back off the wall
max_fall = 19
roll_impact = 15.5     # Landing faster than this needs a roll
coyote_frames = 6      # You can still jump this many frames after running off an edge
buffer_frames = 8      # A jump pressed this early before landing still counts

runner_w = 20
stand_h = 44
low_h = 22             # Height while sliding or rolling

start_speed = 6.4
speed_gain = 4.4       # Extra speed reached by the end of the ramp
ramp_length = 40000    # Pixels until full speed

hurdle_h = 34
barrier_gap = 34       # Space under a billboard (only fits a sliding runner)

runner_color = (90, 235, 255)
coin_color = (255, 215, 90)
swarm_color = (255, 50, 80)

building_colors = [
    (34, 26, 62),
    (26, 32, 70),
    (44, 24, 64),
    (24, 38, 64),
    (38, 30, 78),
]
neon_colors = [
    (255, 90, 190),
    (90, 235, 255),
    (255, 200, 80),
    (140, 255, 150),
    (190, 120, 255),
]
billboard_words = ["SLIDE", "DUCK", "LOW", "MIND YOUR HEAD", "NEON", "GO GO", "CITY", "RUN"]

# Points for each trick (multiplied by your combo)
tricks = {
    "HURDLE": 10,
    "SLIDE": 15,
    "WALL KICK": 15,
    "MANTLE": 25,
    "ROLL": 20,
    "LEAP": 15,
    "BIG LEAP": 30,
}

######################繪圖工具/ graphics helpers######################

_cache = {}


def cached(key, build):
    """Build a surface once and reuse it"""
    if key not in _cache:
        if len(_cache) > 600:
            _cache.clear()
        _cache[key] = build()
    return _cache[key]


def lighten(color, amount):
    return tuple(int(c + (255 - c) * amount) for c in color)


def darken(color, factor):
    return tuple(int(c * factor) for c in color)


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def get_glow(radius, color):
    def build():
        glow = pygame.Surface((radius * 2, radius * 2))
        for r in range(radius, 0, -2):
            t = 1 - r / radius
            pygame.draw.circle(glow, darken(color, t * t * 0.6), (radius, radius), r)
        return glow
    return cached(("glow", radius, color), build)


def add_glow(surface, center, radius, color):
    radius = int(radius)
    glow = get_glow(radius, color)
    surface.blit(glow, (center[0] - radius, center[1] - radius), special_flags=pygame.BLEND_ADD)


def draw_text(surface, text, font, color, center, shadow=True):
    if shadow:
        back = font.render(text, True, (4, 4, 14))
        surface.blit(back, back.get_rect(center=(center[0] + 2, center[1] + 3)))
    front = font.render(text, True, color)
    surface.blit(front, front.get_rect(center=center))


def draw_glow_text(surface, text, font, color, center):
    """Text with a blurry neon glow behind it"""
    def build():
        sharp = font.render(text, True, color, (0, 0, 0))
        w, h = sharp.get_size()
        padded = pygame.Surface((w + 40, h + 40))
        padded.blit(sharp, (20, 20))
        small = pygame.transform.smoothscale(padded, (max(1, (w + 40) // 8), max(1, (h + 40) // 8)))
        return pygame.transform.smoothscale(small, padded.get_size())
    glow = cached(("text_glow", text, font.get_height(), color), build)
    for _ in range(2):
        surface.blit(glow, glow.get_rect(center=center), special_flags=pygame.BLEND_ADD)
    draw_text(surface, text, font, color, center)


def get_sky():
    """Sunset gradient: dark purple at the top, orange at the horizon"""
    def build():
        colors = [(10, 6, 30), (40, 12, 70), (120, 30, 100), (230, 90, 90), (255, 170, 100)]
        small = pygame.Surface((1, 40))
        for y in range(40):
            t = y / 39 * (len(colors) - 1)
            i = min(int(t), len(colors) - 2)
            small.set_at((0, y), mix(colors[i], colors[i + 1], t - i))
        return pygame.transform.smoothscale(small, (bg_x, bg_y))
    return cached(("sky",), build)


def get_sun():
    """Big striped sunset sun"""
    def build():
        r = 130
        sun = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        for y in range(r * 2):
            t = y / (r * 2)
            color = mix((255, 230, 120), (255, 80, 140), t)
            half = math.sqrt(max(0, r * r - (y - r) ** 2))
            # Stripes get thicker toward the bottom
            if t > 0.5 and (y % 14) < (t - 0.5) * 16:
                continue
            pygame.draw.line(sun, color, (r - half, y), (r + half, y))
        return sun
    return cached(("sun",), build)


def make_building_sprite(w, color, seed):
    """Building face with lit windows (only the top part, the rest is plain)"""
    rng = random.Random(seed)
    height = 700
    face = pygame.Surface((w, height))
    face.fill(color)
    # Vertical shading stripe on the left edge
    pygame.draw.rect(face, lighten(color, 0.08), (0, 0, 6, height))
    win_w, win_h = rng.choice([(10, 14), (14, 10), (8, 18)])
    gap_x, gap_y = win_w + rng.randint(8, 14), win_h + rng.randint(10, 16)
    lit = lighten(rng.choice(neon_colors), 0.3)
    for y in range(28, height, gap_y):
        for x in range(16, w - win_w - 8, gap_x):
            roll = rng.random()
            if roll < 0.18:
                window = mix(color, lit, 0.75)
            elif roll < 0.5:
                window = lighten(color, 0.12)
            else:
                continue
            face.fill(window, (x, y, win_w, win_h))
    # Fade into darkness further down
    shade = pygame.Surface((w, height), pygame.SRCALPHA)
    for y in range(0, height, 10):
        shade.fill((0, 0, 0, int(min(200, y * 0.35))), (0, y, w, 10))
    face.blit(shade, (0, 0))
    return face

######################音效/ sounds######################

def make_sound(duration, wave_func, volume):
    """
    Turn a wave function into a pygame Sound \n
    wave_func(t, duration): / Returns a value between -1 and 1
    """
    sample_rate = 22050
    samples = array("h")
    for i in range(int(sample_rate * duration)):
        t = i / sample_rate
        samples.append(int(max(-1.0, min(1.0, wave_func(t, duration))) * volume * 32767))
    sound_file = io.BytesIO()
    with wave.open(sound_file, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(samples.tobytes())
    sound_file.seek(0)
    return pygame.mixer.Sound(file=sound_file)


def sweep(t, duration, f0, f1):
    """Sine wave sliding from frequency f0 to f1"""
    return math.sin(2 * math.pi * (f0 * t + (f1 - f0) * t * t / (2 * duration)))


class SoundBank:
    def __init__(self):
        self.muted = False
        self.sounds = {}
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(22050, -16, 1, 512)
            self.build()
        except pygame.error as error:
            print(f"Sound is unavailable: {error}")

    def build(self):
        noise = random.Random(11)
        fade = lambda t, d: (1 - t / d) ** 2
        self.sounds["jump"] = make_sound(0.12, lambda t, d: sweep(t, d, 300, 700) * fade(t, d), 0.22)
        self.sounds["double"] = make_sound(0.16, lambda t, d: sweep(t, d, 500, 1200) * fade(t, d), 0.2)
        self.sounds["kick"] = make_sound(
            0.14, lambda t, d: (sweep(t, d, 180, 520) * 0.7 + noise.uniform(-1, 1) * 0.3) * fade(t, d), 0.3)
        self.sounds["land"] = make_sound(0.08, lambda t, d: noise.uniform(-1, 1) * fade(t, d), 0.12)
        self.sounds["slide"] = make_sound(0.25, lambda t, d: noise.uniform(-1, 1) * (1 - t / d) * 0.6, 0.14)
        self.sounds["roll"] = make_sound(
            0.3, lambda t, d: (noise.uniform(-1, 1) * 0.5 + sweep(t, d, 120, 70) * 0.5) * fade(t, d), 0.25)
        self.sounds["coin"] = make_sound(
            0.15, lambda t, d: math.sin(2 * math.pi * (1320 if t < 0.05 else 1980) * t) * fade(t, d), 0.16)
        self.sounds["stumble"] = make_sound(
            0.35, lambda t, d: (sweep(t, d, 320, 90) * 0.6 + noise.uniform(-1, 1) * 0.4) * fade(t, d), 0.35)
        self.sounds["die"] = make_sound(
            0.9, lambda t, d: (sweep(t, d, 500, 50) * 0.6 + noise.uniform(-1, 1) * 0.3) * (1 - t / d), 0.35)
        # Trick chimes climb a scale as your combo grows
        for k in range(8):
            f = 520 * 2 ** ([0, 2, 4, 7, 9, 12, 14, 16][k] / 12)
            self.sounds[f"trick{k}"] = make_sound(
                0.2, lambda t, d, f=f: (math.sin(2 * math.pi * f * t) + 0.4 * math.sin(4 * math.pi * f * t)) * fade(t, d),
                0.17)

    def play(self, name):
        if not self.muted and name in self.sounds:
            self.sounds[name].play()

######################物件類別/ object class######################

class Building:
    def __init__(self, index, x, w, top, gap_before):
        """
        One rooftop \n
        index: / Order in the city (used for gap-jump bonuses) \n
        gap_before: / Width of the gap you jump to reach it
        """
        self.index = index
        self.rect = pygame.Rect(x, top, w, 4000)
        self.gap_before = gap_before
        self.seed = random.randint(0, 99999)
        self.color = random.choice(building_colors)
        self.neon = random.choice(neon_colors)
        self.walls = []
        self.antennas = [(random.randint(20, max(21, w - 40)), random.randint(18, 50)) for _ in range(random.randint(0, 2))]

    def draw(self, surface, cam_x, cam_y, frame):
        sx, sy = self.rect.x - cam_x, self.rect.top - cam_y
        if sx > bg_x or sx + self.rect.w < 0 or sy > bg_y:
            return
        face = cached(("building", self.seed, self.rect.w), lambda: make_building_sprite(self.rect.w, self.color, self.seed))
        surface.blit(face, (sx, sy))
        if sy + 700 < bg_y:
            surface.fill((0, 0, 0), (sx, sy + 700, self.rect.w, bg_y - sy - 700))
        for ax, ah in self.antennas:
            pygame.draw.line(surface, darken(self.color, 0.6), (sx + ax, sy), (sx + ax, sy - ah), 3)
            if (frame // 30 + ax) % 2 == 0:
                add_glow(surface, (sx + ax, sy - ah), 10, (255, 60, 60))
                pygame.draw.circle(surface, (255, 120, 120), (sx + ax, sy - ah), 2)
        pygame.draw.line(surface, self.neon, (sx, sy), (sx + self.rect.w - 1, sy), 3)
        for wall in self.walls:
            wx, wy = wall.x - cam_x, wall.y - cam_y
            pygame.draw.rect(surface, lighten(self.color, 0.1), (wx, wy, wall.w, wall.h))
            pygame.draw.rect(surface, lighten(self.color, 0.2), (wx, wy, 6, wall.h))
            for y in range(14, wall.h - 8, 22):
                pygame.draw.line(surface, darken(self.color, 0.7), (wx + 6, wy + y), (wx + wall.w, wy + y), 2)
            pygame.draw.line(surface, self.neon, (wx, wy), (wx + wall.w - 1, wy), 3)


class Hazard:
    def __init__(self, kind, rect, color):
        """
        Something to get past \n
        kind: / "hurdle" (jump it) or "barrier" (slide under it)
        """
        self.kind = kind
        self.rect = rect
        self.color = color
        self.word = random.choice(billboard_words)
        self.broken = False
        self.passed = False

    def draw(self, surface, cam_x, cam_y, font, frame):
        if self.broken:
            return
        r = self.rect.move(-cam_x, -cam_y)
        if r.right < 0 or r.left > bg_x:
            return
        if self.kind == "hurdle":
            pygame.draw.line(surface, (90, 90, 110), (r.left + 4, r.bottom), (r.left + 4, r.top + 6), 3)
            pygame.draw.line(surface, (90, 90, 110), (r.right - 4, r.bottom), (r.right - 4, r.top + 6), 3)
            bar = pygame.Rect(r.left - 3, r.top, r.w + 6, 12)
            pygame.draw.rect(surface, (255, 150, 40), bar)
            for x in range(bar.left, bar.right, 10):
                pygame.draw.line(surface, (245, 245, 245), (x, bar.bottom), (min(bar.right, x + 6), bar.top), 3)
        else:
            # Billboard hanging on poles; the bottom edge is what you slide under
            board = pygame.Rect(r.left, r.bottom - 64, r.w, 64)
            for px in (r.left + 10, r.right - 10):
                pygame.draw.line(surface, (60, 55, 80), (px, r.top), (px, board.top), 4)
            pygame.draw.rect(surface, (20, 14, 36), board)
            flicker = 0.75 + 0.25 * math.sin(frame * 0.3 + r.x)
            pygame.draw.rect(surface, darken(self.color, flicker), board, 3)
            add_glow(surface, board.center, min(60, r.w // 2 + 10), darken(self.color, 0.6))
            text = font.render(self.word, True, lighten(self.color, 0.3))
            if text.get_width() > r.w - 10:
                text = pygame.transform.smoothscale(text, (r.w - 10, text.get_height()))
            surface.blit(text, text.get_rect(center=board.center))
            pygame.draw.line(surface, self.color, (r.left, r.bottom), (r.right, r.bottom), 3)


class Coin:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.taken = False

    def draw(self, surface, cam_x, cam_y, frame):
        sx, sy = self.x - cam_x, self.y - cam_y + math.sin(frame * 0.08 + self.x * 0.02) * 3
        if sx < -20 or sx > bg_x + 20:
            return
        add_glow(surface, (sx, sy), 18, darken(coin_color, 0.7))
        width = abs(math.cos(frame * 0.09 + self.x * 0.01)) * 8 + 2
        pygame.draw.ellipse(surface, coin_color, (sx - width, sy - 9, width * 2, 18))
        pygame.draw.ellipse(surface, lighten(coin_color, 0.5), (sx - width * 0.5, sy - 6, width, 12))


class Particle:
    def __init__(self, x, y, vx, vy, color, life, size=3, fall=0.25):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.life = self.max_life = life
        self.size = size
        self.fall = fall

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += self.fall
        self.vx *= 0.97
        self.life -= 1

    def draw(self, surface, cam_x, cam_y):
        t = self.life / self.max_life
        size = max(1, int(self.size * t + 0.5))
        pygame.draw.rect(surface, mix((0, 0, 0), self.color, t), (self.x - cam_x - size / 2, self.y - cam_y - size / 2, size, size))


class FloatingText:
    def __init__(self, x, y, text, color, font):
        self.x = x
        self.y = y
        self.life = 55
        self.image = font.render(text, True, color)
        self.shadow = font.render(text, True, (4, 4, 14))

    def update(self):
        self.y -= 1.1
        self.life -= 1

    def draw(self, surface, cam_x, cam_y):
        alpha = min(255, self.life * 8)
        for image, offset in ((self.shadow, 2), (self.image, 0)):
            image.set_alpha(alpha)
            surface.blit(image, image.get_rect(center=(self.x - cam_x + offset, self.y - cam_y + offset)))


def limb(start, a1, l1, a2, l2):
    """
    Two-part limb (thigh + shin, or upper arm + forearm) \n
    Angles are measured from straight down, positive = toward the front
    """
    joint = (start[0] + math.sin(a1) * l1, start[1] + math.cos(a1) * l1)
    end = (joint[0] + math.sin(a2) * l2, joint[1] + math.cos(a2) * l2)
    return joint, end


def load_best():
    try:
        with open(BEST_FILE) as file:
            return int(file.read().strip() or 0)
    except (OSError, ValueError):
        return 0


def save_best(score):
    try:
        with open(BEST_FILE, "w") as file:
            file.write(str(score))
    except OSError as error:
        print(f"Could not save best score: {error}")

######################遊戲類別/ game class######################

class Game:
    def __init__(self, screen):
        self.screen = screen
        self.canvas = pygame.Surface((bg_x, bg_y))
        self.clock = pygame.time.Clock()
        self.sounds = SoundBank()
        self.big_font = pygame.font.Font(None, 96)
        self.mid_font = pygame.font.Font(None, 54)
        self.font = pygame.font.Font(None, 32)
        self.small_font = pygame.font.Font(None, 24)
        self.board_font = pygame.font.Font(None, 30)

        self.best = load_best()
        self.frame = 0
        self.reset()
        self.state = "title"  # title, playing, paused, dying, dead

    ######## game flow ########

    def reset(self):
        self.buildings = [Building(0, -600, 1900, 440, 0)]
        self.hazards = []
        self.coins = []
        self.particles = []
        self.texts = []
        self.trail = deque(maxlen=10)

        # Runner (x = left edge, feet = bottom edge, in world pixels)
        self.px = 100.0
        self.feet = 440.0
        self.vx = start_speed
        self.vy = 0.0
        self.on_ground = True
        self.coyote = coyote_frames
        self.jump_buffer = 0
        self.down_timer = 0
        self.air_jumps = 1
        self.can_cut_jump = False
        self.wall_contact = 0
        self.touching_wall = False
        self.kick_chain = 0
        self.sliding = False
        self.slide_time = 0
        self.roll_timer = 0
        self.flip_timer = 0
        self.stumble = 0
        self.run_phase = 0.0
        self.takeoff = 0

        self.chase_x = self.px - 380
        self.cam_x = self.px - 250
        self.cam_y = 440 - 430
        self.shake = 0
        self.coin_count = 0
        self.trick_score = 0
        self.combo = 0
        self.combo_timer = 0
        self.best_combo = 0
        self.stumbles = 0
        self.start_timer = 0
        self.new_best = False
        self.death_reason = ""
        self.death_timer = 0
        self.fill_city()

    def distance(self):
        """Distance run, in 'meters'"""
        return max(0, int((self.px - 100) / 30))

    def score(self):
        return self.distance() + self.coin_count * 5 + self.trick_score

    def base_speed(self, x=None):
        x = self.px if x is None else x
        return start_speed + speed_gain * min(1.0, max(0.0, x) / ramp_length)

    def difficulty(self, x):
        return min(1.0, max(0.0, x) / (ramp_length * 0.75))

    ######## city building ########

    def fill_city(self):
        while self.buildings[-1].rect.right < self.cam_x + bg_x + 600:
            self.add_building()
        keep_after = min(self.cam_x, self.chase_x) - 300
        self.buildings = [b for b in self.buildings if b.rect.right > keep_after]
        self.hazards = [h for h in self.hazards if h.rect.right > keep_after]
        self.coins = [c for c in self.coins if c.x > keep_after and not c.taken]

    def add_building(self):
        last = self.buildings[-1]
        d = self.difficulty(last.rect.right)
        if random.random() < 0.12:
            gap = 0
            top = last.rect.top + random.choice([-28, 40, 70])
        else:
            gap = random.randint(70, int(120 + 120 * d))
            rise = 70 if gap > 150 else 105  # Long jumps can't also go way up
            top = last.rect.top + random.randint(-rise, 110)
        top = max(240, min(580, top))
        width = random.randint(440, 900)
        building = Building(last.index + 1, last.rect.right + gap, width, top, gap)
        self.buildings.append(building)

        # Coins arc over big gaps
        if gap > 90:
            peak = min(last.rect.top, top) - 70
            for i in range(5):
                t = (i + 0.5) / 5
                self.coins.append(Coin(last.rect.right + gap * t, peak - math.sin(math.pi * t) * 50))
        self.populate(building, d)

    def populate(self, building, d):
        """Put hurdles, billboards, walls and coins on a rooftop"""
        top = building.rect.top
        speed_scale = self.base_speed(building.rect.x) / start_speed
        x = building.rect.left + 170
        while x < building.rect.right - 230:
            roll = random.random()
            neon = random.choice(neon_colors)
            if roll < 0.3:
                self.hazards.append(Hazard("hurdle", pygame.Rect(x, top - hurdle_h, 26, hurdle_h), neon))
                size = 26
            elif roll < 0.55 and d > 0.03:
                w = random.randint(80, 140)
                self.hazards.append(Hazard("barrier", pygame.Rect(x, top - barrier_gap - 180, w, 180), neon))
                size = w
            elif roll < 0.75 and d > 0.06 and building.rect.right - x > 320:
                h = random.randint(130, int(150 + 80 * d))
                wall = pygame.Rect(x, top - h, 48, h)
                building.walls.append(wall)
                for i in range(3):
                    self.coins.append(Coin(x + 12 + i * 12, top - h - 34 - i * 4))
                size = 48
            elif roll < 0.9:
                for i in range(5):
                    self.coins.append(Coin(x + i * 34, top - 30))
                size = 140
            else:
                size = 60
            x += size + int(random.randint(220, 360) * speed_scale)

    def solids(self):
        """(rect, building) for everything you can stand on or bump into"""
        result = []
        left, right = self.px - 200, self.px + 300
        for b in self.buildings:
            if b.rect.right > left and b.rect.left < right:
                result.append((b.rect, b))
                for wall in b.walls:
                    result.append((wall, b))
        return result

    def ground_ref(self):
        """Roof height used for the camera and for 'did you fall'"""
        cx = self.px + runner_w / 2
        prev = None
        for b in self.buildings:
            if b.rect.left <= cx < b.rect.right:
                return b.rect.top
            if b.rect.left > cx:
                return max(b.rect.top, prev.rect.top) if prev else b.rect.top
            prev = b
        return self.buildings[-1].rect.top

    ######## runner helpers ########

    def runner_h(self):
        return low_h if (self.sliding or self.roll_timer > 0) else stand_h

    def runner_rect(self, h=None):
        h = self.runner_h() if h is None else h
        return pygame.Rect(round(self.px), round(self.feet) - h, runner_w, h)

    def ceiling_blocked(self):
        """True if standing up right now would hit a billboard"""
        tall = self.runner_rect(stand_h)
        return any(h.kind == "barrier" and not h.broken and tall.colliderect(h.rect) for h in self.hazards)

    def center(self):
        return self.px + runner_w / 2, self.feet - self.runner_h() / 2

    def add_trick(self, name, x=None, y=None):
        self.combo += 1
        self.combo_timer = 170
        self.best_combo = max(self.best_combo, self.combo)
        multiplier = min(5, 1 + self.combo // 4)
        points = tricks[name] * multiplier
        self.trick_score += points
        cx, cy = self.center()
        label = f"{name} +{points}" if multiplier == 1 else f"{name} +{points}  x{multiplier}"
        self.texts.append(FloatingText(x if x is not None else cx, (y if y is not None else cy) - 40, label,
                                       lighten(neon_colors[self.combo % len(neon_colors)], 0.3), self.small_font))
        self.sounds.play(f"trick{min(7, self.combo - 1)}")

    def burst(self, x, y, color, count, power, fall=0.25):
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(0.3, 1) * power
            self.particles.append(Particle(x, y, math.cos(angle) * speed, math.sin(angle) * speed, color,
                                           random.randint(18, 40), random.randint(2, 5), fall))

    def dust(self, count, spread=2.5):
        for _ in range(count):
            self.particles.append(Particle(self.px + random.uniform(0, runner_w), self.feet - 1,
                                           random.uniform(-spread, spread * 0.4) - self.vx * 0.2, random.uniform(-2.2, -0.3),
                                           (170, 160, 190), random.randint(14, 26), random.randint(2, 4), 0.12))

    def trip(self, text):
        """Lose your speed (the swarm gets closer)"""
        self.vx = min(self.vx, 2.0)
        self.stumble = 36
        self.sliding = False
        self.combo = 0
        self.combo_timer = 0
        self.stumbles += 1
        self.shake = 10
        self.sounds.play("stumble")
        cx, cy = self.center()
        self.texts.append(FloatingText(cx, cy - 46, text, (255, 110, 120), self.font))

    def die(self, reason):
        if self.state != "playing":
            return
        self.state = "dying"
        self.death_reason = reason
        self.death_timer = 60
        self.shake = 18
        self.sounds.play("die")
        cx, cy = self.center()
        self.burst(cx, cy, runner_color, 50, 8)
        self.burst(cx, cy, swarm_color, 30, 6)
        if self.score() > self.best:
            self.best = self.score()
            self.new_best = True
            save_best(self.best)

    ######## input ########

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.state in ("playing", "paused", "dead"):
                        self.reset()
                        self.state = "title"
                    else:
                        pygame.quit()
                        sys.exit()
                elif event.key == pygame.K_m:
                    self.sounds.muted = not self.sounds.muted
                elif event.key == pygame.K_p and self.state in ("playing", "paused"):
                    self.state = "paused" if self.state == "playing" else "playing"
                elif event.key in (pygame.K_SPACE, pygame.K_w, pygame.K_UP):
                    self.press_jump()
                elif event.key in (pygame.K_s, pygame.K_DOWN):
                    self.down_timer = 12
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.press_jump()

    def press_jump(self):
        if self.state == "title":
            self.reset()
            self.state = "playing"
        elif self.state == "dead" and self.death_timer <= -30:
            self.reset()
            self.state = "playing"
        elif self.state == "playing":
            self.jump_buffer = buffer_frames

    ######## update ########

    def update(self):
        if self.state == "playing":
            self.start_timer += 1
            self.update_runner()
            self.update_swarm()
        self.update_world()

    def update_runner(self):
        keys = pygame.key.get_pressed()
        down = keys[pygame.K_s] or keys[pygame.K_DOWN]
        sprint = keys[pygame.K_d] or keys[pygame.K_RIGHT]
        brake = keys[pygame.K_a] or keys[pygame.K_LEFT]
        jump_held = keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP] or pygame.mouse.get_pressed()[0]
        self.down_timer = max(0, self.down_timer - 1)
        self.roll_timer = max(0, self.roll_timer - 1)
        self.flip_timer = max(0, self.flip_timer - 1)
        self.wall_contact = max(0, self.wall_contact - 1)

        # --- speed ---
        base = self.base_speed()
        target = base + (1.8 if sprint else 0) - (2.6 if brake else 0)
        if self.sliding:
            target = base + (1.2 if self.slide_time < 20 else -0.8)
        if self.stumble > 0:
            self.stumble -= 1
            target = 2.2
        accel = 0.3 if self.on_ground else 0.4
        self.vx += max(-accel * 2, min(accel, target - self.vx))

        # --- sliding ---
        blocked = self.ceiling_blocked()
        if self.on_ground and self.stumble == 0 and (down or (blocked and self.runner_h() == low_h)):
            if not self.sliding and self.roll_timer == 0:
                self.sounds.play("slide")
            self.sliding = True
            self.slide_time += 1
        else:
            self.sliding = False
            self.slide_time = 0

        # --- jumping ---
        if self.jump_buffer > 0:
            if self.coyote > 0 and not blocked:
                self.vy = -jump_power
                self.coyote = 0
                self.jump_buffer = 0
                self.can_cut_jump = True
                self.sliding = False
                self.sounds.play("jump")
                self.dust(6)
            elif self.wall_contact > 0 and not self.on_ground:
                self.vy = -kick_power
                self.vx = -kick_push
                self.wall_contact = 0
                self.air_jumps = 1
                self.jump_buffer = 0
                self.can_cut_jump = False
                self.kick_chain += 1
                self.sounds.play("kick")
                self.burst(self.px + runner_w, self.feet - 20, (220, 220, 255), 10, 3)
                self.add_trick("WALL KICK")
            elif self.air_jumps > 0 and not self.on_ground:
                self.vy = -air_jump_power
                self.air_jumps -= 1
                self.jump_buffer = 0
                self.can_cut_jump = True
                self.flip_timer = 26
                self.sounds.play("double")
                self.burst(self.px + runner_w / 2, self.feet, runner_color, 12, 3, 0.05)
            else:
                self.jump_buffer -= 1
        # Let go of jump early for a short hop
        if self.can_cut_jump and not jump_held and self.vy < -6:
            self.vy = -6
            self.can_cut_jump = False

        # --- move sideways ---
        was_ground = self.on_ground
        old_right = self.runner_rect().right
        self.px += self.vx
        rect = self.runner_rect()
        for solid, building in self.solids():
            if not rect.colliderect(solid):
                continue
            if old_right <= solid.left + 1:
                # Small step or ledge within reach: pop up on top of it
                reach = 12 if was_ground else 30
                if self.feet - solid.top <= reach:
                    self.feet = solid.top
                    self.vy = min(self.vy, 0)
                    if not was_ground and self.kick_chain > 0:
                        self.add_trick("MANTLE")
                        self.kick_chain = 0
                else:
                    self.px = solid.left - runner_w
                    self.vx = min(self.vx, 0)
            else:
                self.px = solid.right
                self.vx = max(self.vx, 0)
            rect = self.runner_rect()

        # --- move up/down ---
        self.on_ground = False
        if self.touching_wall and self.vy > 0:
            self.vy = min(self.vy + gravity * 0.5, 3.2)  # Wall slide
        else:
            self.vy = min(self.vy + gravity + (0.9 if down and not was_ground else 0), max_fall)
        old_feet = self.feet
        self.feet += self.vy
        rect = self.runner_rect()
        landed_on = None
        for solid, building in self.solids():
            if not rect.colliderect(solid):
                continue
            if self.vy >= 0 and old_feet <= solid.top + 1:
                impact = self.vy
                self.feet = solid.top
                self.vy = 0
                self.on_ground = True
                landed_on = building
                if not was_ground:
                    self.land(impact, down, building)
            elif self.vy < 0:
                self.feet = solid.bottom + self.runner_h()
                self.vy = 0
            rect = self.runner_rect()

        if self.on_ground:
            self.coyote = coyote_frames
            self.air_jumps = 1
            self.kick_chain = 0
            self.takeoff = landed_on.index
        else:
            self.coyote = max(0, self.coyote - 1)

        # --- touching a wall in the air? ---
        self.touching_wall = False
        if not self.on_ground:
            probe = rect.move(2, 0)
            for solid, building in self.solids():
                if probe.colliderect(solid) and rect.right <= solid.left + 2 and self.feet > solid.top + 6:
                    self.touching_wall = True
                    self.wall_contact = 6
                    if self.vy > 0 and self.frame % 4 == 0:
                        self.particles.append(Particle(solid.left, self.feet - 30, -0.5, -0.5, (200, 200, 230), 14, 2, 0))

        # --- hurdles, billboards, coins ---
        rect = self.runner_rect()
        for hazard in self.hazards:
            if hazard.broken or hazard.rect.right < self.px - 50 or hazard.rect.left > self.px + 80:
                continue
            if rect.colliderect(hazard.rect):
                hazard.broken = True
                self.burst(hazard.rect.centerx, hazard.rect.bottom - 10, (255, 150, 40) if hazard.kind == "hurdle" else hazard.color,
                           24, 6)
                self.trip("OOF!" if hazard.kind == "hurdle" else "BONK!")
            elif not hazard.passed and self.px > hazard.rect.right:
                hazard.passed = True
                self.add_trick("HURDLE" if hazard.kind == "hurdle" else "SLIDE", hazard.rect.centerx, hazard.rect.bottom - 20)

        cx, cy = self.center()
        for coin in self.coins:
            if not coin.taken and abs(coin.x - cx) < 22 and abs(coin.y - cy) < 30:
                coin.taken = True
                self.coin_count += 1
                self.sounds.play("coin")
                self.burst(coin.x, coin.y, coin_color, 8, 2.5, 0.05)

        # --- animation ---
        if self.on_ground and not self.sliding:
            self.run_phase += self.vx * 0.055
            if self.vx > 8 and self.frame % 3 == 0:
                self.dust(1)
        if self.sliding and self.frame % 2 == 0:
            self.dust(1, 4)
        if self.vx > 9 or self.flip_timer > 0:
            self.trail.append((cx, cy))
        elif self.trail:
            self.trail.popleft()

        # --- falling to your doom ---
        if self.feet > self.ground_ref() + 340:
            self.die("You fell between the buildings")

    def land(self, impact, down, building):
        if impact >= roll_impact:
            if down or self.down_timer > 0:
                self.roll_timer = 22
                self.sounds.play("roll")
                self.dust(10, 4)
                self.add_trick("ROLL")
            else:
                self.vx *= 0.45
                self.stumble = 22
                self.combo = 0
                self.combo_timer = 0
                self.stumbles += 1
                self.shake = 8
                self.sounds.play("stumble")
                self.dust(14, 4)
                cx, cy = self.center()
                self.texts.append(FloatingText(cx, cy - 46, "HARD LANDING - hold DOWN to roll!", (255, 140, 120),
                                               self.small_font))
        else:
            self.sounds.play("land")
            self.dust(5)
        if building.index == self.takeoff + 1:
            if building.gap_before >= 180:
                self.add_trick("BIG LEAP")
            elif building.gap_before >= 110:
                self.add_trick("LEAP")

    def update_swarm(self):
        """The swarm chases at a bit under your normal speed - trip up and it catches you"""
        if self.start_timer > 90:
            self.chase_x += self.base_speed() * 0.97
        self.chase_x = max(self.chase_x, self.px - 560)
        if self.px < self.chase_x:
            self.die("The swarm caught you")

    def update_world(self):
        if self.combo_timer > 0:
            self.combo_timer -= 1
            if self.combo_timer == 0:
                self.combo = 0
        self.shake = max(0, self.shake - 1)

        # Camera: keep the runner on the left third, and the roof near the bottom
        self.cam_x += (self.px - 250 + max(0, self.vx - 7) * 12 - self.cam_x) * 0.2
        target_y = min(self.ground_ref() - 430, self.feet - 240)
        self.cam_y += (target_y - self.cam_y) * 0.08
        self.fill_city()

        for particle in self.particles:
            particle.update()
        self.particles = [p for p in self.particles if p.life > 0]
        for text in self.texts:
            text.update()
        self.texts = [t for t in self.texts if t.life > 0]

    ######## drawing ########

    def draw(self):
        canvas = self.canvas
        canvas.blit(get_sky(), (0, 0))
        sun = get_sun()
        canvas.blit(sun, (bg_x // 2 - 130, 300 - self.cam_y * 0.04))
        self.draw_skyline(canvas, 0.12, 60, (40, 18, 64), 90, 230)
        self.draw_skyline(canvas, 0.3, 80, (26, 14, 48), 140, 300, windows=True)

        cam_x, cam_y = int(self.cam_x), int(self.cam_y)
        if self.shake:
            cam_x += random.randint(-self.shake, self.shake) // 2
            cam_y += random.randint(-self.shake, self.shake) // 2

        for building in self.buildings:
            building.draw(canvas, cam_x, cam_y, self.frame)
        for hazard in self.hazards:
            hazard.draw(canvas, cam_x, cam_y, self.board_font, self.frame)
        for coin in self.coins:
            if not coin.taken:
                coin.draw(canvas, cam_x, cam_y, self.frame)
        for particle in self.particles:
            particle.draw(canvas, cam_x, cam_y)
        if self.state != "dying" and self.state != "dead":
            self.draw_runner(canvas, cam_x, cam_y)
        if self.vx > 9.5 and self.state == "playing":
            self.draw_speed_lines(canvas)
        if self.state != "title":
            self.draw_swarm(canvas, cam_x)
        for text in self.texts:
            text.draw(canvas, cam_x, cam_y)

        self.screen.blit(canvas, (0, 0))
        if self.state == "title":
            self.draw_title()
        else:
            self.draw_hud()
        if self.state == "paused":
            self.draw_overlay()
            draw_glow_text(self.screen, "PAUSED", self.big_font, (255, 255, 255), (bg_x // 2, bg_y // 2 - 20))
            draw_text(self.screen, "P to keep running", self.font, (200, 210, 240), (bg_x // 2, bg_y // 2 + 40))
        elif self.state == "dead":
            self.draw_dead()
        pygame.display.update()

    def draw_skyline(self, canvas, factor, seg_w, color, low, high, windows=False):
        """Far-away buildings that scroll slower than the rooftops"""
        offset = self.cam_x * factor
        base_y = bg_y - 40 - self.cam_y * factor * 0.3
        first = int(offset // seg_w) - 1
        for k in range(first, first + bg_x // seg_w + 3):
            rng = random.Random(k * 7919 + int(factor * 100))
            h = rng.randint(low, high)
            w = seg_w - rng.randint(0, 20)
            x = k * seg_w - offset
            pygame.draw.rect(canvas, color, (x, base_y - h, w, h + 400))
            if windows:
                lit = lighten(color, 0.25)
                for _ in range(rng.randint(2, 6)):
                    wx, wy = rng.randint(6, max(7, w - 12)), rng.randint(10, h - 10)
                    canvas.fill(lit, (x + wx, base_y - h + wy, 4, 5))

    def runner_pose(self):
        """
        Joint positions for the stick-figure runner (feet at 0, 0) \n
        Returns: hip, neck, legs, arms, spin angle
        """
        spin = 0.0
        if self.roll_timer > 0 or self.flip_timer > 0:
            # Tucked ball, spinning forward
            if self.roll_timer > 0:
                spin = (1 - self.roll_timer / 22) * math.tau
            else:
                spin = (1 - self.flip_timer / 26) * math.tau
            hip = (0, -14)
            neck = (4, -28)
            legs = [limb(hip, 1.9, 11, -0.2, 11), limb(hip, 1.6, 11, -0.5, 11)]
            arms = [limb(neck, 1.2, 9, 2.2, 8), limb(neck, 0.9, 9, 2.0, 8)]
        elif self.sliding:
            hip = (0, -7)
            lean = -1.0
            neck = (hip[0] + math.sin(lean) * 17, hip[1] - math.cos(lean) * 17)
            legs = [limb(hip, 1.45, 11, 1.55, 12), limb(hip, 1.15, 11, 0.1, 11)]
            arms = [limb(neck, -0.6, 9, -0.2, 8), limb(neck, 1.3, 9, 1.6, 8)]
        elif not self.on_ground and self.touching_wall:
            hip = (0, -22)
            neck = (1, -39)
            legs = [limb(hip, 1.3, 11, 0.2, 12), limb(hip, 0.3, 11, -0.2, 12)]
            arms = [limb(neck, 2.4, 9, 2.8, 8), limb(neck, 2.0, 9, 2.6, 8)]
        elif not self.on_ground:
            hip = (0, -22)
            neck = (3, -39)
            if self.vy < 0:
                legs = [limb(hip, 1.2, 11, 0.1, 12), limb(hip, -0.2, 11, -0.8, 12)]
                arms = [limb(neck, 2.6, 9, 2.9, 8), limb(neck, -0.7, 9, -0.2, 8)]
            else:
                legs = [limb(hip, 0.6, 11, -0.1, 12), limb(hip, -0.1, 11, -0.6, 12)]
                arms = [limb(neck, 2.0, 9, 2.4, 8), limb(neck, -1.8, 9, -2.2, 8)]
        else:
            lean = 0.22 + self.vx * 0.025 if self.stumble == 0 else -0.35
            bob = abs(math.cos(self.run_phase)) * 2
            hip = (0, -21 - bob)
            neck = (hip[0] + math.sin(lean) * 17, hip[1] - math.cos(lean) * 17)
            legs, arms = [], []
            for side in (0, math.pi):
                s = math.sin(self.run_phase + side)
                thigh = s * 0.85
                legs.append(limb(hip, thigh, 11, thigh - 0.3 - 0.9 * max(0, -math.cos(self.run_phase + side)), 12))
                if self.stumble > 0:
                    flail = 2.4 + math.sin(self.frame * 0.5 + side) * 0.6
                    arms.append(limb(neck, flail, 9, flail + 0.3, 8))
                else:
                    upper = -s * 0.9 + lean
                    arms.append(limb(neck, upper, 9, upper + 1.2, 8))
        return hip, neck, legs, arms, spin

    def draw_runner(self, canvas, cam_x, cam_y):
        fx, fy = self.px + runner_w / 2 - cam_x, self.feet - cam_y
        for i, (tx, ty) in enumerate(self.trail):
            add_glow(canvas, (tx - cam_x, ty - cam_y), 6 + i, darken(runner_color, 0.25))

        hip, neck, legs, arms, spin = self.runner_pose()
        pivot = (0, -18)
        cos_a, sin_a = math.cos(spin), math.sin(spin)

        def place(point):
            dx, dy = point[0] - pivot[0], point[1] - pivot[1]
            return (fx + pivot[0] + dx * cos_a - dy * sin_a, fy + pivot[1] + dx * sin_a + dy * cos_a)

        head_dir = (neck[0] - hip[0], neck[1] - hip[1])
        length = math.hypot(*head_dir) or 1
        head = (neck[0] + head_dir[0] / length * 7, neck[1] + head_dir[1] / length * 7)
        add_glow(canvas, place(((hip[0] + neck[0]) / 2, (hip[1] + neck[1]) / 2)), 34, darken(runner_color, 0.45))

        back_color = darken(runner_color, 0.55)
        front_color = runner_color if self.stumble == 0 else mix(runner_color, (255, 120, 120), 0.6)
        hip_p, neck_p = place(hip), place(neck)
        for color, (joint, end), start in ((back_color, legs[1], hip_p), (back_color, arms[1], neck_p)):
            pygame.draw.lines(canvas, color, False, [start, place(joint), place(end)], 4)
        pygame.draw.line(canvas, front_color, hip_p, neck_p, 5)
        for color, (joint, end), start in ((front_color, legs[0], hip_p), (front_color, arms[0], neck_p)):
            pygame.draw.lines(canvas, color, False, [start, place(joint), place(end)], 4)
        head_p = place(head)
        pygame.draw.circle(canvas, front_color, head_p, 7)
        pygame.draw.circle(canvas, (255, 255, 255), head_p, 3)

    def draw_speed_lines(self, canvas):
        rng = random.Random(self.frame // 2)
        for _ in range(8):
            y = rng.randint(60, bg_y - 40)
            x = rng.randint(0, bg_x)
            length = rng.randint(40, 120)
            pygame.draw.line(canvas, (255, 230, 240), (x, y), (x - length, y), 1)

    def draw_swarm(self, canvas, cam_x):
        """A wall of red glitchy drones on the left side"""
        edge = self.chase_x - cam_x
        if edge < -40:
            return
        dark = cached(("swarm_fill",), lambda: self.make_swarm_fill())
        canvas.blit(dark, (edge - dark.get_width(), 0))
        rng = random.Random(self.frame // 3)
        for y in range(0, bg_y, 14):
            jitter = rng.randint(-18, 6)
            pygame.draw.rect(canvas, swarm_color if rng.random() < 0.7 else (255, 200, 210), (edge + jitter - 12, y, 12, 10))
        for i in range(10):
            y = (i * 61 + self.frame * 2) % bg_y
            x = edge - 30 - (i * 37) % 120 + math.sin(self.frame * 0.1 + i) * 8
            add_glow(canvas, (x, y), 16, (180, 20, 40))
            pygame.draw.circle(canvas, (255, 230, 120), (x, y), 3)

    def make_swarm_fill(self):
        width = 800
        fill = pygame.Surface((width, bg_y), pygame.SRCALPHA)
        for x in range(width):
            t = x / width
            fill.fill((60 + int(80 * t), 0, 20, int(140 + 100 * t)), (x, 0, 1, bg_y))
        return fill

    def draw_hud(self):
        draw_text(self.screen, f"{self.distance()} m", self.mid_font, (255, 255, 255), (80, 32))
        draw_text(self.screen, f"Score {self.score()}", self.font, (255, 225, 110), (80, 66))
        draw_text(self.screen, f"Coins {self.coin_count}", self.font, coin_color, (bg_x - 80, 28))
        draw_text(self.screen, f"Best {self.best}", self.small_font, (190, 200, 230), (bg_x - 80, 56))

        if self.combo >= 2:
            multiplier = min(5, 1 + self.combo // 4)
            color = lighten(neon_colors[self.combo % len(neon_colors)], 0.3)
            draw_glow_text(self.screen, f"COMBO {self.combo}  x{multiplier}", self.font, color, (bg_x // 2, 28))
            width = int(160 * self.combo_timer / 170)
            pygame.draw.rect(self.screen, color, (bg_x // 2 - 80, 46, width, 4))

        # How close is the swarm?
        gap = self.px - self.chase_x
        danger = max(0.0, min(1.0, 1 - (gap - 40) / 420))
        bar = pygame.Rect(bg_x // 2 - 100, bg_y - 26, 200, 10)
        pygame.draw.rect(self.screen, (40, 20, 40), bar)
        color = mix((255, 200, 80), swarm_color, danger)
        pygame.draw.rect(self.screen, color, (bar.x, bar.y, int(bar.w * danger), bar.h))
        pygame.draw.rect(self.screen, (120, 80, 120), bar, 1)
        label = "SWARM" if danger < 0.75 or self.frame // 8 % 2 else "RUN!"
        draw_text(self.screen, label, self.small_font, color, (bar.x - 40, bar.centery))
        if self.sounds.muted:
            draw_text(self.screen, "MUTED", self.small_font, (150, 150, 170), (bg_x - 40, bg_y - 16))

    def draw_overlay(self):
        dim = cached(("dim",), lambda: self.make_dim())
        self.screen.blit(dim, (0, 0))

    def make_dim(self):
        dim = pygame.Surface((bg_x, bg_y), pygame.SRCALPHA)
        dim.fill((6, 4, 18, 170))
        return dim

    def draw_title(self):
        self.draw_overlay()
        title = "SKYLINE SPRINT"
        x = bg_x // 2 - self.big_font.size(title)[0] // 2
        for i, letter in enumerate(title):
            color = neon_colors[i % len(neon_colors)]
            y = 100 + math.sin(self.frame * 0.06 + i * 0.5) * 7
            width = self.big_font.size(letter)[0]
            if letter != " ":
                draw_glow_text(self.screen, letter, self.big_font, color, (x + width // 2, y))
            x += width
        alpha = 150 + int(100 * math.sin(self.frame * 0.08))
        start = self.font.render("Press SPACE or click to run", True, (255, 255, 255))
        start.set_alpha(alpha)
        self.screen.blit(start, start.get_rect(center=(bg_x // 2, 168)))
        draw_text(self.screen, f"Best: {self.best}", self.font, (255, 225, 110), (bg_x // 2, 204))

        lines = [
            ("SPACE / W / UP", "Jump  (again in the air = double jump)"),
            ("Jump at a wall", "Wall kick - keep kicking to climb up"),
            ("S / DOWN", "Slide under billboards"),
            ("Hold DOWN landing", "Roll out of big drops"),
            ("D / A", "Sprint / slow down"),
        ]
        for i, (key, text) in enumerate(lines):
            y = 270 + i * 34
            draw_text(self.screen, key, self.font, (120, 230, 255), (bg_x // 2 - 150, y))
            draw_text(self.screen, text, self.small_font, (215, 210, 240), (bg_x // 2 + 120, y))
        draw_text(self.screen, "Chain tricks for combos.  Trip up and the red swarm catches you!", self.small_font,
                  (255, 150, 170), (bg_x // 2, 460))
        draw_text(self.screen, "P: pause   M: mute   Esc: quit", self.small_font, (130, 125, 170), (bg_x // 2, bg_y - 14),
                  shadow=False)

    def draw_dead(self):
        self.draw_overlay()
        draw_glow_text(self.screen, "WIPEOUT", self.big_font, (255, 90, 150), (bg_x // 2, 110))
        draw_text(self.screen, self.death_reason, self.font, (220, 200, 230), (bg_x // 2, 170))
        rows = [
            ("Distance", f"{self.distance()} m"),
            ("Coins", f"{self.coin_count} x 5"),
            ("Tricks", str(self.trick_score)),
            ("Best combo", str(self.best_combo)),
            ("Stumbles", str(self.stumbles)),
        ]
        for i, (label, value) in enumerate(rows):
            y = 220 + i * 34
            draw_text(self.screen, label, self.font, (170, 185, 225), (bg_x // 2 - 80, y))
            draw_text(self.screen, value, self.font, (255, 255, 255), (bg_x // 2 + 80, y))
        draw_glow_text(self.screen, f"SCORE {self.score()}", self.mid_font, (255, 225, 110), (bg_x // 2, 410))
        if self.new_best and self.frame // 15 % 2 == 0:
            draw_glow_text(self.screen, "NEW BEST!", self.font, (140, 255, 150), (bg_x // 2, 455))
        elif not self.new_best:
            draw_text(self.screen, f"Best: {self.best}", self.font, (170, 185, 225), (bg_x // 2, 455))
        if self.death_timer <= -30:
            draw_text(self.screen, "Space / click to run again      Esc: title", self.font, (200, 210, 240), (bg_x // 2, 520))

    ######## main loop ########

    def step(self):
        self.frame += 1
        self.handle_events()
        if self.state == "title":
            # Demo: jog in place while the city drifts by
            self.run_phase += 0.35
            self.cam_x += 2
            self.px = self.cam_x + 250
            self.feet = self.buildings[0].rect.top
            self.chase_x = self.px - 380
            self.fill_city()
        elif self.state == "playing":
            self.update()
        elif self.state in ("dying", "dead"):
            self.death_timer -= 1
            if self.death_timer <= 0:
                self.state = "dead"
            self.update_world()
        pygame.mouse.set_visible(self.state != "playing")
        self.draw()

    def run(self):
        while True:
            self.clock.tick(60)  # set fps
            self.step()

######################主程式/ main program######################

def main():
    pygame.mixer.pre_init(22050, -16, 1, 512)
    pygame.init()
    pygame.display.set_caption("Skyline Sprint")
    screen = pygame.display.set_mode((bg_x, bg_y))
    Game(screen).run()


if __name__ == "__main__":
    main()
