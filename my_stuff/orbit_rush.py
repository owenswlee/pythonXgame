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
BEST_FILE = os.path.join(GAME_DIR, "orbit_best.txt")

launch_speed = 7.2
max_speed = 11
gravity = 16  # How hard planets pull on you while flying
gravity_range = 260
start_y = 450  # World Y of the first planet (smaller Y = higher up)

planet_colors = [
    (255, 120, 90),
    (255, 190, 80),
    (110, 220, 140),
    (80, 180, 255),
    (150, 120, 255),
    (240, 110, 200),
    (90, 220, 210),
]

# Background color changes as you climb: (top color, bottom color)
sky_stages = [
    ((6, 10, 32), (14, 24, 62)),   # Deep blue
    ((20, 6, 42), (50, 16, 76)),   # Purple
    ((30, 4, 22), (74, 18, 44)),   # Crimson
    ((2, 24, 30), (8, 52, 64)),    # Teal
]

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
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))


def get_glow(radius, color):
    """Soft round light on black. Blit with BLEND_ADD to brighten what's under it"""
    def build():
        surf = pygame.Surface((radius * 2, radius * 2))
        for r in range(radius, 0, -1):
            pygame.draw.circle(surf, darken(color, (1 - r / radius) ** 2), (radius, radius), r)
        return surf
    return cached(("glow", radius, color), build)


def add_glow(surface, center, radius, color):
    radius = max(2, int(radius))
    surface.blit(get_glow(radius, color), (int(center[0]) - radius, int(center[1]) - radius),
                 special_flags=pygame.BLEND_ADD)


def make_planet_sprite(radius, color, seed):
    """
    A shaded planet with soft stripes \n
    radius: / Planet size \n
    seed: / Different seeds give different stripes
    """
    rng = random.Random(seed)
    size = radius * 2 + 2
    center = radius + 1
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    dark = darken(color, 0.35)
    light = lighten(color, 0.6)
    for r in range(radius, 0, -1):
        t = 1 - r / radius
        shade = mix(dark, color, t * 2) if t < 0.5 else mix(color, light, (t - 0.5) * 2)
        shift = t * radius * 0.4
        pygame.draw.circle(surf, shade, (center - shift, center - shift), r)

    # Stripes like a gas giant
    stripes = pygame.Surface((size, size), pygame.SRCALPHA)
    for _ in range(rng.randint(2, 5)):
        y = rng.uniform(0.15, 0.85) * size
        h = rng.uniform(2, radius * 0.3)
        tint = (255, 255, 255, 28) if rng.random() < 0.5 else (0, 0, 20, 45)
        pygame.draw.ellipse(stripes, tint, (-radius * 0.3, y, size * 1.6, h))
    mask = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(mask, (255, 255, 255, 255), (center, center), radius)
    stripes.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    surf.blit(stripes, (0, 0))
    return surf


def make_ring_sprite(radius, color):
    """A flat ring around a planet (drawn in two halves: behind and in front)"""
    w, h = int(radius * 4.2), int(radius * 1.3)
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    for i, alpha in ((0, 200), (4, 120), (8, 70)):
        pygame.draw.ellipse(surf, (*lighten(color, 0.4), alpha), (i, i * 0.3, w - i * 2, h - i * 0.6), 3)
    return surf


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


