import random

from panda3d.core import NodePath, Vec3

from game.geometry import make_box


class Effects(object):
    """Дешёвые эффекты: взрывы и искры из маленьких кубиков."""

    MAX_ITEMS = 140

    def __init__(self, parent):
        self.root = parent.attachNewNode("effects")
        self.items = []

        self.templates = {
            "fire": self._template((1.0, 0.55, 0.10, 1), 0.35),
            "smoke": self._template((0.25, 0.25, 0.27, 1), 0.40),
            "spark": self._template((1.0, 0.95, 0.50, 1), 0.15),
            "flash": self._template((1.0, 0.90, 0.55, 1), 1.0),
        }

    def _template(self, color, size):
        holder = NodePath("effect_template")
        box = make_box("p", size, size, size, color)
        box.reparentTo(holder)
        box.setZ(-size / 2.0)
        holder.setLightOff()
        return holder

    def _spawn(self, kind, pos, velocity, life, scale, gravity):
        if len(self.items) >= self.MAX_ITEMS:
            return
        node = self.templates[kind].copyTo(self.root)
        node.setPos(pos)
        node.setScale(scale)
        self.items.append({
            "node": node,
            "pos": Vec3(pos),
            "vel": velocity,
            "life": life,
            "max": life,
            "scale": scale,
            "gravity": gravity,
        })

    def explosion(self, pos, size=1.0):
        self._spawn("flash", pos, Vec3(0, 0, 0), 0.18, 2.5 * size, 0.0)
        for _ in range(10):
            vel = Vec3(
                random.uniform(-1, 1),
                random.uniform(-1, 1),
                random.uniform(-0.3, 1),
            )
            vel *= random.uniform(6.0, 14.0) * size
            kind = "fire" if random.random() < 0.6 else "smoke"
            self._spawn(
                kind, pos, vel, random.uniform(0.5, 1.0),
                random.uniform(0.8, 1.6) * size, 9.0
            )

    def spark(self, pos):
        for _ in range(4):
            vel = Vec3(
                random.uniform(-1, 1),
                random.uniform(-1, 1),
                random.uniform(0, 1),
            ) * random.uniform(4.0, 9.0)
            self._spawn("spark", pos, vel, random.uniform(0.15, 0.3), 1.0, 12.0)

    def update(self, dt):
        for item in list(self.items):
            item["life"] -= dt
            if item["life"] <= 0.0:
                item["node"].removeNode()
                self.items.remove(item)
                continue

            item["vel"].z -= item["gravity"] * dt
            item["pos"] += item["vel"] * dt
            item["node"].setPos(item["pos"])
            item["node"].setScale(
                max(0.01, item["scale"] * item["life"] / item["max"])
            )
