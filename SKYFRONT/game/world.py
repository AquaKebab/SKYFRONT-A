import math

from panda3d.core import AmbientLight, DirectionalLight, Fog, TextureStage, Vec3, Vec4

from game.geometry import make_box, make_cylinder
from game.materials import get_surface_texture
from game.maps import SPAWN_POINTS
from settings import GROUND_SIZE, FOG_NEAR, FOG_FAR

DOOR_COLOR = (0.10, 0.11, 0.13, 1)
DIRS = {"+x": (1, 0), "-x": (-1, 0), "+y": (0, 1), "-y": (0, -1)}


class World(object):
    """Строит карту под узлом root (свет и туман вешаются на root)."""

    def __init__(self, base, root, map_def):
        self.base = base
        self.root = root
        self.map = map_def
        self.pal = map_def["palette"]

        self.static_root = root.attachNewNode("static")
        self.dynamic_root = root.attachNewNode("dynamic")
        self.sky_root = root.attachNewNode("sky")

        # (x, y, полуразмер x, полуразмер y, высота)
        self.obstacles = []
        self.radar_dishes = []
        self.core_flash = 0.0

        cx, cy = map_def["core"]
        self.core_pos = Vec3(cx, cy, 0)
        self.core_target = Vec3(cx, cy, 3.0)
        self.core_radius = 3.5

        self.spawn_points = [Vec3(x, y, 1.0) for x, y in SPAWN_POINTS]
        self.turret_points = [Vec3(x, y, 0) for x, y in map_def["turrets"]]

        self.create_lighting()
        self.create_ground()
        self.create_ground_details()
        self.create_horizon()

        for item in map_def.get("hangars", []):
            self.build_hangar(*item)
        for item in map_def.get("towers", []):
            self.build_tower(*item)
        for item in map_def.get("buildings", []):
            self.build_building(*item)
        for index, item in enumerate(map_def.get("containers", [])):
            self.build_container(index, *item)
        for item in map_def.get("tanks", []):
            self.build_tank(*item)
        for item in map_def.get("lamps", []):
            self.build_lamp(*item)
        for item in map_def.get("radars", []):
            self.build_radar(*item)
        for item in map_def.get("rocks", []):
            self.build_rock(*item)
        for item in map_def.get("trees", []):
            self.build_tree(*item)

        self.build_core()

        self.static_root.flattenStrong()
        self.sky_root.setLightOff()
        self.sky_root.flattenStrong()

    # ------------------------------------------------------------------
    # Помощники
    def box(self, x, y, size, color, z=0.0, solid=False, h=0.0,
            parent=None, texture_kind=None):
        node = make_box("box", size[0], size[1], size[2], color)
        node.reparentTo(parent if parent is not None else self.static_root)
        kind = texture_kind or ("concrete" if solid else "metal")
        node.setTexture(get_surface_texture(kind), 1)
        node.setTexScale(TextureStage.getDefault(), max(1.0, size[0] / 5.0),
                         max(1.0, size[1] / 5.0))
        node.setPos(x, y, z)
        if h:
            node.setH(h)
        if solid:
            self.obstacles.append(
                (x, y, size[0] / 2.0, size[1] / 2.0, z + size[2])
            )
        return node

    def cyl(self, x, y, radius, height, color, z=0.0, segments=12,
            top_radius=None, parent=None):
        node = make_cylinder(
            "cyl", radius, height, color, segments, top_radius
        )
        node.reparentTo(parent if parent is not None else self.static_root)
        node.setTexture(get_surface_texture("metal"), 1)
        node.setTexScale(TextureStage.getDefault(), 2.0, 2.0)
        node.setPos(x, y, z)
        return node

    # ------------------------------------------------------------------
    def create_lighting(self):
        pal = self.pal

        ambient = AmbientLight("ambient")
        a = pal["ambient"]
        ambient.setColor(Vec4(a[0], a[1], a[2], 1))
        self.ambient_np = self.root.attachNewNode(ambient)
        self.root.setLight(self.ambient_np)

        sun = DirectionalLight("sun")
        s = pal["sun"]
        sun.setColor(Vec4(s[0], s[1], s[2], 1))
        self.sun_np = self.root.attachNewNode(sun)
        self.sun_np.setHpr(-35, -55, 0)
        self.root.setLight(self.sun_np)

        fill = DirectionalLight("fill")
        fill.setColor(Vec4(0.22, 0.25, 0.32, 1))
        self.fill_np = self.root.attachNewNode(fill)
        self.fill_np.setHpr(145, -25, 0)
        self.root.setLight(self.fill_np)

        sky = pal["sky"]
        self.fog = Fog("fog")
        self.fog.setColor(sky[0], sky[1], sky[2])
        self.fog.setLinearRange(FOG_NEAR, FOG_FAR)
        self.root.setFog(self.fog)

    def create_ground(self):
        p = self.pal

        slab = make_box("ground", GROUND_SIZE, GROUND_SIZE, 2.0, p["ground"])
        slab.reparentTo(self.static_root)
        terrain_kind = {
            "airbase": "grass", "desert": "sand", "arctic": "snow"
        }.get(self.map.get("id"), "concrete")
        slab.setTexture(get_surface_texture(terrain_kind), 1)
        slab.setTexScale(TextureStage.getDefault(), 90.0, 90.0)
        slab.setZ(-2.0)     # верхняя грань строго на z = 0

        cx, cy = self.map["core"]
        self.box(cx, cy, (30, 30, 0.10), p["pad"], texture_kind="asphalt")
        self.box(0, 0, (380, 8, 0.06), p["road"], texture_kind="asphalt")
        self.box(0, 0, (8, 380, 0.05), p["road"], texture_kind="asphalt")
        for i in range(-5, 6):
            pos = i * 34
            self.box(pos, 0, (8, 0.5, 0.07), p["dash"], texture_kind="concrete")
            self.box(0, pos, (0.5, 8, 0.065), p["dash"], texture_kind="concrete")

        # Площадки запуска дронов
        for sp in self.spawn_points:
            self.box(sp.x, sp.y, (9, 9, 0.15), p["pad"], texture_kind="asphalt")
            self.box(sp.x, sp.y, (2.5, 2.5, 0.30), p["accent"],
                     texture_kind="metal")

    def create_ground_details(self):
        """Разметка, края дорог и небольшие маркеры для читаемости карты."""
        p = self.pal
        # Обочины главных дорожек
        for offset in (-5.2, 5.2):
            self.box(0, offset, (380, 0.18, 0.035), p["dash"],
                     z=0.015, texture_kind="concrete")
            self.box(offset, 0, (0.18, 380, 0.035), p["dash"],
                     z=0.015, texture_kind="concrete")

        # Контрастные маркеры по периметру игровой зоны
        for i in range(8):
            v = -154.0 + i * 44.0
            for x, y in ((v, -178), (v, 178), (-178, v), (178, v)):
                self.box(x, y, (0.55, 0.55, 1.1), p["accent"], z=0.0,
                         texture_kind="metal")
                self.box(x, y, (0.72, 0.72, 0.12), p["dash"], z=1.1,
                         texture_kind="metal")

        # Малые технические площадки около центра
        for x, y in ((-18, -18), (18, -18), (-18, 18), (18, 18)):
            self.box(x, y, (5.0, 5.0, 0.08), p["road"], z=0.01,
                     texture_kind="asphalt")
            self.box(x, y, (0.18, 4.2, 0.05), p["accent"], z=0.06,
                     texture_kind="metal")

    def create_horizon(self):
        p = self.pal
        for i in range(16):
            angle = 2.0 * math.pi * i / 16.0
            dist = 520.0 + 30.0 * math.sin(i * 2.3)
            radius = 80.0 + 25.0 * math.sin(i * 3.1)
            height = 70.0 + 45.0 * abs(math.sin(i * 1.7))
            node = make_cylinder(
                "mountain", radius, height, p["mountain"], 7, 0.0
            )
            node.reparentTo(self.static_root)
            node.setPos(math.cos(angle) * dist, math.sin(angle) * dist, -2.0)

        for i in range(10):
            angle = 2.0 * math.pi * i / 10.0 + 0.3
            dist = 120.0 + 300.0 * abs(math.sin(i * 1.3))
            node = make_box(
                "cloud",
                50.0 + 30.0 * abs(math.sin(i * 2.1)),
                25.0 + 15.0 * abs(math.sin(i * 1.1)),
                6.0, p["cloud"]
            )
            node.reparentTo(self.sky_root)
            node.setPos(
                math.cos(angle) * dist, math.sin(angle) * dist,
                95.0 + 40.0 * abs(math.sin(i * 0.9))
            )

    # ------------------------------------------------------------------
    # Постройки
    def build_hangar(self, x, y, sx, sy, door):
        p = self.pal
        self.box(x, y, (sx, sy, 8), p["hangar"], solid=True)
        self.box(x, y, (sx + 0.2, sy + 0.2, 0.7), p["accent"], z=5.2)
        self.box(x, y, (sx + 1, sy + 1, 0.6), p["roof"], z=8)
        self.box(x, y, (sx - 6, sy - 6, 0.9), p["roof"], z=8.6)

        dx, dy = DIRS[door]
        if dy != 0:
            w = sx * 0.55
            size = (w, 0.3, 5.2)
            stripe = (w + 1.0, 0.34, 0.6)
            px, py = x, y + dy * (sy / 2.0 + 0.05)
        else:
            w = sy * 0.55
            size = (0.3, w, 5.2)
            stripe = (0.34, w + 1.0, 0.6)
            px, py = x + dx * (sx / 2.0 + 0.05), y
        self.box(px, py, size, DOOR_COLOR)
        self.box(px, py, stripe, p["accent"], z=5.2)

    def build_building(self, x, y, sx, sy, sz):
        p = self.pal
        self.box(x, y, (sx, sy, sz), p["building"], solid=True)
        self.box(x, y, (sx + 0.2, sy + 0.2, 1.0), p["glass"], z=sz * 0.45)
        self.box(x, y, (sx + 0.8, sy + 0.8, 0.5), p["roof"], z=sz)
        self.box(x + sx * 0.2, y - sy * 0.15, (3, 3, 1.4), p["hangar"],
                 z=sz + 0.5)

    def build_tower(self, x, y):
        p = self.pal
        self.box(x, y, (10, 10, 14), (0.45, 0.48, 0.50, 1), solid=True)
        self.box(x, y, (10.2, 10.2, 1.5), p["accent"], z=3)
        self.box(x, y, (10.2, 10.2, 1.5), p["accent"], z=8)
        self.box(x, y, (14, 14, 2), (0.25, 0.30, 0.35, 1), z=14)
        self.box(x, y, (12, 12, 2.5), p["glass"], z=16)
        self.box(x, y, (14, 14, 0.5), p["roof"], z=18.5)
        self.box(x, y, (0.3, 0.3, 6), (0.7, 0.7, 0.7, 1), z=19)

    def build_container(self, index, x, y, rot):
        p = self.pal
        colors = p["containers"]
        color = colors[index % len(colors)]
        sx, sy = (8, 4) if rot == 0 else (4, 8)
        self.box(x, y, (sx, sy, 2.6), color, solid=True)
        dark = (color[0] * 0.6, color[1] * 0.6, color[2] * 0.6, 1)
        self.box(x, y, (sx * 0.92, sy * 0.92, 0.15), dark, z=2.6)

    def build_tank(self, x, y, r, h):
        p = self.pal
        self.cyl(x, y, r, h, p["tank"], segments=14)
        self.cyl(x, y, r * 1.03, 0.6, p["accent"], z=h * 0.55, segments=14)
        self.cyl(x, y, r * 0.55, 1.0, p["roof"], z=h, segments=10)
        self.obstacles.append((x, y, r * 0.9, r * 0.9, h))

    def build_lamp(self, x, y):
        self.cyl(x, y, 0.15, 6.2, (0.55, 0.55, 0.50, 1), segments=6)
        self.box(x, y, (1.2, 0.5, 0.25), (0.95, 0.90, 0.60, 1), z=6.1)
        self.obstacles.append((x, y, 0.25, 0.25, 6.0))

    def build_radar(self, x, y):
        p = self.pal
        self.box(x, y, (4, 4, 1.2), p["hangar"], solid=True)
        self.cyl(x, y, 0.4, 3.5, (0.7, 0.7, 0.72, 1), z=1.2, segments=8)

        pivot = self.dynamic_root.attachNewNode("radar")
        pivot.setPos(x, y, 4.7)
        dish = make_cylinder("dish", 2.6, 0.25, (0.85, 0.87, 0.9, 1), 14, 2.2)
        dish.reparentTo(pivot)
        dish.setP(-60)
        feed = make_cylinder("feed", 0.08, 1.3, (0.3, 0.3, 0.3, 1), 6)
        feed.reparentTo(pivot)
        feed.setP(-60)
        feed.setPos(0, 0, 0.1)
        pivot.flattenStrong()
        self.radar_dishes.append(pivot)

    def build_rock(self, x, y, s):
        p = self.pal
        self.box(x, y, (s * 2.0, s * 1.6, s * 1.1), p["rock"], h=25)
        self.box(x + s * 0.3, y - s * 0.2, (s * 1.3, s * 1.1, s * 1.6),
                 p["rock"], h=-15)
        self.box(x - s * 0.5, y + s * 0.4, (s * 0.9, s * 0.8, s * 0.7),
                 p["rock"], h=40)
        self.obstacles.append((x, y, s * 1.0, s * 0.9, s * 1.4))

    def build_tree(self, x, y, s):
        p = self.pal
        self.cyl(x, y, 0.3 * s, 2.4 * s, p["trunk"], segments=6)
        self.cyl(x, y, 2.0 * s, 3.2 * s, p["leaf"], z=1.6 * s,
                 segments=8, top_radius=0.0)
        self.cyl(x, y, 1.5 * s, 2.8 * s, p["leaf"], z=3.6 * s,
                 segments=8, top_radius=0.0)
        self.obstacles.append((x, y, 0.6 * s, 0.6 * s, 4.0 * s))

    def build_core(self):
        cx, cy = self.map["core"]
        self.core_node = self.dynamic_root.attachNewNode("core")
        self.core_node.setPos(cx, cy, 0)

        parent = self.core_node
        self.cyl(0, 0, 4.2, 0.6, (0.15, 0.17, 0.20, 1), segments=16,
                 parent=parent)
        self.cyl(0, 0, 3.3, 0.5, self.pal["accent"], z=0.6, segments=16,
                 parent=parent)
        self.cyl(0, 0, 2.2, 4.5, (0.20, 0.55, 0.75, 1), z=1.1, segments=14,
                 parent=parent)
        glow = self.cyl(0, 0, 2.2, 2.6, (0.5, 0.95, 1.0, 1), z=5.6,
                        segments=14, top_radius=0.0, parent=parent)
        glow.setLightOff()
        self.core_node.flattenStrong()

        self.obstacles.append((cx, cy, 3.0, 3.0, 8.0))

    # ------------------------------------------------------------------
    def flash_core(self):
        self.core_flash = 0.35

    def update(self, dt):
        for dish in self.radar_dishes:
            dish.setH(dish.getH() + 25.0 * dt)

        if self.core_flash > 0.0:
            self.core_flash -= dt
            self.core_node.setColorScale(1.0, 0.35, 0.35, 1.0)
        else:
            self.core_node.setColorScale(1.0, 1.0, 1.0, 1.0)

    def point_in_obstacle(self, x, y, z, margin=0.0):
        for cx, cy, hx, hy, height in self.obstacles:
            if (z <= height + margin
                    and abs(x - cx) <= hx + margin
                    and abs(y - cy) <= hy + margin):
                return True
        return False

    def resolve_collisions(self, x, y, z, radius):
        """Выталкивает круг игрока из построек. Возвращает (x, y)."""
        for cx, cy, hx, hy, height in self.obstacles:
            if z >= height:
                continue

            px = max(cx - hx, min(cx + hx, x))
            py = max(cy - hy, min(cy + hy, y))
            dx = x - px
            dy = y - py
            dist2 = dx * dx + dy * dy

            if dist2 >= radius * radius:
                continue

            if dist2 > 1e-9:
                dist = math.sqrt(dist2)
                k = (radius - dist) / dist
                x += dx * k
                y += dy * k
            else:
                options = (
                    (x - (cx - hx), -1, 0),
                    ((cx + hx) - x, 1, 0),
                    (y - (cy - hy), 0, -1),
                    ((cy + hy) - y, 0, 1),
                )
                dist, sx, sy = min(options, key=lambda o: o[0])
                x += sx * (dist + radius)
                y += sy * (dist + radius)

        return x, y