def get_sky(stage):
    """
    Background gradient for a height (stage 0.0, 1.0, 2.0... blends between sky_stages)
    """
    index = int(stage) % len(sky_stages)
    t = round((stage - int(stage)) * 16) / 16  # Rounded so the cache stays small

    def build():
        top_a, bottom_a = sky_stages[index]
        top_b, bottom_b = sky_stages[(index + 1) % len(sky_stages)]
        top, bottom = mix(top_a, top_b, t), mix(bottom_a, bottom_b, t)
        small = pygame.Surface((1, 32))
        for y in range(32):
            small.set_at((0, y), mix(top, bottom, y / 31))
        return pygame.transform.smoothscale(small, (bg_x, bg_y))
    return cached(("sky", index, t), build)

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
        noise = random.Random(7)
        fade = lambda t, d: (1 - t / d) ** 2
        self.sounds["launch"] = make_sound(0.14, lambda t, d: sweep(t, d, 250, 900) * fade(t, d), 0.25)
        # Landing chimes get higher as your hop chain grows
        for k in range(8):
            f = 440 * 2 ** (k * 2 / 12)
            self.sounds[f"land{k}"] = make_sound(
                0.22, lambda t, d, f=f: (math.sin(2 * math.pi * f * t) + 0.5 * math.sin(3 * math.pi * f * t)) * fade(t, d), 0.22)
        self.sounds["gem"] = make_sound(
            0.18, lambda t, d: math.sin(2 * math.pi * (1320 if t < 0.06 else 1760) * t) * fade(t, d), 0.2)
        self.sounds["tick"] = make_sound(0.04, lambda t, d: math.sin(2 * math.pi * 1000 * t) * fade(t, d), 0.18)
        self.sounds["boom"] = make_sound(
            0.6, lambda t, d: (math.sin(2 * math.pi * (70 - 40 * t) * t) * 0.6 + noise.uniform(-1, 1) * 0.4) * fade(t, d), 0.6)
        self.sounds["die"] = make_sound(0.8, lambda t, d: sweep(t, d, 600, 60) * (1 - t / d), 0.3)

    def play(self, name):
        if not self.muted and name in self.sounds:
            self.sounds[name].play()

######################物件類別/ object class######################

class Planet:
    def __init__(self, x, y, radius, color, move_amp=0):
        """
        x, y: / Center (world coordinates) \n
        radius: / Planet size \n
        move_amp: / How far it slides left and right (0 = stays still)
        """
        self.x = self.home_x = x
        self.y = y
        self.radius = int(radius)
        self.orbit_r = int(radius) + 34
        self.color = color
        self.move_amp = move_amp
        self.move_phase = random.uniform(0, math.tau)
        self.life = None  # Frames left before it collapses (starts when you land)
        self.max_life = 1
        self.dead = False
        seed = random.randrange(10 ** 6)
        self.sprite = make_planet_sprite(self.radius, color, seed)
        self.ring = make_ring_sprite(self.radius, color) if random.random() < 0.35 else None

    def update(self, frame):
        if self.move_amp:
            self.x = self.home_x + math.sin(frame * 0.018 + self.move_phase) * self.move_amp
        if self.life is not None and not self.dead:
            self.life -= 1

    def draw(self, surface, cam_y, frame, is_current):
        sx, sy = self.x, self.y - cam_y
        if sy < -150 or sy > bg_y + 150:
            return

        # Shake when it's about to collapse
        danger = self.life is not None and self.life < 70
        if danger:
            sx += random.uniform(-2, 2)
            sy += random.uniform(-2, 2)

        # Orbit path
        orbit_color = darken(self.color, 0.45) if not is_current else darken(self.color, 0.8)
        dots = 36
        for i in range(dots):
            a = i / dots * math.tau + frame * 0.004
            pygame.draw.circle(surface, orbit_color, (sx + math.cos(a) * self.orbit_r, sy + math.sin(a) * self.orbit_r), 1)

        add_glow(surface, (sx, sy), self.radius * 1.9, darken(self.color, 0.35))
        if self.ring:
            rect = self.ring.get_rect(center=(sx, sy))
            half = rect.height // 2
            surface.blit(self.ring, rect, (0, 0, rect.width, half))  # Back half
        surface.blit(self.sprite, self.sprite.get_rect(center=(sx, sy)))
        if self.ring:
            surface.blit(self.ring, (rect.x, rect.y + half), (0, half, rect.width, rect.height - half))  # Front half

        if danger and frame // 6 % 2 == 0:
            add_glow(surface, (sx, sy), self.radius * 1.3, (120, 20, 20))

        # Countdown ring
        if self.life is not None:
            left = max(0.0, self.life / self.max_life)
            color = mix((255, 60, 60), (110, 240, 150), left)
            r = self.orbit_r + 9
            box = pygame.Rect(sx - r, sy - r, r * 2, r * 2)
            if left > 0.01:
                pygame.draw.arc(surface, color, box, math.pi / 2, math.pi / 2 + math.tau * left, 3)


