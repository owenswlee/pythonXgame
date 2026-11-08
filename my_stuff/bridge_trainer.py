######################載入套件/ import packages######################

import json
import math
import os
import random
import tempfile
import time
import wave
from array import array
from collections import deque

from PIL import Image
from ursina import (Ursina, Entity, Text, Sky, Mesh, Texture, Button, Slider, Shader, Vec2, camera, color,
                    held_keys, mouse, window, application, Vec3, destroy)

######################遊戲常數/ game constants######################

GAME_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_FILE = os.path.join(GAME_DIR, "bridge_save.json")

# Movement works like classic block-game physics: 20 ticks per second, distances in blocks per tick
tick_length = 0.05
player_half_w = 0.3      # 0.6 blocks wide
player_height = 1.8      # Sneaking doesn't change your hitbox, only your eyes
stand_eye = 1.62
sneak_eye = 1.54
walk_accel = 0.1         # Ground movement speed attribute
sprint_accel = 0.13
air_accel = 0.02
air_sprint_accel = 0.026
sneak_multiplier = 0.3
ground_slip = 0.6 * 0.91  # Normal block slipperiness * air drag
air_slip = 0.91
gravity = 0.08
air_drag = 0.98
jump_power = 0.42
sprint_jump_boost = 0.2
reach = 4.5
place_delay = 4          # Ticks between blocks while holding right click
void_y = -30

# Settings you can change on the settings page (saved between games)
DEFAULT_SETTINGS = {
    "sensitivity": 40,
    "fov": 70,
    "volume": 80,
    "view_bob": True,
    "sprint_fov": True,     # Zoom out a little while sprinting
    "ghost": True,
    "sneak_toggle": False,  # False = hold Shift, True = press Shift to switch
    "sprint_toggle": False,
    "show_fps": True,
    "show_splits": True,
    "show_hand": True,
    "crosshair": "White",
    "fullscreen": False,
}

# Rebindable controls: action -> key name (as Ursina names it)
DEFAULT_KEYS = {
    "forward": "w", "back": "s", "left": "a", "right": "d",
    "jump": "space", "sneak": "left shift", "sprint": "left control", "reset": "r",
}
KEY_LABELS = {"forward": "Forward", "back": "Back", "left": "Left", "right": "Right",
              "jump": "Jump", "sneak": "Sneak", "sprint": "Sprint", "reset": "Restart run"}
# Some keys arrive under more than one name (shift and left shift), so treat them as the same key
KEY_ALIASES = {
    "shift": ("shift", "left shift", "right shift"), "left shift": ("shift", "left shift"),
    "right shift": ("shift", "right shift"), "control": ("control", "left control", "right control"),
    "left control": ("control", "left control"), "right control": ("control", "right control"),
    "alt": ("alt", "left alt", "right alt"), "left alt": ("alt", "left alt"), "right alt": ("alt", "right alt"),
}
UNBINDABLE = {"escape", "left mouse down", "right mouse down", "middle mouse down", "scroll up", "scroll down"}
CROSSHAIR_COLORS = {
    "White": color.rgba(1, 1, 1, 0.85),
    "Green": color.rgba(0.4, 1, 0.45, 0.9),
    "Yellow": color.rgba(1, 0.9, 0.3, 0.9),
    "Red": color.rgba(1, 0.35, 0.35, 0.9),
    "Cyan": color.rgba(0.4, 0.95, 1, 0.9),
}

# Modes: name, bridge length (None = endless)
MODES = [("Short", 25), ("Medium", 50), ("Long", 100), ("Endless", None)]
split_every = 10

# Hotbar: shown name, texture tile
HOTBAR = [
    ("Planks", "planks"),
    ("Stone", "stone"),
    ("Sandstone", "sandstone"),
    ("White Wool", "wool_white"),
    ("Red Wool", "wool_red"),
    ("Orange Wool", "wool_orange"),
    ("Lime Wool", "wool_lime"),
    ("Blue Wool", "wool_blue"),
    ("Purple Wool", "wool_purple"),
]
wool_colors = {
    "wool_white": (232, 234, 236), "wool_red": (176, 46, 38), "wool_orange": (240, 118, 20),
    "wool_lime": (112, 185, 25), "wool_blue": (53, 57, 157), "wool_purple": (122, 42, 172),
}

######################像素材質/ pixel textures######################

def clamp(value):
    return max(0, min(255, int(value)))


def shade(rgb, amount):
    """amount > 0 lightens, < 0 darkens (-1..1)"""
    if amount >= 0:
        return tuple(clamp(c + (255 - c) * amount) for c in rgb)
    return tuple(clamp(c * (1 + amount)) for c in rgb)


def value_noise(rng, cells):
    """
    Smooth random blotches that tile seamlessly \n
    cells: / How many blotches across (more = smaller blotches) \n
    return: 16x16 list of values from about -1 to 1
    """
    grid = [[rng.uniform(-1, 1) for _ in range(cells)] for _ in range(cells)]
    size = 16 / cells
    result = [[0.0] * 16 for _ in range(16)]
    for y in range(16):
        for x in range(16):
            gx, gy = x / size, y / size
            x0, y0 = int(gx), int(gy)
            tx, ty = gx - x0, gy - y0
            tx, ty = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)  # Smooth the blend
            a = grid[y0 % cells][x0 % cells]
            b = grid[y0 % cells][(x0 + 1) % cells]
            c = grid[(y0 + 1) % cells][x0 % cells]
            d = grid[(y0 + 1) % cells][(x0 + 1) % cells]
            top = a + (b - a) * tx
            bottom = c + (d - c) * tx
            result[y][x] = top + (bottom - top) * ty
    return result


