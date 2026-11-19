import math

from panda3d.core import Vec3

from game.models import build_soldier
from settings import (
    PLAYER_SPEED,
    PLAYER_SPRINT,
    PLAYER_TURN_SPEED,
    PLAYER_JUMP_SPEED,
    PLAYER_RADIUS,
    PLAYER_EYE_HEIGHT,
    PLAYER_PIVOT_HEIGHT,
    GRAVITY,
    CAMERA_SHOULDER,
    GUN_FIRE_RATE,
    GUN_MAGAZINE,
    GUN_RELOAD_TIME,
    WORLD_LIMIT,
)


def clamp(value, low, high):
    return max(low, min(high, value))


class Soldier(object):
    """Защитник базы: движение, прыжок, винтовка."""

    def __init__(self, parent, world, controls, start):
        self.world = world
        self.controls = controls

        self.position = Vec3(start)
        self.velocity_z = 0.0
        self.on_ground = True
        self.heading = controls.heading

        self.model, self.legs, self.left_arm = build_soldier(parent)
        self.model.setPos(self.position)

        self.walk_phase = 0.0
        self.swing_amp = 0.0
        self.combat_timer = 0.0

        self.ammo = GUN_MAGAZINE
        self.fire_cd = 0.0
        self.reload_t = 0.0

    # ------------------------------------------------------------------
    def update(self, dt, firing):
        c = self.controls

        forward, sideways = c.move_axes()
        angle = math.radians(c.heading)
        cam_forward = Vec3(-math.sin(angle), math.cos(angle), 0)
        cam_right = Vec3(math.cos(angle), math.sin(angle), 0)

        move = cam_forward * forward + cam_right * sideways
        moving = move.length() > 0.001

        speed = PLAYER_SPEED * (PLAYER_SPRINT if c.is_down("shift") else 1.0)

        if moving:
            move.normalize()      # диагональ не быстрее
            self.position.x += move.x * speed * dt
            self.position.y += move.y * speed * dt

        # Прыжок и гравитация
        if c.is_down("space") and self.on_ground:
            self.velocity_z = PLAYER_JUMP_SPEED
            self.on_ground = False

        if not self.on_ground:
            self.velocity_z -= GRAVITY * dt
            self.position.z += self.velocity_z * dt
            if self.position.z <= 0.0:
                self.position.z = 0.0
                self.velocity_z = 0.0
                self.on_ground = True

        # Постройки и границы мира
        x, y = self.world.resolve_collisions(
            self.position.x, self.position.y, self.position.z, PLAYER_RADIUS
        )
        self.position.x = clamp(x, -WORLD_LIMIT, WORLD_LIMIT)
        self.position.y = clamp(y, -WORLD_LIMIT, WORLD_LIMIT)

        # Направление модели
        if firing:
            self.combat_timer = 1.2
        elif self.combat_timer > 0.0:
            self.combat_timer = max(0.0, self.combat_timer - dt)

        if c.camera_mode == 1 or self.combat_timer > 0.0:
            self.heading = c.heading
        elif moving:
            target = math.degrees(math.atan2(-move.x, move.y))
            diff = (target - self.heading + 180.0) % 360.0 - 180.0
            step = PLAYER_TURN_SPEED * dt
            self.heading = (self.heading + clamp(diff, -step, step)) % 360.0

        # Анимация ходьбы
        target_amp = 1.0 if (moving and self.on_ground) else 0.0
        self.swing_amp += (target_amp - self.swing_amp) * min(1.0, dt * 10.0)
        if moving:
            self.walk_phase += dt * speed * 0.9
        swing = math.sin(self.walk_phase) * 35.0 * self.swing_amp
        self.legs[0].setP(swing)
        self.legs[1].setP(-swing)
        self.left_arm.setP(-swing * 0.6)

        self.model.setPos(self.position)
        self.model.setH(self.heading)

    def update_camera(self):
        pos = self.position
        pivot = Vec3(pos.x, pos.y, pos.z + PLAYER_PIVOT_HEIGHT)
        eye = Vec3(pos.x, pos.y, pos.z + PLAYER_EYE_HEIGHT)
        return self.controls.update_camera(pivot, eye, CAMERA_SHOULDER)

    # ------------------------------------------------------------------
    # Оружие
    def update_weapon(self, dt):
        self.fire_cd = max(0.0, self.fire_cd - dt)
        if self.reload_t > 0.0:
            self.reload_t -= dt
            if self.reload_t <= 0.0:
                self.reload_t = 0.0
                self.ammo = GUN_MAGAZINE

    def start_reload(self):
        if self.reload_t <= 0.0 and self.ammo < GUN_MAGAZINE:
            self.reload_t = GUN_RELOAD_TIME
            return True
        return False

    def can_fire(self):
        return self.reload_t <= 0.0 and self.ammo > 0 and self.fire_cd <= 0.0

    def consume_shot(self):
        self.ammo -= 1
        self.fire_cd = 1.0 / GUN_FIRE_RATE
        if self.ammo <= 0:
            self.start_reload()

    def muzzle_position(self):
        c = self.controls
        pos = self.position
        if c.camera_mode == 1:
            eye = Vec3(pos.x, pos.y, pos.z + PLAYER_EYE_HEIGHT)
            return eye + c.view_direction() * 0.6

        h = math.radians(c.heading)
        forward = Vec3(-math.sin(h), math.cos(h), 0)
        right = Vec3(math.cos(h), math.sin(h), 0)
        return Vec3(pos.x, pos.y, pos.z + 1.45) + forward * 1.0 + right * 0.45

    def destroy(self):
        self.model.removeNode()