class Gem:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.phase = random.uniform(0, math.tau)
        self.taken = False

    def draw(self, surface, cam_y, frame):
        sx = self.x
        sy = self.y - cam_y + math.sin(frame * 0.08 + self.phase) * 4
        spin = frame * 0.05 + self.phase
        add_glow(surface, (sx, sy), 22, (110, 95, 20))
        points = []
        for i in range(8):
            r = 11 if i % 2 == 0 else 4
            a = spin + i * math.pi / 4
            points.append((sx + math.cos(a) * r, sy + math.sin(a) * r))
        pygame.draw.polygon(surface, (255, 225, 110), points)
        pygame.draw.circle(surface, (255, 255, 230), (sx, sy), 2)


class Asteroid:
    def __init__(self, x, y, speed):
        self.x = x
        self.y = y
        self.vx = speed
        self.radius = random.randint(13, 22)
        self.angle = random.uniform(0, math.tau)
        self.spin = random.uniform(-0.04, 0.04)
        # Bumpy outline
        self.shape = [(i / 9 * math.tau, self.radius * random.uniform(0.75, 1.1)) for i in range(9)]

    def update(self):
        self.x += self.vx
        self.angle += self.spin
        # Wrap around the sides of the screen
        if self.x < -40:
            self.x = bg_x + 40
        elif self.x > bg_x + 40:
            self.x = -40

    def draw(self, surface, cam_y):
        sx, sy = self.x, self.y - cam_y
        points = [(sx + math.cos(a + self.angle) * r, sy + math.sin(a + self.angle) * r) for a, r in self.shape]
        add_glow(surface, (sx, sy), self.radius * 1.8, (60, 25, 15))
        pygame.draw.polygon(surface, (95, 80, 78), points)
        pygame.draw.polygon(surface, (160, 140, 130), points, 2)
        pygame.draw.circle(surface, (70, 58, 58), (sx + self.radius * 0.25, sy - self.radius * 0.2), self.radius * 0.25)


class Particle:
    def __init__(self, x, y, vx, vy, color, life, size=3):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.color = color
        self.life = self.max_life = life
        self.size = size

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vx *= 0.96
        self.vy *= 0.96
        self.life -= 1

    def draw(self, surface, cam_y):
        t = self.life / self.max_life
        add_glow(surface, (self.x, self.y - cam_y), self.size * 3 * t + 2, darken(self.color, t * 0.8))


class FloatingText:
    def __init__(self, x, y, text, color, font):
        self.x, self.y = x, y
        self.text = text
        self.color = color
        self.font = font
        self.life = 50

    def update(self):
        self.y -= 0.8
        self.life -= 1

    def draw(self, surface, cam_y):
        image = self.font.render(self.text, True, self.color)
        image.set_alpha(min(255, self.life * 8))
        surface.blit(image, image.get_rect(center=(self.x, self.y - cam_y)))

