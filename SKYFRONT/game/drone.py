import math
import random

from panda3d.core import Vec3

from game.models import build_drone
from game.healthbar import WorldHealthBar

DRONE_TYPES = {
    "scout":    {"hp": 1.0,  "speed": 24.0, "scale": 0.8, "damage": 6.0,  "radius": 1.0},
    "standard": {"hp": 3.0,  "speed": 15.0, "scale": 1.0, "damage": 10.0, "radius": 1.3},
    "heavy":    {"hp": 8.0,  "speed": 9.0,  "scale": 1.6, "damage": 22.0, "radius": 2.0},
    "player":   {"hp": 10.0, "speed": 20.0, "scale": 1.1, "damage": 18.0, "radius": 1.4},
}

FLY_LIMIT = 190.0


def clamp(value, low, high):
    return max(low, min(high, value))


class Drone(object):
    """Вымышленный аркадный дрон. Летит сам (ИИ) или управляется игроком."""

    def __init__(self, parent, kind, pos, target=None, controlled=False):
        info = DRONE_TYPES[kind]

        self.kind = kind
        self.hp = float(info["hp"])
        self.max_hp = float(info["hp"])
        self.speed = float(info["speed"])
        self.damage = float(info["damage"])
        self.radius = float(info["radius"])

        self.pos = Vec3(pos)
        self.vel = Vec3(0, 0, 0)
        self.target = Vec3(target) if target is not None else None
        self.controlled = controlled
        self.alive = True

        self.time = random.uniform(0.0, 10.0)
        self.weave_phase = random.uniform(0.0, 6.28)
        self.weave_amp = random.uniform(3.0, 7.0)
        self.cruise_alt = random.uniform(14.0, 26.0)
        self.heading = 0.0
        self.flash = 0.0
        self._flashing = False

        self.node, self.rotors = build_drone(
            parent, info["scale"], controlled
        )
        self.node.setPos(self.pos)
        self.health_bar = WorldHealthBar(
            self.node, width=2.0 * info["scale"], z=2.0 * info["scale"]
        )
        self.health_bar.set(self.hp / self.max_hp)

    # ------------------------------------------------------------------
    def update_ai(self, dt):
        """Полёт к цели со снижением и лёгким рысканьем."""
        self.time += dt

        to_target = self.target - self.pos
        flat = Vec3(to_target.x, to_target.y, 0)
        dist_h = flat.length()
        if dist_h > 0.001:
            flat.normalize()

        side = Vec3(-flat.y, flat.x, 0)
        weave = (
            math.sin(self.time * 1.7 + self.weave_phase)
            * self.weave_amp * min(1.0, dist_h / 30.0)
        )

        desired_z = self.target.z + min(dist_h * 0.45, self.cruise_alt)
        vz = clamp(
            (desired_z - self.pos.z) * 1.5,
            -self.speed * 0.8,
            self.speed * 0.6,
        )

        desired = Vec3(
            flat.x * self.speed + side.x * weave,
            flat.y * self.speed + side.y * weave,
            vz,
        )

        self.vel += (desired - self.vel) * min(1.0, dt * 3.0)
        self.pos += self.vel * dt

        horizontal = math.sqrt(self.vel.x ** 2 + self.vel.y ** 2)
        if horizontal > 0.5:
            self.heading = math.degrees(math.atan2(-self.vel.x, self.vel.y))

        self.apply_visual(dt)

    def fly(self, dt, forward, sideways, vertical, heading, boost):
        """Управление игроком (оператор дронов)."""
        h = math.radians(heading)
        fwd = Vec3(-math.sin(h), math.cos(h), 0)
        right = Vec3(math.cos(h), math.sin(h), 0)

        move = fwd * forward + right * sideways
        if move.length() > 1.0:
            move.normalize()

        speed = self.speed * (1.7 if boost else 1.0)
        desired = Vec3(move.x * speed, move.y * speed, vertical * speed * 0.7)

        self.vel += (desired - self.vel) * min(1.0, dt * 4.0)
        self.pos += self.vel * dt

        self.pos.x = clamp(self.pos.x, -FLY_LIMIT, FLY_LIMIT)
        self.pos.y = clamp(self.pos.y, -FLY_LIMIT, FLY_LIMIT)
        if self.pos.z < 0.6:
            self.pos.z = 0.6
            if self.vel.z < 0:
                self.vel.z = 0
        if self.pos.z > 80.0:
            self.pos.z = 80.0

        self.heading = heading
        self.time += dt
        self.apply_visual(dt)

    def apply_visual(self, dt):
        horizontal = math.sqrt(self.vel.x ** 2 + self.vel.y ** 2)
        tilt = min(horizontal * 0.9, 22.0)

        self.node.setPos(self.pos)
        self.node.setHpr(self.heading, -tilt, 0)

        for index, rotor in enumerate(self.rotors):
            direction = 1.0 if index % 2 == 0 else -1.0
            rotor.setH(rotor.getH() + direction * 1800.0 * dt)

        if self.flash > 0.0:
            self.flash -= dt
            self.node.setColorScale(1.0, 0.35, 0.35, 1.0)
            self._flashing = True
        elif self._flashing:
            self.node.setColorScale(1.0, 1.0, 1.0, 1.0)
            self._flashing = False

    def hit(self, damage):
        """Возвращает True, если дрон уничтожен."""
        self.hp -= damage
        self.health_bar.set(self.hp / self.max_hp)
        self.flash = 0.12
        if self.hp <= 0.0:
            self.alive = False
            return True
        return False

    def destroy(self):
        self.alive = False
        self.health_bar.destroy()
        self.node.removeNode()
