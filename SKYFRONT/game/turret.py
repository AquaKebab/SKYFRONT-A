import math
import random

from panda3d.core import Vec3

from game.models import build_turret
from game.healthbar import WorldHealthBar
from settings import (
    TURRET_RANGE,
    TURRET_FIRE_INTERVAL,
    TURRET_DAMAGE,
    TURRET_BULLET_SPEED,
    TURRET_SPREAD,
    TURRET_TURN_SPEED,
)

PIVOT_Z = 1.35      # высота оси ствола над землёй
MUZZLE_LENGTH = 2.4


def clamp(value, low, high):
    return max(low, min(high, value))


class Turret(object):
    """Автоматическая зенитная турель базы (противник оператора)."""

    def __init__(self, parent, pos, audio=None):
        self.pos = Vec3(pos)
        self.node, self.head, self.pitch_node = build_turret(parent)
        self.node.setPos(self.pos)
        self.max_hp = 100.0
        self.hp = self.max_hp
        self.alive = True
        self.audio = audio
        self.health_bar = WorldHealthBar(self.node, width=2.5, z=5.0)
        self.heading = random.uniform(0.0, 360.0)
        self.elevation = 10.0
        self.cooldown = random.uniform(0.5, 1.5)
        self.apply()

    def apply(self):
        self.head.setH(self.heading)
        self.pitch_node.setP(self.elevation)

    def take_damage(self, amount):
        if not self.alive:
            return
        self.hp = max(0.0, self.hp - amount)
        self.health_bar.set(self.hp / self.max_hp)
        if self.hp <= 0.0:
            self.alive = False
            self.health_bar.destroy()
            self.node.removeNode()

    def update(self, dt, drones, projectiles):
        if not self.alive:
            return
        origin = Vec3(self.pos.x, self.pos.y, self.pos.z + PIVOT_Z)

        target = None
        best = TURRET_RANGE
        for drone in drones:
            if not drone.alive:
                continue
            dist = (drone.pos - origin).length()
            if dist < best:
                best = dist
                target = drone

        if target is None:
            self.heading = (self.heading + 20.0 * dt) % 360.0
            self.elevation += (10.0 - self.elevation) * min(1.0, dt * 2.0)
            self.apply()
            return

        lead_time = best / TURRET_BULLET_SPEED * 0.7
        aim = target.pos + target.vel * lead_time
        v = aim - origin

        want_h = math.degrees(math.atan2(-v.x, v.y))
        horizontal = math.sqrt(v.x * v.x + v.y * v.y)
        want_p = math.degrees(math.atan2(v.z, horizontal))

        diff_h = (want_h - self.heading + 180.0) % 360.0 - 180.0
        diff_p = want_p - self.elevation
        step = TURRET_TURN_SPEED * dt

        self.heading = (self.heading + clamp(diff_h, -step, step)) % 360.0
        self.elevation = clamp(
            self.elevation + clamp(diff_p, -step, step), -5.0, 85.0
        )
        self.apply()

        self.cooldown -= dt
        if self.cooldown <= 0.0 and abs(diff_h) < 10.0 and abs(diff_p) < 10.0:
            self.cooldown = TURRET_FIRE_INTERVAL * random.uniform(0.8, 1.3)

            h = math.radians(self.heading)
            p = math.radians(self.elevation)
            direction = Vec3(
                -math.sin(h) * math.cos(p),
                math.cos(h) * math.cos(p),
                math.sin(p),
            )
            direction += Vec3(
                random.uniform(-TURRET_SPREAD, TURRET_SPREAD),
                random.uniform(-TURRET_SPREAD, TURRET_SPREAD),
                random.uniform(-TURRET_SPREAD, TURRET_SPREAD),
            )
            direction.normalize()

            muzzle = origin + direction * MUZZLE_LENGTH
            projectiles.fire(
                "turret", muzzle, direction,
                TURRET_BULLET_SPEED, TURRET_DAMAGE, 1.5
            )
            if self.audio is not None:
                self.audio.play("turret_pulse", 0.25)

    def destroy(self):
        if self.alive:
            self.alive = False
            self.health_bar.destroy()
            self.node.removeNode()