######################定義函式區/ define functions######################

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
        self.big_font = pygame.font.Font(None, 104)
        self.mid_font = pygame.font.Font(None, 54)
        self.font = pygame.font.Font(None, 32)
        self.small_font = pygame.font.Font(None, 24)

        # Parallax star layers: (how fast they scroll, stars)
        self.star_layers = []
        for factor, count, size, shade in ((0.12, 70, 1, 70), (0.3, 45, 1, 140), (0.55, 22, 2, 210)):
            stars = [(random.uniform(0, bg_x), random.uniform(0, bg_y)) for _ in range(count)]
            self.star_layers.append((factor, stars, size, shade))

        self.best = load_best()
        self.frame = 0
        self.reset()
        self.state = "title"  # title, playing, paused, dying, dead

    ######## game flow ########

    def reset(self):
        self.planets = [Planet(bg_x / 2, start_y, 36, planet_colors[3])]
        self.gems = []
        self.asteroids = []
        self.particles = []
        self.texts = []
        self.shockwaves = []
        self.trail = deque(maxlen=22)
        self.cam_y = 0.0
        self.void_y = start_y + 420
        self.shake = 0
        self.gem_score = 0
        self.hop_score = 0
        self.chain = 0
        self.top_y = start_y
        self.new_best = False

        first = self.planets[0]
        self.orbit = first
        self.angle = -math.pi / 2
        self.dir = 1
        self.ang_speed = 0.05
        self.orbit_cur_r = first.orbit_r
        self.orbit_time = 0
        self.last_planet = None
        self.leave_timer = 0
        self.px, self.py = first.x, first.y - first.orbit_r
        self.vx = self.vy = 0.0
        while self.planets[-1].y > self.cam_y - 500:
            self.add_planet()

    def climb(self):
        """How far you've climbed, in 'meters'"""
        return max(0, int((start_y - self.top_y) / 10))

    def score(self):
        return self.climb() + self.gem_score + self.hop_score

    def difficulty(self):
        """0 at the start, grows by 1 every 100 meters"""
        return (start_y - self.planets[-1].y) / 1000

    def add_planet(self):
        """Make the next planet above the highest one (plus gems and asteroids between)"""
        prev = self.planets[-1]
        d = self.difficulty()
        radius = max(16, random.uniform(20, 40) - d * 2)
        move = random.uniform(40, 120) if d > 1.2 and random.random() < min(0.55, 0.15 + d * 0.08) else 0
        y = prev.y - random.uniform(175, 235) - min(d * 10, 55)
        x = prev.home_x
        for _ in range(30):
            x = random.uniform(90 + move, bg_x - 90 - move)
            if 70 < abs(x - prev.home_x) < 330:
                break
        color = random.choice([c for c in planet_colors if c != prev.color])  # Neighbors never match
        planet = Planet(x, y, radius, color, move)
        self.planets.append(planet)

        mid_x, mid_y = (prev.home_x + x) / 2, (prev.y + y) / 2
        if random.random() < 0.75:
            gem = Gem(mid_x + random.uniform(-60, 60), mid_y + random.uniform(-20, 20))
            if all(math.hypot(gem.x - p.home_x, gem.y - p.y) > p.orbit_r + p.move_amp + 14 for p in (prev, planet)):
                self.gems.append(gem)

        if d > 0.8 and random.random() < min(0.7, 0.25 + d * 0.1):
            rock = Asteroid(random.uniform(0, bg_x), mid_y, random.choice((-1, 1)) * random.uniform(1, 2.2 + d * 0.3))
            if all(abs(rock.y - p.y) > p.orbit_r + rock.radius + 8 for p in (prev, planet)):
                self.asteroids.append(rock)

    def launch(self):
        if self.state != "playing" or self.orbit is None:
            return
        tx, ty = -math.sin(self.angle) * self.dir, math.cos(self.angle) * self.dir
        self.vx, self.vy = tx * launch_speed, ty * launch_speed
        # Quick hops keep your chain going
        self.chain = self.chain + 1 if self.orbit_time < 75 else 0
        self.last_planet = self.orbit
        self.leave_timer = 25
        self.orbit = None
        self.sounds.play("launch")
        for _ in range(12):
            self.particles.append(Particle(self.px, self.py, -tx * random.uniform(1, 4) + random.uniform(-1, 1),
                                           -ty * random.uniform(1, 4) + random.uniform(-1, 1), (120, 220, 255), 25))

    def capture(self, planet):
        dx, dy = self.px - planet.x, self.py - planet.y
        dist = max(1.0, math.hypot(dx, dy))
        self.orbit = planet
        self.angle = math.atan2(dy, dx)
        # Keep spinning the way you were already moving around it
        self.dir = 1 if dx * self.vy - dy * self.vx > 0 else -1
        speed = math.hypot(self.vx, self.vy)
        self.ang_speed = max(0.04, min(0.08, speed / planet.orbit_r))
        self.orbit_cur_r = dist
        self.orbit_time = 0
        self.shake = max(self.shake, 4)
        self.sounds.play(f"land{min(self.chain, 7)}")

        if planet.life is None:
            # First time landing here: start its collapse timer
            planet.life = planet.max_life = int(max(110, 300 - self.difficulty() * 28))
            points = 10 * (self.chain + 1)
            self.hop_score += points
            label = f"+{points}" if self.chain == 0 else f"+{points}  CHAIN x{self.chain + 1}"
            self.texts.append(FloatingText(planet.x, planet.y - planet.orbit_r - 24, label, (150, 240, 255), self.font))
        for i in range(18):
            a = i / 18 * math.tau
            self.particles.append(Particle(planet.x + math.cos(a) * planet.orbit_r, planet.y + math.sin(a) * planet.orbit_r,
                                           math.cos(a) * 1.5, math.sin(a) * 1.5, planet.color, 22, 2))

    def explode(self, x, y, color, count, power):
        for _ in range(count):
            a = random.uniform(0, math.tau)
            s = random.uniform(0.5, power)
            self.particles.append(Particle(x, y, math.cos(a) * s, math.sin(a) * s, color, random.randint(25, 55),
                                           random.uniform(2, 5)))
        self.shockwaves.append([x, y, 0, color])

    def die(self, reason):
        if self.state != "playing":
            return
        self.state = "dying"
        self.death_timer = 70
        self.death_reason = reason
        self.shake = 22
        self.sounds.play("die")
        self.explode(self.px, self.py, (120, 220, 255), 60, 7)
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
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.press()
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_UP, pygame.K_w):
                    self.press()
                elif event.key == pygame.K_p and self.state in ("playing", "paused"):
                    self.state = "paused" if self.state == "playing" else "playing"
                elif event.key == pygame.K_m:
                    self.sounds.muted = not self.sounds.muted
                elif event.key == pygame.K_ESCAPE:
                    if self.state == "title":
                        pygame.quit()
                        sys.exit()
                    self.reset()
                    self.state = "title"

    def press(self):
        if self.state == "title":
            self.reset()
            self.state = "playing"
        elif self.state == "playing":
            self.launch()
        elif self.state == "paused":
            self.state = "playing"
        elif self.state == "dead" and self.death_timer <= -30:
            self.reset()
            self.state = "playing"

    ######## update ########

    def update(self):
        for planet in self.planets:
            was_alive = not planet.dead
            planet.update(self.frame)
            if was_alive and planet.life is not None and planet.life <= 0:
                planet.dead = True
                self.explode(planet.x, planet.y, planet.color, 70, 6)
                self.shake = max(self.shake, 12)
                self.sounds.play("boom")
                if self.orbit is planet:
                    self.orbit = None
                    self.die("Your planet collapsed!")

        for rock in self.asteroids:
            rock.update()

        if self.state == "playing":
            self.update_player()
        self.update_world()

    def update_player(self):
        if self.orbit:
            planet = self.orbit
            self.orbit_time += 1
            self.angle += self.ang_speed * self.dir
            self.orbit_cur_r += (planet.orbit_r - self.orbit_cur_r) * 0.12
            self.px = planet.x + math.cos(self.angle) * self.orbit_cur_r
            self.py = planet.y + math.sin(self.angle) * self.orbit_cur_r
            if planet.life is not None and planet.life < 90 and planet.life % 15 == 0:
                self.sounds.play("tick")
        else:
            if self.leave_timer > 0:
                self.leave_timer -= 1
            # Gravity bends your path
            for planet in self.planets:
                if planet.dead:
                    continue
                dx, dy = planet.x - self.px, planet.y - self.py
                d2 = dx * dx + dy * dy
                if d2 < gravity_range ** 2:
                    d = math.sqrt(d2)
                    pull = gravity * planet.radius / max(d2, 900)
                    self.vx += dx / d * pull
                    self.vy += dy / d * pull
            speed = math.hypot(self.vx, self.vy)
            if speed > max_speed:
                self.vx *= max_speed / speed
                self.vy *= max_speed / speed
            self.px += self.vx
            self.py += self.vy

            for planet in self.planets:
                if planet.dead or (planet is self.last_planet and self.leave_timer > 0):
                    continue
                if math.hypot(self.px - planet.x, self.py - planet.y) < planet.orbit_r:
                    self.capture(planet)
                    break

            if self.px < -25 or self.px > bg_x + 25:
                self.die("Drifted off into space!")
            elif self.py - self.cam_y > bg_y + 30:
                self.die("Fell out of the sky!")

        self.trail.append((self.px, self.py))
        self.top_y = min(self.top_y, self.py)

        for gem in self.gems:
            if not gem.taken and math.hypot(gem.x - self.px, gem.y - self.py) < 22:
                gem.taken = True
                points = 25 * (self.chain + 1)
                self.gem_score += points
                self.sounds.play("gem")
                self.explode(gem.x, gem.y, (255, 220, 100), 16, 3)
                self.texts.append(FloatingText(gem.x, gem.y - 20, f"+{points}", (255, 225, 110), self.font))

        for rock in self.asteroids:
            if math.hypot(rock.x - self.px, rock.y - self.py) < rock.radius + 6:
                self.explode(rock.x, rock.y, (200, 150, 120), 30, 4)
                self.die("Smashed by an asteroid!")
                break

        if self.py > self.void_y - 8:
            self.die("Swallowed by the void!")

        # Camera only moves up
        target = self.py - bg_y * 0.6
        if target < self.cam_y:
            self.cam_y += (target - self.cam_y) * 0.06

        # The void rises faster as you climb, and never falls too far behind
        self.void_y -= min(1.7, 0.35 + self.difficulty() * 0.13)
        self.void_y = min(self.void_y, self.cam_y + bg_y + 140)

    def update_world(self):
        while self.planets[-1].y > self.cam_y - 500:
            self.add_planet()
        bottom = self.cam_y + bg_y + 300
        self.planets = [p for p in self.planets if p.y < bottom and not (p.dead and p is not self.orbit)] or self.planets[-1:]
        self.gems = [g for g in self.gems if not g.taken and g.y < bottom]
        self.asteroids = [a for a in self.asteroids if a.y < bottom]

        # Embers rising out of the void
        if self.frame % 3 == 0 and self.void_y - self.cam_y < bg_y + 40:
            self.particles.append(Particle(random.uniform(0, bg_x), self.void_y, random.uniform(-0.3, 0.3),
                                           random.uniform(-2.5, -0.8), (255, 70, 160), 40, 2))
        for item in self.particles + self.texts:
            item.update()
        self.particles = [p for p in self.particles if p.life > 0]
        self.texts = [t for t in self.texts if t.life > 0]
        for wave_ in self.shockwaves:
            wave_[2] += 1
        self.shockwaves = [w for w in self.shockwaves if w[2] < 30]

    ######## drawing ########

    def draw(self):
        canvas = self.canvas
        canvas.blit(get_sky(-self.cam_y / 3000), (0, 0))
        for factor, stars, size, shade in self.star_layers:
            for x, y in stars:
                sy = (y - self.cam_y * factor) % bg_y
                twinkle = shade if (x * 7 + self.frame // 8) % 23 else shade // 2
                pygame.draw.circle(canvas, (twinkle, twinkle, min(255, twinkle + 40)), (x, sy), size)

        current = self.orbit if self.state == "playing" else None
        for planet in self.planets:
            if not planet.dead:
                planet.draw(canvas, self.cam_y, self.frame, planet is current)
        for gem in self.gems:
            gem.draw(canvas, self.cam_y, self.frame)
        for rock in self.asteroids:
            rock.draw(canvas, self.cam_y)
        for x, y, age, color in self.shockwaves:
            pygame.draw.circle(canvas, lighten(color, 0.3), (x, y - self.cam_y), 10 + age * 5, max(1, 6 - age // 5))

        if self.state in ("playing", "paused", "title"):
            if self.orbit and self.state == "playing":
                self.draw_aim(canvas)
            self.draw_player(canvas)

        for particle in self.particles:
            particle.draw(canvas, self.cam_y)
        for text in self.texts:
            text.draw(canvas, self.cam_y)
        self.draw_void(canvas)

        offset = (0, 0)
        if self.shake > 0:
            power = self.shake // 2 + 1
            offset = (random.randint(-power, power), random.randint(-power, power))
            self.shake -= 1
        self.screen.fill((0, 0, 0))
        self.screen.blit(canvas, offset)

        if self.state == "title":
            self.draw_title()
        else:
            self.draw_hud()
            if self.state == "paused":
                self.draw_overlay()
                draw_glow_text(self.screen, "PAUSED", self.big_font, (150, 210, 255), (bg_x // 2, bg_y // 2 - 20))
                draw_text(self.screen, "Press P to keep flying", self.font, (190, 200, 230), (bg_x // 2, bg_y // 2 + 50))
            elif self.state == "dead":
                self.draw_dead()
        pygame.display.flip()

    def draw_player(self, canvas):
        # Comet tail
        for i, (x, y) in enumerate(self.trail):
            t = (i + 1) / len(self.trail)
            add_glow(canvas, (x, y - self.cam_y), 3 + 9 * t, darken((60, 160, 255), t * 0.7))
        sx, sy = self.px, self.py - self.cam_y
        pulse = 1 + 0.15 * math.sin(self.frame * 0.3)
        add_glow(canvas, (sx, sy), 26 * pulse, (40, 110, 160))
        pygame.draw.circle(canvas, (200, 245, 255), (sx, sy), 6)
        pygame.draw.circle(canvas, (255, 255, 255), (sx - 1, sy - 1), 3)

    def draw_aim(self, canvas):
        """Dotted preview of where you'll fly if you launch right now"""
        tx, ty = -math.sin(self.angle) * self.dir, math.cos(self.angle) * self.dir
        x, y = self.px, self.py
        vx, vy = tx * launch_speed, ty * launch_speed
        for step in range(36):
            for planet in self.planets:
                if planet.dead:
                    continue
                dx, dy = planet.x - x, planet.y - y
                d2 = dx * dx + dy * dy
                if d2 < gravity_range ** 2:
                    d = math.sqrt(d2)
                    pull = gravity * planet.radius / max(d2, 900)
                    vx += dx / d * pull
                    vy += dy / d * pull
            x += vx
            y += vy
            if step % 3 == 0:
                fade = 1 - step / 36
                pygame.draw.circle(canvas, darken((150, 220, 255), fade), (x, y - self.cam_y), 2)

    def draw_void(self, canvas):
        top = self.void_y - self.cam_y
        if top > bg_y + 40:
            return
        points = [(0, bg_y)]
        for x in range(0, bg_x + 20, 20):
            wave_y = top + math.sin(x * 0.03 + self.frame * 0.08) * 8 + math.sin(x * 0.071 - self.frame * 0.05) * 5
            points.append((x, wave_y))
        points.append((bg_x, bg_y))
        glow = cached(("void_glow",), lambda: self.make_void_glow())
        canvas.blit(glow, (0, top - 90), special_flags=pygame.BLEND_ADD)
        pygame.draw.polygon(canvas, (40, 0, 30), points)
        pygame.draw.lines(canvas, (255, 80, 170), False, points[1:-1], 3)

    def make_void_glow(self):
        surf = pygame.Surface((bg_x, 100))
        for y in range(100):
            pygame.draw.line(surf, darken((140, 20, 90), (y / 100) ** 2), (0, y), (bg_x, y))
        return surf

    def draw_hud(self):
        draw_text(self.screen, f"{self.climb()} m", self.mid_font, (255, 255, 255), (90, 34))
        draw_text(self.screen, f"Score {self.score()}", self.font, (255, 225, 110), (90, 72))
        draw_text(self.screen, f"Best {self.best}", self.font, (170, 190, 230), (bg_x - 80, 30))
        if self.chain > 0 and self.state == "playing":
            draw_glow_text(self.screen, f"CHAIN x{self.chain + 1}", self.font, (120, 230, 255), (bg_x - 80, 66))
        if self.sounds.muted:
            draw_text(self.screen, "MUTED", self.small_font, (150, 150, 170), (bg_x - 40, bg_y - 16))

    def draw_overlay(self):
        dim = cached(("dim",), lambda: self.make_dim())
        self.screen.blit(dim, (0, 0))

    def make_dim(self):
        dim = pygame.Surface((bg_x, bg_y), pygame.SRCALPHA)
        dim.fill((4, 6, 18, 165))
        return dim

    def draw_title(self):
        title = "ORBIT RUSH"
        x = bg_x // 2 - 230
        for i, letter in enumerate(title):
            color = planet_colors[i % len(planet_colors)]
            y = 120 + math.sin(self.frame * 0.06 + i * 0.5) * 8
            width = self.big_font.size(letter)[0]
            draw_glow_text(self.screen, letter, self.big_font, color, (x + width // 2, y))
            x += width
        alpha = 150 + int(100 * math.sin(self.frame * 0.08))
        start = self.font.render("Press SPACE or click to launch", True, (255, 255, 255))
        start.set_alpha(alpha)
        self.screen.blit(start, start.get_rect(center=(bg_x // 2, 190)))

        lines = [
            "Tap to fling yourself off your planet - gravity bends your path",
            "Planets collapse after you land, so keep hopping!",
            "Grab gold stars, dodge asteroids, and outrun the rising void",
            "Hop fast to build a CHAIN for bonus points",
        ]
        for i, line in enumerate(lines):
            draw_text(self.screen, line, self.small_font, (180, 195, 235), (bg_x // 2, 488 + i * 24))
        draw_text(self.screen, f"Best: {self.best}", self.font, (255, 225, 110), (bg_x // 2, 228))
        draw_text(self.screen, "P: pause   M: mute   Esc: quit", self.small_font, (110, 125, 165), (bg_x // 2, bg_y - 12),
                  shadow=False)

    def draw_dead(self):
        self.draw_overlay()
        draw_glow_text(self.screen, "LOST IN SPACE", self.big_font, (255, 90, 150), (bg_x // 2, 140))
        draw_text(self.screen, self.death_reason, self.font, (220, 200, 230), (bg_x // 2, 205))
        rows = [("Climbed", f"{self.climb()} m"), ("Hop bonus", str(self.hop_score)), ("Star bonus", str(self.gem_score))]
        for i, (label, value) in enumerate(rows):
            y = 265 + i * 38
            draw_text(self.screen, label, self.font, (170, 185, 225), (bg_x // 2 - 80, y))
            draw_text(self.screen, value, self.font, (255, 255, 255), (bg_x // 2 + 80, y))
        draw_glow_text(self.screen, f"SCORE {self.score()}", self.mid_font, (255, 225, 110), (bg_x // 2, 400))
        if self.new_best and self.frame // 15 % 2 == 0:
            draw_glow_text(self.screen, "NEW BEST!", self.font, (120, 240, 160), (bg_x // 2, 445))
        elif not self.new_best:
            draw_text(self.screen, f"Best: {self.best}", self.font, (170, 185, 225), (bg_x // 2, 445))
        if self.death_timer <= -30:
            draw_text(self.screen, "Space / click to fly again      Esc: title", self.font, (200, 210, 240), (bg_x // 2, 520))

    ######## main loop ########

    def step(self):
        self.frame += 1
        self.handle_events()
        if self.state == "title":
            # Demo: spin around the first planet
            self.cam_y = 70
            self.angle += 0.03
            planet = self.planets[0]
            self.px = planet.x + math.cos(self.angle) * planet.orbit_r
            self.py = planet.y + math.sin(self.angle) * planet.orbit_r
            self.trail.append((self.px, self.py))
            self.update_world()
        elif self.state == "playing":
            self.update()
        elif self.state in ("dying", "dead"):
            self.death_timer -= 1
            if self.death_timer <= 0:
                self.state = "dead"
            self.update()
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
    pygame.display.set_caption("Orbit Rush")
    screen = pygame.display.set_mode((bg_x, bg_y))
    Game(screen).run()


if __name__ == "__main__":
    main()