def make_tile(name):
    """
    Draw one 16x16 pixel-art block texture in code \n
    name: / Which texture (stone, planks, wool_red...)
    """
    img = Image.new("RGB", (16, 16))
    rng = random.Random(name)
    px = img.load()

    if name == "stone":
        base = (126, 126, 128)
        big, small = value_noise(rng, 4), value_noise(rng, 8)
        tones = [[big[y][x] * 0.1 + small[y][x] * 0.06 + rng.uniform(-0.035, 0.035) for x in range(16)]
                 for y in range(16)]
        # A couple of thin cracks
        for _ in range(3):
            x, y = rng.randrange(16), rng.randrange(16)
            for _ in range(rng.randint(3, 6)):
                tones[y][x] -= 0.16
                x = (x + rng.choice((-1, 0, 1))) % 16
                y = (y + rng.choice((0, 1))) % 16
        for y in range(16):
            for x in range(16):
                px[x, y] = shade(base, tones[y][x])

    elif name == "planks":
        base = (166, 130, 80)
        board_tones = [0.04, -0.05, 0.07, -0.02]
        tones = [[board_tones[y // 4] + rng.uniform(-0.035, 0.035) for x in range(16)] for y in range(16)]
        for board in range(4):
            top = board * 4
            # Wood grain: short darker streaks along the board
            for _ in range(4):
                y = top + rng.randrange(3)
                x = rng.randrange(16)
                for i in range(rng.randint(3, 7)):
                    tones[y][(x + i) % 16] -= 0.1
            for x in range(16):
                tones[top][x] += 0.05       # Light top edge of each board
                tones[top + 3][x] = -0.36   # Dark gap under each board
            seam = (board * 5 + 2) % 16
            for y in range(top, top + 3):
                tones[y][seam] = -0.3       # Where two boards meet
                tones[y][(seam + 1) % 16] += 0.06
        knot_x, knot_y = rng.randrange(1, 14), rng.choice((1, 5, 9, 13))
        tones[knot_y][knot_x] -= 0.25
        tones[knot_y][knot_x + 1] -= 0.18
        for y in range(16):
            for x in range(16):
                px[x, y] = shade(base, tones[y][x])

    elif name == "sandstone":
        base = (222, 208, 156)
        small = value_noise(rng, 8)
        for y in range(16):
            for x in range(16):
                tone = small[y][x] * 0.035 + rng.uniform(-0.03, 0.03)
                if y < 3:
                    tone += 0.07             # Smooth top band
                elif y == 3 or y == 12:
                    tone -= 0.1              # Thin lines between bands
                elif y > 12:
                    tone -= 0.07
                elif rng.random() < 0.08:
                    tone -= 0.08             # Sandy specks
                px[x, y] = shade(base, tone)

    elif name == "sandstone_top":
        base = (226, 212, 160)
        big, small = value_noise(rng, 4), value_noise(rng, 8)
        for y in range(16):
            for x in range(16):
                tone = big[y][x] * 0.03 + small[y][x] * 0.03 + rng.uniform(-0.03, 0.03)
                if rng.random() < 0.06:
                    tone -= 0.08  # Sandy specks
                if x in (0, 15) or y in (0, 15):
                    tone -= 0.05
                px[x, y] = shade(base, tone)

    elif name.startswith("wool_"):
        base = wool_colors[name]
        pattern = random.Random("wool")  # Same fluffy pattern for every color
        big, small = value_noise(pattern, 4), value_noise(pattern, 8)
        tones = [[big[y][x] * 0.06 + small[y][x] * 0.05 + pattern.uniform(-0.04, 0.04) for x in range(16)]
                 for y in range(16)]
        # Little curls of fiber: a light pixel with a dark one next to it
        for _ in range(26):
            x, y = pattern.randrange(16), pattern.randrange(16)
            tones[y][x] += 0.1
            tones[(y + 1) % 16][(x + 1) % 16] -= 0.1
        for y in range(16):
            for x in range(16):
                if x in (0, 15) or y in (0, 15):
                    tones[y][x] -= 0.1       # Soft edge so each block stands out
                px[x, y] = shade(base, tones[y][x])

    elif name == "platform":
        base = (98, 102, 112)
        for y in range(16):
            for x in range(16):
                tone = rng.uniform(-0.04, 0.04)
                if x == 0 or y == 0:
                    tone = 0.18
                elif x == 15 or y == 15:
                    tone = -0.3
                elif x in (1, 14) or y in (1, 14):
                    tone += 0.06
                px[x, y] = shade(base, tone)

    elif name == "goal":
        base = (240, 196, 50)
        for y in range(16):
            for x in range(16):
                tone = rng.uniform(-0.05, 0.05)
                if x == 0 or y == 0:
                    tone = 0.45
                elif x == 15 or y == 15:
                    tone = -0.3
                elif (x, y) in ((4, 4), (5, 4), (4, 5), (11, 10), (10, 11), (11, 11)):
                    tone = 0.6
                px[x, y] = shade(base, tone)
    return img

######################方塊網格/ block meshes######################

# Each face: outward normal, 4 corners (bottom-left, bottom-right, top-right, top-left), light level
FACES = [
    ((0, 1, 0), [(0, 1, 0), (1, 1, 0), (1, 1, 1), (0, 1, 1)], 1.0),
    ((0, -1, 0), [(0, 0, 1), (1, 0, 1), (1, 0, 0), (0, 0, 0)], 0.5),
    ((1, 0, 0), [(1, 0, 0), (1, 0, 1), (1, 1, 1), (1, 1, 0)], 0.6),
    ((-1, 0, 0), [(0, 0, 1), (0, 0, 0), (0, 1, 0), (0, 1, 1)], 0.6),
    ((0, 0, 1), [(1, 0, 1), (0, 0, 1), (0, 1, 1), (1, 1, 1)], 0.8),
    ((0, 0, -1), [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)], 0.8),
]
UV_CORNERS = [(0, 0), (1, 0), (1, 1), (0, 1)]
UV_MIRRORED = [(1 - u, v) for u, v in UV_CORNERS]
TOP_TILES = {"sandstone": "sandstone_top"}  # Blocks whose top and bottom look different from their sides
PLACE_SOUNDS = {"planks": "place_wood", "stone": "place_stone", "sandstone": "place_stone"}  # Others: soft wool
SPIN_TILES = {"stone", "wool_white", "wool_red", "wool_orange", "wool_lime", "wool_blue", "wool_purple"}
AO_LIGHT = (0.5, 0.68, 0.84, 1.0)  # Corner brightness by how many neighbors touch it
_light_colors = {}


def light_color(level):
    level = round(level, 3)
    if level not in _light_colors:
        _light_colors[level] = color.rgba(level, level, level, 1)
    return _light_colors[level]


class Atlas:
    def __init__(self, names):
        """All block textures side by side in one image (one texture = fast drawing)"""
        self.names = list(names)
        self.index = {name: i for i, name in enumerate(self.names)}
        self.tiles = {name: make_tile(name) for name in self.names}
        image = Image.new("RGB", (16 * len(self.names), 16))
        for name, tile in self.tiles.items():
            image.paste(tile, (16 * self.index[name], 0))
        self.texture = Texture(image)
        self.texture.filtering = None  # Keep pixels sharp
        self.icons = {}

    def uv(self, name, u, v):
        inset = 0.02  # Stops neighboring tiles bleeding in at the edges
        count = len(self.names)
        return ((self.index[name] + inset + u * (1 - 2 * inset)) / count, inset + v * (1 - 2 * inset))

    def icon(self, name):
        if name not in self.icons:
            texture = Texture(self.tiles[name])
            texture.filtering = None
            self.icons[name] = texture
        return self.icons[name]


def build_mesh(cells, tile_of, solid, atlas, offset=(0, 0, 0)):
    """
    Turn blocks into one mesh, skipping hidden faces and darkening corners (ambient occlusion) \n
    cells: / Block positions to draw \n
    tile_of: / cell -> texture name \n
    solid: / cell -> True if a block is there (for hiding faces)
    """
    vertices, triangles, uvs, colors = [], [], [], []
    for cell in cells:
        tile = tile_of(cell)
        # Turn or flip the texture depending on where the block is, so rows of blocks don't look stamped
        spin = ((cell[0] * 73856093) ^ (cell[1] * 19349663) ^ (cell[2] * 83492791)) & 255
        for normal, corners, light in FACES:
            out = (cell[0] + normal[0], cell[1] + normal[1], cell[2] + normal[2])
            if solid(out):
                continue
            axes = [a for a in range(3) if normal[a] == 0]
            start = len(vertices)
            face_tile = TOP_TILES.get(tile, tile) if normal[1] != 0 else tile
            face_uvs = UV_MIRRORED if spin & 4 else UV_CORNERS
            if normal[1] != 0 and (tile in SPIN_TILES or face_tile != tile):
                turn = spin % 4
                face_uvs = face_uvs[turn:] + face_uvs[:turn]
            for corner, (u, v) in zip(corners, face_uvs):
                # Look at the 3 blocks touching this corner on the outside of the face
                side1 = list(out)
                side2 = list(out)
                side1[axes[0]] += 1 if corner[axes[0]] else -1
                side2[axes[1]] += 1 if corner[axes[1]] else -1
                diag = list(side1)
                diag[axes[1]] = side2[axes[1]]
                s1, s2, d = solid(tuple(side1)), solid(tuple(side2)), solid(tuple(diag))
                ao = 0 if s1 and s2 else 3 - (s1 + s2 + d)

                vertices.append(Vec3(cell[0] + corner[0] - offset[0], cell[1] + corner[1] - offset[1],
                                     cell[2] + corner[2] - offset[2]))
                uvs.append(atlas.uv(face_tile, u, v))
                colors.append(light_color(light * AO_LIGHT[ao]))
            triangles += [start, start + 1, start + 2, start, start + 2, start + 3]
    return Mesh(vertices=vertices, triangles=triangles, uvs=uvs, colors=colors)

# Like Ursina's unlit shader, plus fog that starts at fog_start and is solid by fog_end
block_shader = Shader(language=Shader.GLSL, vertex="""
#version 130
uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelMatrix;
in vec4 p3d_Vertex;
in vec2 p3d_MultiTexCoord0;
in vec4 p3d_Color;
out vec2 uvs;
out vec4 vertex_color;
out vec3 world_position;
void main() {
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
    uvs = p3d_MultiTexCoord0;
    vertex_color = p3d_Color;
    world_position = (p3d_ModelMatrix * p3d_Vertex).xyz;
}
""", fragment="""
#version 130
uniform sampler2D p3d_Texture0;
uniform vec4 p3d_ColorScale;
uniform vec3 camera_world_position;
uniform vec4 fog_color;
uniform float fog_start;
uniform float fog_end;
in vec2 uvs;
in vec4 vertex_color;
in vec3 world_position;
out vec4 color;
void main() {
    color = texture(p3d_Texture0, uvs) * p3d_ColorScale * vertex_color;
    float distance = length(world_position - camera_world_position);
    float t = clamp((distance - fog_start) / (fog_end - fog_start), 0.0, 1.0);
    color.rgb = mix(color.rgb, fog_color.rgb, t);
}
""", default_input={"fog_color": color.rgb32(190, 215, 255), "fog_start": 45.0, "fog_end": 140.0,
                    "camera_world_position": Vec3(0, 0, 0)})
block_shader.continuous_input["camera_world_position"] = lambda: camera.world_position

######################音效/ sounds######################

def write_sound(path, duration, wave_func, volume):
    """Make a .wav file from a wave function (no sound files needed)"""
    rate = 22050
    samples = array("h")
    for i in range(int(rate * duration)):
        t = i / rate
        samples.append(int(max(-1.0, min(1.0, wave_func(t, duration))) * volume * 32767))
    with wave.open(path, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(rate)
        wav_file.writeframes(samples.tobytes())


class Sounds:
    def __init__(self, app):
        self.sounds = {}
        self.volume = 0.8
        folder = os.path.join(tempfile.gettempdir(), "bridge_trainer_sounds")
        os.makedirs(folder, exist_ok=True)
        noise = random.Random(3)
        recipes = {
            # Soft thud: noise plus a low tone that dies away fast
            "place": (0.09, lambda t, d: (noise.uniform(-1, 1) * 0.6 + math.sin(2 * math.pi * 160 * t) * 0.6)
                      * (1 - t / d) ** 4, 0.5),
            # Hollow knock for wood: two low tones that ring a little
            "place_wood": (0.12, lambda t, d: (math.sin(2 * math.pi * 210 * t) + 0.5 * math.sin(2 * math.pi * 430 * t)
                                               + noise.uniform(-1, 1) * 0.25) * (1 - t / d) ** 5, 0.45),
            # Sharp click for stone: mostly bright noise, very short
            "place_stone": (0.07, lambda t, d: (noise.uniform(-1, 1) * 0.8 + math.sin(2 * math.pi * 900 * t) * 0.3)
                            * (1 - t / d) ** 6, 0.45),
            "break": (0.12, lambda t, d: noise.uniform(-1, 1) * (1 - t / d) ** 3, 0.35),
            "finish": (0.7, lambda t, d: math.sin(2 * math.pi * [523, 659, 784, 1047][min(3, int(t / 0.12))] * t)
                       * (1 - t / d), 0.3),
            "fall": (0.5, lambda t, d: math.sin(2 * math.pi * (500 - 700 * t) * t) * (1 - t / d), 0.25),
        }
        for name, (duration, func, volume) in recipes.items():
            path = os.path.join(folder, f"{name}.wav")
            try:
                from panda3d.core import Filename
                write_sound(path, duration, func, volume)
                self.sounds[name] = app.loader.loadSfx(Filename.fromOsSpecific(path))
            except Exception as error:  # Sound is a bonus - never crash because of it
                print(f"Sound '{name}' unavailable: {error}")

    def play(self, name, pitch=1.0):
        sound = self.sounds.get(name)
        if sound:
            sound.setVolume(self.volume)
            sound.setPlayRate(pitch)
            sound.play()

######################存檔/ saving######################

def load_save():
    data = {"best": {}, "ghosts": {}, "settings": {}, "keys": {}, "best_distance": {}}
    try:
        with open(SAVE_FILE) as file:
            loaded = json.load(file)
        for key in data:
            if isinstance(loaded.get(key), dict):
                data[key] = loaded[key]
    except (OSError, ValueError):
        pass
    return data


def write_save(data):
    try:
        with open(SAVE_FILE, "w") as file:
            json.dump(data, file)
    except OSError as error:
        print(f"Could not save: {error}")

######################物理/ physics helpers######################

def voxel_raycast(origin, direction, max_distance, solid):
    """
    Step through the block grid along a ray \n
    return: (block, face normal) of the first block hit, or (None, None)
    """
    cell = [math.floor(origin.x), math.floor(origin.y), math.floor(origin.z)]
    steps, t_max, t_delta = [], [], []
    for o, d, c in zip((origin.x, origin.y, origin.z), (direction.x, direction.y, direction.z), cell):
        if d > 0:
            steps.append(1)
            t_max.append((c + 1 - o) / d)
            t_delta.append(1 / d)
        elif d < 0:
            steps.append(-1)
            t_max.append((o - c) / -d)
            t_delta.append(-1 / d)
        else:
            steps.append(0)
            t_max.append(math.inf)
            t_delta.append(math.inf)
    while True:
        axis = t_max.index(min(t_max))
        if t_max[axis] > max_distance:
            return None, None
        cell[axis] += steps[axis]
        t_max[axis] += t_delta[axis]
        if solid(tuple(cell)):
            normal = [0, 0, 0]
            normal[axis] = -steps[axis]
            return tuple(cell), tuple(normal)

######################遊戲類別/ game class######################

class BridgeTrainer(Entity):
    def __init__(self, app):
        super().__init__()
        self.atlas = Atlas([tile for _, tile in HOTBAR] + ["platform", "goal"] + list(TOP_TILES.values()))
        self.sounds = Sounds(app)
        self.save = load_save()
        settings = self.save["settings"]
        self.settings = {key: settings.get(key, value) for key, value in DEFAULT_SETTINGS.items()}
        if self.settings["crosshair"] not in CROSSHAIR_COLORS:
            self.settings["crosshair"] = "White"
        saved_keys = self.save.get("keys", {})
        self.keys = {action: saved_keys.get(action, key) for action, key in DEFAULT_KEYS.items()}
        self.binding = None      # Action waiting for a new key on the controls page
        self.mode = settings.get("mode", 0)
        self.diagonal = settings.get("diagonal", False)
        self.slot = settings.get("slot", 3)

        self.blocks = {}         # cell -> texture name
        self.kinds = {}          # cell -> "platform", "goal" or "placed"
        self.chunks = {}         # chunk key -> set of cells
        self.chunk_models = {}   # chunk key -> Entity
        self.dirty = set()

        self.paused = True
        self.page = "main"       # Which menu page is open: main or settings
        self.reset_armed = False  # "Reset best times" needs two clicks
        self.sneak_on = False    # For toggle sneak / toggle sprint
        self.sprint_on = False
        self.last_toggle = {}
        self.refreshing = False  # True while the settings page is being filled in
        self.attempts = 0        # This session only
        self.session_times = []
        self.tick_count = 0
        self.tick_time = 0.0
        self.target = None
        self.clicks = deque()    # Times of recent right clicks (for CPS)
        self.swing = 0.0
        self.walk_dist = 0.0
        self.name_timer = 0.0

        self.outline = Entity(model="wireframe_cube", color=color.rgba(0, 0, 0, 0.9), scale=1.004, enabled=False)
        self.ghost = Entity(model="cube", color=color.rgba(0.55, 0.8, 1, 0.35), scale=(0.6, 1.8, 0.6), enabled=False)
        self.held = Entity(parent=camera, texture=self.atlas.texture, scale=0.32, double_sided=True)
        self.held_models = {}
        self.effects = []        # Flashes and flying bits: [entity, seconds left, total seconds, velocity or None]
        self.tile_colors = {name: tile.resize((1, 1), Image.BOX).getpixel((0, 0))
                            for name, tile in self.atlas.tiles.items()}

        self.build_clouds()
        self.build_ui()
        self.build_settings_page()
        self.build_controls_page()
        self.apply_settings()
        self.select_slot(self.slot)
        self.setup_course()
        self.show_menu(True)

    ######## world ########

    @staticmethod
    def chunk_key(cell):
        return (cell[0] >> 4, cell[1] >> 4, cell[2] >> 4)

    def mark_dirty(self, cell):
        """A block changed: redraw its chunk and any chunk touching it (faces and shading can change)"""
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    self.dirty.add(self.chunk_key((cell[0] + dx, cell[1] + dy, cell[2] + dz)))

    def add_block(self, cell, tile, kind):
        self.blocks[cell] = tile
        self.kinds[cell] = kind
        self.chunks.setdefault(self.chunk_key(cell), set()).add(cell)
        self.mark_dirty(cell)

    def remove_block(self, cell):
        del self.blocks[cell]
        del self.kinds[cell]
        self.chunks[self.chunk_key(cell)].discard(cell)
        self.mark_dirty(cell)

    def rebuild_dirty(self):
        for key in self.dirty:
            cells = self.chunks.get(key)
            model = self.chunk_models.pop(key, None)
            if model:
                destroy(model)
            if cells:
                mesh = build_mesh(cells, self.blocks.get, self.blocks.__contains__, self.atlas)
                self.chunk_models[key] = Entity(model=mesh, texture=self.atlas.texture, shader=block_shader)
        self.dirty.clear()

    def setup_course(self):
        """Clear everything and build the start (and goal) platform"""
        for cell in list(self.blocks):
            self.remove_block(cell)

        for x in range(-2, 3):
            for z in range(-2, 3):
                self.add_block((x, -1, z), "platform", "platform")

        # Bridge goes toward +z (straight) or +x +z (diagonal)
        self.direction = Vec3(1, 0, 1).normalized() if self.diagonal else Vec3(0, 0, 1)
        length = MODES[self.mode][1]
        if length:
            gap = round(length / math.sqrt(2)) if self.diagonal else length
            center = (gap + 5, gap + 5) if self.diagonal else (0, length + 5)
            for x in range(center[0] - 2, center[0] + 3):
                for z in range(center[1] - 2, center[1] + 3):
                    self.add_block((x, -1, z), "goal", "goal")
        self.respawn()

    def build_clouds(self):
        rng = random.Random(12)
        self.clouds = []
        for _ in range(45):
            cloud = Entity(model="cube", color=color.rgba(1, 1, 1, 0.82),
                           scale=(rng.randrange(8, 28), 4, rng.randrange(8, 20)),
                           position=(rng.uniform(-220, 220), 70, rng.uniform(-220, 220)))
            self.clouds.append(cloud)

    ######## run state ########

    def best_key(self):
        return f"{MODES[self.mode][0]}_{'diag' if self.diagonal else 'straight'}"

    def respawn(self):
        if getattr(self, "start_tick", None) is not None and getattr(self, "finish_time", None) is None:
            self.attempts += 1  # Gave up or fell during a run
            self.record_distance()
        self.pos = Vec3(0.5, 0, 0.5)
        self.prev_pos = Vec3(self.pos)
        self.vel = Vec3(0, 0, 0)
        self.on_ground = True
        self.sneaking = False
        self.sprinting = False
        self.jump_ticks = 0
        self.place_timer = 0
        self.eye = stand_eye
        # Face away from the goal and look down, ready to bridge
        self.yaw = 225 if self.diagonal else 180
        self.pitch = 80
        self.start_tick = None
        self.finish_time = None
        self.placed = 0
        self.distance = 0.0
        self.splits = []
        self.compare_splits = list(self.save["ghosts"].get(self.best_key(), {}).get("splits", []))
        self.path = []
        for cell in [c for c, kind in self.kinds.items() if kind == "placed"]:
            self.remove_block(cell)
        self.finish_text.text = ""
        self.summary_bg.enabled = self.summary_text.enabled = False

    def record_distance(self):
        """Endless mode has no finish line, so its record is the farthest you got"""
        if MODES[self.mode][1] is None and self.distance > self.save["best_distance"].get(self.best_key(), 0):
            self.save["best_distance"][self.best_key()] = round(self.distance, 1)
            write_save(self.save)

    def run_time(self, partial=0.0):
        if self.finish_time is not None:
            return self.finish_time
        if self.start_tick is None:
            return 0.0
        return (self.tick_count - self.start_tick + partial) * tick_length

    def start_timer(self):
        if self.start_tick is None:
            self.start_tick = self.tick_count
            self.path = []

    def finish(self):
        self.finish_time = self.run_time()
        self.attempts += 1
        self.session_times.append(self.finish_time)
        key = self.best_key()
        best = self.save["best"].get(key)
        self.sounds.play("finish")
        self.show_summary(best, self.compare_splits)
        if best is None or self.finish_time < best:
            self.save["best"][key] = self.finish_time
            self.save["ghosts"][key] = {"path": [[round(v, 3) for v in p] for p in self.path], "splits": self.splits}
            write_save(self.save)
            self.finish_text.text = f"NEW BEST!  {self.finish_time:.2f}s"
            self.finish_text.color = color.rgb32(120, 255, 140)
        else:
            self.finish_text.text = f"FINISHED  {self.finish_time:.2f}s   (+{self.finish_time - best:.2f})"
            self.finish_text.color = color.rgb32(255, 220, 90)

    def show_summary(self, best, best_splits):
        """Results panel after reaching the goal"""
        t = self.finish_time
        if best is None:
            compare = "First finish on this course!"
        else:
            tag = "<green>" if t < best else "<red>"
            compare = f"{tag}{t - best:+.2f}s<default> compared to your best ({best:.2f}s)"
        lines = [compare, f"Blocks: {self.placed}      Average speed: {self.distance / max(t, 0.05):.2f} blocks/s"]
        split_parts = []
        for i, split in enumerate(self.splits):
            part = f"{(i + 1) * split_every}: {split:.2f}"
            if i < len(best_splits):
                diff = split - best_splits[i]
                part += f" ({'<green>' if diff <= 0 else '<red>'}{diff:+.2f}<default>)"
            split_parts.append(part)
        for i in range(0, len(split_parts), 3):  # Three splits per line
            lines.append("    ".join(split_parts[i:i + 3]))
        lines += ["", f"{self.key_name(self.keys['reset'])}: go again      Esc: menu"]
        self.summary_text.text = "\n".join(lines)
        self.summary_bg.scale_y = 0.04 + 0.033 * len(lines)
        self.summary_bg.enabled = self.summary_text.enabled = True

    ######## physics ########

    def overlaps_blocks(self, min_x, min_y, min_z, max_x, max_y, max_z):
        """Is any block inside this box? (touching edges doesn't count)"""
        eps = 1e-7
        for bx in range(math.floor(min_x + eps), math.floor(max_x - eps) + 1):
            for by in range(math.floor(min_y + eps), math.floor(max_y - eps) + 1):
                for bz in range(math.floor(min_z + eps), math.floor(max_z - eps) + 1):
                    if (bx, by, bz) in self.blocks:
                        return True
        return False

    def box(self, dx=0.0, dy=0.0, dz=0.0):
        x, y, z = self.pos.x + dx, self.pos.y + dy, self.pos.z + dz
        return (x - player_half_w, y, z - player_half_w, x + player_half_w, y + player_height, z + player_half_w)

    def clip(self, axis, amount):
        """
        How far the player can move along one axis before hitting a block
        """
        if amount == 0:
            return 0.0
        box = self.box()
        lo, hi = box[axis], box[axis + 3]
        # Every block in the space swept by the move
        ranges = []
        for a in range(3):
            a_lo, a_hi = box[a], box[a + 3]
            if a == axis:
                a_lo, a_hi = (a_lo + amount, a_hi) if amount < 0 else (a_lo, a_hi + amount)
            ranges.append(range(math.floor(a_lo + 1e-7), math.floor(a_hi - 1e-7) + 1))
        for bx in ranges[0]:
            for by in ranges[1]:
                for bz in ranges[2]:
                    if (bx, by, bz) not in self.blocks:
                        continue
                    cell = (bx, by, bz)
                    if amount > 0 and cell[axis] >= hi - 1e-7:
                        amount = min(amount, cell[axis] - hi)
                    elif amount < 0 and cell[axis] + 1 <= lo + 1e-7:
                        amount = max(amount, cell[axis] + 1 - lo)
        return amount

    def move(self, dx, dy, dz):
        # Sneaking on the ground: shrink the move until there's still a block under you
        if self.on_ground and self.sneaking:
            step = 0.05
            while dx != 0 and not self.overlaps_blocks(*self.box(dx, -1, 0)):
                dx = 0.0 if abs(dx) < step else dx - math.copysign(step, dx)
            while dz != 0 and not self.overlaps_blocks(*self.box(0, -1, dz)):
                dz = 0.0 if abs(dz) < step else dz - math.copysign(step, dz)
            while dx != 0 and dz != 0 and not self.overlaps_blocks(*self.box(dx, -1, dz)):
                dx = 0.0 if abs(dx) < step else dx - math.copysign(step, dx)
                dz = 0.0 if abs(dz) < step else dz - math.copysign(step, dz)

        want = (dx, dy, dz)
        dy = self.clip(1, dy)
        self.pos.y += dy
        dx = self.clip(0, dx)
        self.pos.x += dx
        dz = self.clip(2, dz)
        self.pos.z += dz

        self.on_ground = want[1] != dy and want[1] < 0
        if want[0] != dx:
            self.vel.x = 0
        if want[1] != dy:
            self.vel.y = 0
        if want[2] != dz:
            self.vel.z = 0

    def is_held(self, action):
        """1 if the key for this action is held down, else 0"""
        key = self.keys[action]
        return 1 if any(held_keys[name] for name in KEY_ALIASES.get(key, (key,))) else 0

    def pressed(self, key, action):
        """Is this key event the key bound to an action?"""
        bound = self.keys[action]
        return key in KEY_ALIASES.get(bound, (bound,))

    def tick(self):
        """One physics step (20 per second)"""
        self.tick_count += 1
        self.prev_pos = Vec3(self.pos)

        for axis in ("x", "y", "z"):
            if abs(getattr(self.vel, axis)) < 0.005:
                setattr(self.vel, axis, 0)

        forward = self.is_held("forward") - self.is_held("back")
        strafe = self.is_held("right") - self.is_held("left")
        if self.settings["sneak_toggle"]:
            self.sneaking = self.sneak_on
        else:
            self.sneaking = bool(self.is_held("sneak"))
        if self.sneaking:
            forward *= sneak_multiplier
            strafe *= sneak_multiplier
        forward *= 0.98
        strafe *= 0.98

        if self.settings["sprint_toggle"]:
            wants_sprint = self.sprint_on
        else:
            wants_sprint = self.is_held("sprint")
        if wants_sprint and self.is_held("forward") and not self.sneaking:
            self.sprinting = True
        elif not self.is_held("forward") or self.sneaking:
            self.sprinting = False

        yaw = math.radians(self.yaw)
        if self.is_held("jump"):
            if self.on_ground and self.jump_ticks == 0:
                self.vel.y = jump_power
                if self.sprinting:
                    self.vel.x += math.sin(yaw) * sprint_jump_boost
                    self.vel.z += math.cos(yaw) * sprint_jump_boost
                self.jump_ticks = 10
        else:
            self.jump_ticks = 0
        if self.jump_ticks > 0:
            self.jump_ticks -= 1

        slip = ground_slip if self.on_ground else air_slip
        if self.on_ground:
            accel = (sprint_accel if self.sprinting else walk_accel) * 0.16277136 / slip ** 3
        else:
            accel = air_sprint_accel if self.sprinting else air_accel
        size = forward * forward + strafe * strafe
        if size >= 1e-4:
            k = accel / max(1.0, math.sqrt(size))
            forward *= k
            strafe *= k
            self.vel.x += math.sin(yaw) * forward + math.cos(yaw) * strafe
            self.vel.z += math.cos(yaw) * forward - math.sin(yaw) * strafe

        self.move(self.vel.x, self.vel.y, self.vel.z)
        self.vel.y = (self.vel.y - gravity) * air_drag
        self.vel.x *= slip
        self.vel.z *= slip

        if self.on_ground:
            self.walk_dist += math.hypot(self.pos.x - self.prev_pos.x, self.pos.z - self.prev_pos.z)

        # Holding right click places a block every 4 ticks
        if self.place_timer > 0:
            self.place_timer -= 1
        if held_keys["right mouse"] and self.place_timer == 0:
            self.place_block()

        self.update_run()

    def update_run(self):
        offset = self.pos - Vec3(0.5, 0, 0.5)
        self.distance = max(0.0, offset.x * self.direction.x + offset.z * self.direction.z - 2.5)
        if self.start_tick is None and self.distance > 0.3:
            self.start_timer()
        if self.start_tick is not None and self.finish_time is None:
            self.path.append((self.pos.x, self.pos.y, self.pos.z))
            if self.distance >= split_every * (len(self.splits) + 1):
                self.splits.append(self.run_time())

        if self.pos.y < void_y:
            self.sounds.play("fall")
            self.respawn()
            return

        below = (math.floor(self.pos.x), math.floor(self.pos.y - 0.01), math.floor(self.pos.z))
        if self.on_ground and self.kinds.get(below) == "goal" and self.finish_time is None and self.start_tick:
            self.finish()

    ######## blocks ########

    def eye_position(self, alpha):
        render = self.prev_pos + (self.pos - self.prev_pos) * alpha
        return render + Vec3(0, self.eye, 0)

    def find_target(self, eye, direction):
        cell, normal = voxel_raycast(eye, direction, reach, self.blocks.__contains__)
        if cell is None:
            self.target = None
        else:
            self.target = (cell, (cell[0] + normal[0], cell[1] + normal[1], cell[2] + normal[2]))

    def can_place(self, cell):
        if cell in self.blocks:
            return False
        box = self.box()
        inside = (cell[0] < box[3] and cell[0] + 1 > box[0] and cell[1] < box[4] and cell[1] + 1 > box[1]
                  and cell[2] < box[5] and cell[2] + 1 > box[2])
        return not inside

    def place_block(self):
        self.place_timer = place_delay
        self.swing = 1.0
        if not self.target or not self.can_place(self.target[1]):
            return
        against, cell = self.target
        tile = HOTBAR[self.slot][1]
        self.add_block(cell, tile, "placed")
        self.place_effects(cell, against, tile)
        self.placed += 1
        self.start_timer()
        self.sounds.play(PLACE_SOUNDS.get(tile, "place"), random.uniform(0.85, 1.15))

    def place_effects(self, cell, against, tile):
        """A quick bright flash on the new block, plus a few bits where it touched the old one"""
        # Its own mesh: a mesh can only belong to one entity, and the held block uses the cached one
        mesh = build_mesh([(0, 0, 0)], lambda c: tile, lambda c: False, self.atlas, offset=(0.5, 0.5, 0.5))
        flash = Entity(model=mesh, texture=self.atlas.texture,
                       position=Vec3(*cell) + Vec3(0.5, 0.5, 0.5), scale=1.04, color=color.rgba(1.6, 1.6, 1.6, 0.7))
        self.effects.append([flash, 0.12, 0.12, None])
        contact = (Vec3(*cell) + Vec3(*against)) / 2 + Vec3(0.5, 0.5, 0.5)
        self.burst(contact, tile, 6, 0.25)

    def burst(self, center, tile, count, spread):
        rgb = self.tile_colors[tile]
        for _ in range(count):
            offset = Vec3(random.uniform(-spread, spread), random.uniform(-spread, spread), random.uniform(-spread, spread))
            tint = random.uniform(0.75, 1.1)
            bit = Entity(model="cube", position=center + offset, scale=random.uniform(0.05, 0.1),
                         color=color.rgb32(*(min(255, int(c * tint)) for c in rgb)))
            velocity = offset.normalized() * random.uniform(1, 2.5) + Vec3(0, random.uniform(1, 3), 0)
            life = random.uniform(0.35, 0.6)
            self.effects.append([bit, life, life, velocity])

    def update_effects(self, dt):
        for effect in self.effects:
            entity, left, total, velocity = effect
            effect[1] = left - dt
            t = max(0.0, effect[1] / total)
            if velocity is None:
                entity.alpha = 0.7 * t          # Flash fades out
                entity.scale = 1 + 0.04 * t
            else:
                velocity.y -= 14 * dt           # Bits fall
                entity.position += velocity * dt
                entity.scale *= 0.97
        for effect in [e for e in self.effects if e[1] <= 0]:
            destroy(effect[0])
            self.effects.remove(effect)

    def break_block(self):
        self.swing = 1.0
        if self.target and self.kinds.get(self.target[0]) == "placed":
            cell = self.target[0]
            tile = self.blocks[cell]
            self.burst(Vec3(*cell) + Vec3(0.5, 0.5, 0.5), tile, 14, 0.45)
            self.remove_block(cell)
            self.sounds.play(PLACE_SOUNDS.get(tile, "place"), random.uniform(0.6, 0.75))

    ######## UI ########

    def build_ui(self):
        self.crosshair = [Entity(parent=camera.ui, model="quad", scale=(0.0028, 0.026)),
                          Entity(parent=camera.ui, model="quad", scale=(0.026, 0.0028))]
        self.timer_text = Text("0.00", position=(0, 0.46), origin=(0, 0), scale=2.4)
        self.info_text = Text("", position=(-0.86, 0.47), origin=(-0.5, 0.5), scale=1.05)
        self.split_text = Text("", position=(0.86, 0.47), origin=(0.5, 0.5), scale=1.05)
        self.finish_text = Text("", position=(0, 0.17), origin=(0, 0), scale=2.6)
        self.summary_bg = Entity(parent=camera.ui, model="quad", color=color.rgba(0, 0, 0, 0.55), scale=(0.75, 0.25),
                                 origin=(0, 0.5), position=(0, 0.12), z=0.5, enabled=False)
        self.summary_text = Text("", position=(0, 0.1), origin=(0, 0.5), scale=1.05, line_height=1.25, enabled=False)
        self.name_text = Text("", position=(0, -0.335), origin=(0, 0), scale=1.1)

        # Hotbar
        slot_size = 0.074
        self.slot_x = [(i - 4) * slot_size for i in range(9)]
        Entity(parent=camera.ui, model="quad", color=color.rgba(0, 0, 0, 0.45),
               scale=(slot_size * 9 + 0.012, slot_size + 0.012), position=(0, -0.43), z=2)
        for i, (_, tile) in enumerate(HOTBAR):
            Entity(parent=camera.ui, model="wireframe_quad", color=color.rgba(1, 1, 1, 0.25),
                   scale=slot_size - 0.006, position=(self.slot_x[i], -0.43), z=1)
            Entity(parent=camera.ui, model="quad", texture=self.atlas.icon(tile), scale=slot_size - 0.026,
                   position=(self.slot_x[i], -0.43), z=0.5)
        self.slot_frame = Entity(parent=camera.ui, model="wireframe_quad", color=color.white,
                                 scale=slot_size + 0.004, position=(0, -0.43))
        self.slot_frame2 = Entity(parent=camera.ui, model="wireframe_quad", color=color.white,
                                  scale=slot_size - 0.002, position=(0, -0.43))

        self.menu_bg = Entity(parent=camera.ui, model="quad", color=color.rgba(0.02, 0.03, 0.06, 0.88),
                              scale=(3, 1), z=-1)
        self.main_items = [Text("BRIDGE TRAINER", position=(0, 0.4), origin=(0, 0), scale=2.4, z=-2)]
        self.mode_buttons = []
        self.mode_best = []
        for i, (name, length) in enumerate(MODES):
            x = (i - 1.5) * 0.23
            size = f"{length} blocks" if length else "no finish"
            button = self.menu_button(f"{name}  ({size})", (x, 0.27), lambda i=i: self.choose_mode(i), width=0.215)
            best = Text("", position=(x, 0.215), origin=(0, 0), scale=0.85, z=-2, color=color.rgb32(255, 220, 90))
            self.mode_buttons.append(button)
            self.mode_best.append(best)
        self.direction_buttons = [
            self.menu_button("Straight", (-0.115, 0.13), lambda: self.choose_direction(False), width=0.215),
            self.menu_button("Diagonal", (0.115, 0.13), lambda: self.choose_direction(True), width=0.215),
        ]
        self.menu_text = Text("", position=(0, -0.06), origin=(0, 0), scale=1, line_height=1.2, z=-2,
                              color=color.rgba(1, 1, 1, 0.8))
        self.session_text = Text("", position=(0, -0.21), origin=(0, 0), scale=0.95, z=-2,
                                 color=color.rgb32(150, 220, 255))
        self.play_button = self.menu_button("Play", (-0.13, -0.3), self.start_playing, color.rgb32(40, 140, 80))
        self.settings_button = self.menu_button("Settings", (0.13, -0.3), lambda: self.open_page("settings"))
        self.main_items += self.mode_buttons + self.mode_best + self.direction_buttons + [
            self.menu_text, self.session_text, self.play_button, self.settings_button]

    def select_slot(self, slot):
        self.slot = slot % len(HOTBAR)
        self.slot_frame.x = self.slot_frame2.x = self.slot_x[self.slot]
        name, tile = HOTBAR[self.slot]
        self.name_text.text = name
        self.name_timer = 2.0
        if tile not in self.held_models:
            self.held_models[tile] = build_mesh([(0, 0, 0)], lambda cell: tile, lambda cell: False, self.atlas,
                                                offset=(0.5, 0.5, 0.5))
        self.held.model = self.held_models[tile]

    def show_menu(self, visible):
        self.paused = visible
        mouse.locked = not visible
        self.menu_bg.enabled = visible
        for item in (self.timer_text, self.info_text, self.name_text, self.finish_text):
            item.enabled = not visible
        self.summary_bg.enabled = self.summary_text.enabled = not visible and self.finish_time is not None
        self.split_text.enabled = not visible and self.settings["show_splits"]
        if visible:
            self.open_page("main")
        else:
            self.open_page(None)
            self.save_settings()

    def start_playing(self):
        self.show_menu(False)

    def save_settings(self):
        self.save["settings"] = dict(self.settings, mode=self.mode, diagonal=self.diagonal, slot=self.slot)
        write_save(self.save)

    def open_page(self, page):
        """Show one menu page (main, settings) or None for no menu"""
        if self.page == "settings" and page != "settings":
            self.save_settings()
        self.page = page
        for item in self.main_items:
            item.enabled = page == "main"
        for item in self.settings_items:
            item.enabled = page == "settings"
        for item in self.controls_items:
            item.enabled = page == "controls"
        self.binding = None
        if page == "controls":
            self.refresh_controls()
        if page == "main":
            self.refresh_menu()
        elif page == "settings":
            self.reset_armed = False
            self.refresh_settings()

    @staticmethod
    def paint(button, button_color):
        """Change a button's color, including its hover and pressed shades"""
        button.color = button_color
        button.highlight_color = button_color.tint(0.2)
        button.pressed_color = button_color.tint(-0.2)

    def menu_button(self, text, position, action, button_color=None, width=0.24):
        button = Button(text=text, parent=camera.ui, scale=(width, 0.055), position=position, z=-2,
                        color=button_color or color.rgb32(45, 55, 95), text_size=0.9)
        if action:
            button.on_click = action
        return button

    ######## settings page ########

    def build_settings_page(self):
        self.settings_items = []
        title = Text("SETTINGS", position=(0, 0.42), origin=(0, 0), scale=2, z=-2)
        hint = Text("Esc: back    Changes save automatically", position=(0, -0.38), origin=(0, 0), scale=0.85,
                    color=color.rgba(1, 1, 1, 0.55), z=-2)
        self.settings_items += [title, hint]

        # Sliders: setting, label, lowest, highest, step
        self.sliders = {}
        for i, (key, label, low, high, step) in enumerate((
                ("sensitivity", "Mouse sensitivity", 5, 200, 1),
                ("fov", "Field of view", 50, 110, 1),
                ("volume", "Volume", 0, 100, 5))):
            slider = Slider(low, high, default=self.settings[key], step=step, text=label, dynamic=True,
                            x=-0.12, y=0.31 - i * 0.07, z=-2)
            slider.on_value_changed = lambda key=key, slider=slider: self.slider_changed(key, slider)
            self.sliders[key] = slider
            self.settings_items.append(slider)

        # Toggle buttons in two columns: setting, label, choices
        self.toggles = []
        options = [
            ("view_bob", "View bobbing", (True, False)),
            ("sprint_fov", "Sprint zoom", (True, False)),
            ("sneak_toggle", "Sneak", (False, True)),
            ("sprint_toggle", "Sprint", (False, True)),
            ("ghost", "Ghost of best run", (True, False)),
            ("show_splits", "Show splits", (True, False)),
            ("show_hand", "Show held block", (True, False)),
            ("show_fps", "Show FPS", (True, False)),
            ("crosshair", "Crosshair", tuple(CROSSHAIR_COLORS)),
            ("fullscreen", "Fullscreen", (False, True)),
        ]
        for i, (key, label, choices) in enumerate(options):
            x = -0.21 if i % 2 == 0 else 0.21
            y = 0.06 - (i // 2) * 0.072
            if i == len(options) - 1 and i % 2 == 0:
                x = 0  # Last one on its own row: center it
            button = self.menu_button("", (x, y), None, width=0.4)
            button.on_click = lambda key=key, choices=choices: self.cycle_setting(key, choices)
            self.toggles.append((button, key, label))
            self.settings_items.append(button)

        self.reset_button = self.menu_button("Reset best times", (-0.29, -0.31), self.reset_best,
                                             color.rgb32(130, 40, 50), width=0.26)
        controls = self.menu_button("Controls...", (0, -0.31), lambda: self.open_page("controls"), width=0.26)
        back = self.menu_button("Back", (0.29, -0.31), lambda: self.open_page("main"), width=0.26)
        self.settings_items += [self.reset_button, controls, back]

    ######## controls page ########

    def build_controls_page(self):
        self.controls_items = [
            Text("CONTROLS", position=(0, 0.42), origin=(0, 0), scale=2, z=-2),
            Text("Click an action, then press the key you want for it", position=(0, 0.34), origin=(0, 0),
                 scale=0.95, color=color.rgba(1, 1, 1, 0.7), z=-2),
        ]
        self.key_buttons = {}
        for i, action in enumerate(DEFAULT_KEYS):
            x = -0.21 if i % 2 == 0 else 0.21
            y = 0.24 - (i // 2) * 0.08
            button = self.menu_button("", (x, y), lambda action=action: self.start_binding(action), width=0.4)
            self.key_buttons[action] = button
            self.controls_items.append(button)
        self.controls_items += [
            Text("Mouse: right click place, left click break, scroll / 1-9 pick block", position=(0, -0.1),
                 origin=(0, 0), scale=0.9, color=color.rgba(1, 1, 1, 0.6), z=-2),
            self.menu_button("Reset to default", (-0.15, -0.31), self.reset_keys, width=0.28),
            self.menu_button("Back", (0.15, -0.31), lambda: self.open_page("settings"), width=0.28),
        ]

    def key_name(self, key):
        return key.upper() if len(key) == 1 else key.title()

    def refresh_controls(self):
        for action, button in self.key_buttons.items():
            if action == self.binding:
                button.text = f"{KEY_LABELS[action]}: press a key..."
                self.paint(button, color.rgb32(150, 110, 30))
            else:
                button.text = f"{KEY_LABELS[action]}: {self.key_name(self.keys[action])}"
                self.paint(button, color.rgb32(45, 55, 95))

    def start_binding(self, action):
        self.binding = action
        self.refresh_controls()

    def finish_binding(self, key):
        """The next key pressed after clicking an action becomes its key"""
        if key.endswith(" up") or key.endswith(" hold") or key in UNBINDABLE:
            if key == "escape":
                self.binding = None
                self.refresh_controls()
            return
        key = {"shift": "left shift", "control": "left control", "alt": "left alt"}.get(key, key)
        self.keys[self.binding] = key
        self.binding = None
        self.save["keys"] = dict(self.keys)
        write_save(self.save)
        self.refresh_controls()

    def reset_keys(self):
        self.keys = dict(DEFAULT_KEYS)
        self.binding = None
        self.save["keys"] = dict(self.keys)
        write_save(self.save)
        self.refresh_controls()

    def setting_text(self, key):
        value = self.settings[key]
        if key in ("sneak_toggle", "sprint_toggle"):
            return "Toggle" if value else "Hold"
        if isinstance(value, bool):
            return "On" if value else "Off"
        return str(value)

    def refresh_settings(self):
        for button, key, label in self.toggles:
            button.text = f"{label}: {self.setting_text(key)}"
        self.refreshing = True
        for key, slider in self.sliders.items():
            slider.value = self.settings[key]
        self.refreshing = False
        if not self.reset_armed:
            self.reset_button.text = "Reset best times"

    def slider_changed(self, key, slider):
        if self.refreshing:
            return
        self.settings[key] = int(round(slider.value))
        self.apply_settings()
        if key == "volume":
            self.sounds.play("place")  # So you can hear the new volume

    def cycle_setting(self, key, choices):
        index = choices.index(self.settings[key]) if self.settings[key] in choices else -1
        self.settings[key] = choices[(index + 1) % len(choices)]
        self.apply_settings()
        self.refresh_settings()
        self.save_settings()

    def reset_best(self):
        if not self.reset_armed:
            self.reset_armed = True
            self.reset_button.text = "Click again to confirm"
            return
        self.save["best"] = {}
        self.save["ghosts"] = {}
        write_save(self.save)
        self.reset_armed = False
        self.reset_button.text = "Best times cleared"

    def apply_settings(self):
        """Make the game match the current settings"""
        self.sounds.volume = self.settings["volume"] / 100
        window.fps_counter.enabled = self.settings["show_fps"]
        self.split_text.enabled = self.settings["show_splits"] and not self.paused
        self.held.enabled = self.settings["show_hand"]
        for line in self.crosshair:
            line.color = CROSSHAIR_COLORS[self.settings["crosshair"]]
        camera.fov = self.settings["fov"]
        if window.fullscreen != self.settings["fullscreen"]:
            try:
                window.fullscreen = self.settings["fullscreen"]
            except Exception as error:  # Some setups can't switch; just stay windowed
                print(f"Could not change fullscreen: {error}")

    def choose_mode(self, mode):
        self.mode = mode
        self.setup_course()
        self.refresh_menu()

    def choose_direction(self, diagonal):
        self.diagonal = diagonal
        self.setup_course()
        self.refresh_menu()

    def refresh_menu(self):
        selected, normal = color.rgb32(40, 140, 80), color.rgb32(45, 55, 95)
        shape = "diag" if self.diagonal else "straight"
        for i, (name, length) in enumerate(MODES):
            self.paint(self.mode_buttons[i], selected if i == self.mode else normal)
            best = self.save["best"].get(f"{name}_{shape}")
            best_distance = self.save["best_distance"].get(f"{name}_{shape}")
            if best is not None:
                self.mode_best[i].text = f"best {best:.2f}s"
            elif length is None and best_distance:
                self.mode_best[i].text = f"best {best_distance:.1f} blocks"
            else:
                self.mode_best[i].text = "no best yet"
        for button, diagonal in zip(self.direction_buttons, (False, True)):
            self.paint(button, selected if diagonal == self.diagonal else normal)

        keys = {action: self.key_name(key) for action, key in self.keys.items()}
        move = f"{keys['forward']}{keys['left']}{keys['back']}{keys['right']}"
        self.menu_text.text = "\n".join([
            f"{move} move    {keys['sneak']} sneak    {keys['sprint']} sprint    {keys['jump']} jump",
            "Right click place (hold = every 4 ticks)    Left click break",
            f"1-9 / scroll: pick block    {keys['reset']}: restart    Esc: this menu",
            "Tip: face backwards, look ~80 degrees down, sneak to the edge, click",
        ])
        if self.session_times:
            average = sum(self.session_times) / len(self.session_times)
            runs = "run" if self.attempts == 1 else "runs"
            self.session_text.text = (f"This session: {len(self.session_times)} finished of {self.attempts} {runs}"
                                      f"    best {min(self.session_times):.2f}s    average {average:.2f}s")
        elif self.attempts:
            runs = "run" if self.attempts == 1 else "runs"
            self.session_text.text = f"This session: {self.attempts} {runs}, none finished yet"
        else:
            self.session_text.text = ""


    @staticmethod
    def set_text(text_entity, value):
        """Rebuilding text is slow, so only do it when the words actually change"""
        if getattr(text_entity, "_last_text", None) != value:
            text_entity.text = value
            text_entity._last_text = value

    def update_hud(self, partial):
        now = self.run_time(partial)
        self.set_text(self.timer_text, f"{now:.2f}")
        self.timer_text.color = color.rgb32(120, 255, 140) if self.finish_time else color.white

        name, length = MODES[self.mode]
        now_real = time.time()
        while self.clicks and now_real - self.clicks[0] > 1:
            self.clicks.popleft()
        bps = self.distance / now if now > 0.3 else 0
        lines = [
            f"{name} - {'Diagonal' if self.diagonal else 'Straight'}",
            f"Distance: {self.distance:.1f}" + (f" / {length}" if length else ""),
            f"Blocks: {self.placed}",
            f"Speed: {bps:.2f} b/s",
            f"CPS: {len(self.clicks)}",
        ]
        best = self.save["best"].get(self.best_key())
        if best is not None:
            lines.append(f"Best: {best:.2f}s")
        best_distance = self.save["best_distance"].get(self.best_key())
        if length is None and best_distance:
            lines.append(f"Best: {best_distance:.1f} blocks")
        lines.append(f"Attempt: {self.attempts + 1}")
        if self.session_times:
            average = sum(self.session_times) / len(self.session_times)
            lines.append(f"Last: {self.session_times[-1]:.2f}  Avg: {average:.2f}")
        self.set_text(self.info_text, "\n".join(lines))

        # Splits, compared with your best run (as it was when this run started)
        best_splits = self.compare_splits
        split_lines = []
        first = max(0, len(self.splits) - 6)
        for i in range(first, len(self.splits)):
            line = f"{(i + 1) * split_every}:  {self.splits[i]:.2f}"
            if i < len(best_splits):
                diff = self.splits[i] - best_splits[i]
                tag = "<green>" if diff <= 0 else "<red>"
                line += f"  {tag}{diff:+.2f}<default>"
            split_lines.append(line)
        self.set_text(self.split_text, "\n".join(split_lines))

    ######## main loop ########

    def update(self):
        dt = min(time.dt, 0.25)  # Ursina adds dt (seconds since last frame) to the time module
        self.name_timer = max(0.0, self.name_timer - dt)
        self.name_text.color = color.rgba(1, 1, 1, min(1, self.name_timer))
        for cloud in self.clouds:
            cloud.x += dt * 1.2
            if cloud.x > 220:
                cloud.x -= 440

        if not self.paused:
            sensitivity = self.settings["sensitivity"]
            self.yaw += mouse.velocity[0] * sensitivity
            self.pitch = max(-90, min(90, self.pitch - mouse.velocity[1] * sensitivity))
            self.tick_time += dt
            while self.tick_time >= tick_length:
                self.tick_time -= tick_length
                self.tick()
        partial = self.tick_time / tick_length
        self.rebuild_dirty()

        # Camera (smoothed between physics ticks)
        target_eye = sneak_eye if self.sneaking else stand_eye
        self.eye += (target_eye - self.eye) * min(1, dt * 20)
        eye = self.eye_position(partial)
        camera.rotation = (self.pitch, self.yaw, 0)
        bob = Vec3(0, 0, 0)
        speed = math.hypot(self.pos.x - self.prev_pos.x, self.pos.z - self.prev_pos.z)
        if self.settings["view_bob"] and self.on_ground and speed > 0.01:
            phase = self.walk_dist * math.pi * 1.2
            strength = min(1.0, speed / 0.2)
            bob = camera.right * math.sin(phase) * 0.03 * strength + Vec3(0, -abs(math.cos(phase)) * 0.05 * strength, 0)
        camera.position = eye + bob
        target_fov = self.settings["fov"] * (1.14 if self.sprinting and self.settings["sprint_fov"] else 1)
        camera.fov += (target_fov - camera.fov) * min(1, dt * 10)

        self.find_target(eye, camera.forward)
        self.outline.enabled = self.target is not None
        if self.target:
            self.outline.position = Vec3(*self.target[0]) + Vec3(0.5, 0.5, 0.5)

        # Block in your hand, with a swing when you place
        self.swing = max(0.0, self.swing - dt * 6)
        swing = math.sin(self.swing * math.pi)
        self.held.position = (0.62 - swing * 0.12, -0.4 - swing * 0.08, 0.95 + swing * 0.1)
        self.held.rotation = (10 + swing * 30, -38 + swing * 20, 0)

        self.update_effects(dt)
        self.update_ghost(partial)
        self.update_hud(partial)

    def update_ghost(self, partial):
        run = self.save["ghosts"].get(self.best_key())
        if not (self.settings["ghost"] and run and run["path"]):
            self.ghost.enabled = False
            return
        path = run["path"]
        if self.start_tick is None:
            i, t = 0, 0.0
        else:
            i, t = min(self.tick_count - self.start_tick, len(path) - 1), partial
        a = Vec3(*path[i])
        b = Vec3(*path[min(i + 1, len(path) - 1)])
        self.ghost.enabled = True
        self.ghost.position = a + (b - a) * t + Vec3(0, player_height / 2, 0)

    def input(self, key):
        if self.paused:
            if self.page == "controls":
                if self.binding:
                    self.finish_binding(key)
                elif key == "escape":
                    self.open_page("settings")
                return
            if self.page == "settings":
                if key == "escape":
                    self.open_page("main")
                return
            if key in ("enter", "space"):
                self.start_playing()
                return
            elif key in ("1", "2", "3", "4"):
                self.choose_mode(int(key) - 1)
            elif key == "t":
                self.choose_direction(not self.diagonal)
            elif key == "escape":
                application.quit()
            return

        # Toggle sneak / sprint (both shift names can arrive for one press, so ignore quick repeats)
        for setting, action, attr in (("sneak_toggle", "sneak", "sneak_on"), ("sprint_toggle", "sprint", "sprint_on")):
            if self.settings[setting] and self.pressed(key, action):
                now = time.time()
                if now - self.last_toggle.get(attr, 0) > 0.1:
                    setattr(self, attr, not getattr(self, attr))
                    self.last_toggle[attr] = now

        if key == "right mouse down":
            self.clicks.append(time.time())
            self.place_block()
        elif key == "left mouse down":
            self.break_block()
        elif self.pressed(key, "reset"):
            self.respawn()
        elif key == "escape":
            self.show_menu(True)
        elif key in [str(n) for n in range(1, 10)]:
            self.select_slot(int(key) - 1)
        elif key == "scroll down":
            self.select_slot(self.slot + 1)
        elif key == "scroll up":
            self.select_slot(self.slot - 1)

######################主程式/ main program######################

def make_sky():
    """Light blue overhead fading to a pale horizon, dark below (the void)"""
    image = Image.new("RGB", (1, 128))
    for y in range(128):
        t = 1 - y / 127  # 0 = top of the sky (images are stored upside down)
        if t < 0.5:
            rgb = tuple(int(a + (b - a) * (t / 0.5)) for a, b in zip((112, 160, 255), (190, 215, 255)))
        else:
            rgb = tuple(int(a + (b - a) * min(1, (t - 0.5) / 0.2)) for a, b in zip((190, 215, 255), (20, 24, 52)))
        image.putpixel((0, y), rgb)
    return Texture(image)


def main():
    app = Ursina(title="Bridge Trainer", borderless=False, development_mode=False)
    window.color = color.rgb32(150, 190, 255)
    window.fps_counter.enabled = True
    window.exit_button.visible = False
    Sky(texture=make_sky())
    BridgeTrainer(app)
    app.run()


if __name__ == "__main__":
    main()
