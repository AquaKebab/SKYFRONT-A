import math
import random

from panda3d.core import Vec3

from game.controls import clamp
from game.audio import AudioManager
from game.drone import Drone
from game.effects import Effects
from game.player import Soldier
from game.projectile import Projectiles
from game.turret import Turret
from game.ui import Hud
from game.world import World
from settings import (
    BASE_INTEGRITY,
    DEFENDER_WAVES,
    ATTACKER_BUDGET,
    LAUNCH_COOLDOWN,
    GUN_MAGAZINE,
    BULLET_SPEED,
    BULLET_LIFE,
    BULLET_DAMAGE,
    LOOK_MAX_PITCH,
    TURRET_COUNT,
)

SCORE_VALUES = {"scout": 15, "standard": 10, "heavy": 30, "player": 0}


class Session(object):
    """Общая часть обоих режимов: мир, дроны, пули, эффекты, интерфейс."""

    side = ""

    def __init__(self, base, controls, map_def):
        self.base = base
        self.controls = controls
        self.map_def = map_def

        self.root = base.render.attachNewNode("session")
        self.world = World(base, self.root, map_def)
        self.effects = Effects(self.root)
        self.projectiles = Projectiles(self)
        self.hud = Hud(base, self.side)
        self.audio = AudioManager(base)

        self.drones = []
        self.integrity = float(BASE_INTEGRITY)
        self.score = 0
        self.time = 0.0
        self.finished = False
        self.result = None

    # ------------------------------------------------------------------
    def update(self, dt):
        if self.finished:
            return

        self.time += dt
        self.controls.update(dt)

        self.update_mode(dt)
        self.update_drones(dt)
        self.projectiles.update(dt)
        self.effects.update(dt)
        self.world.update(dt)

        self.check_end()
        self.hud.set_integrity(self.integrity / BASE_INTEGRITY)
        self.update_hud()
        self.hud.update(dt)

    def update_mode(self, dt):
        pass

    def update_hud(self):
        pass

    def check_end(self):
        if self.integrity <= 0.0:
            self.finish("win" if self.side == "attacker" else "lose")

    def finish(self, result):
        self.finished = True
        self.result = result

    def summary(self):
        return []

    # ------------------------------------------------------------------
    def update_drones(self, dt):
        world = self.world
        for drone in list(self.drones):
            if not drone.alive:
                continue

            if not drone.controlled:
                drone.update_ai(dt)

            distance = (drone.pos - world.core_target).length()
            if distance < world.core_radius + drone.radius:
                self.impact(drone)
                continue

            # Контакт с игровой турелью повреждает обе стороны столкновения.
            turret_contact = False
            for turret in getattr(self, "turrets", []):
                if turret.alive and (drone.pos - turret.pos).length() < 3.8:
                    turret.take_damage(max(8.0, drone.damage * 1.8))
                    turret_contact = True
                    break

            if turret_contact:
                self.effects.explosion(drone.pos, 0.8)
                self.hud.show_message("DEFENSE UNIT DAMAGED", 1.2)
                self.remove_drone(drone)
                continue

            if drone.controlled and world.point_in_obstacle(
                drone.pos.x, drone.pos.y, drone.pos.z, drone.radius * 0.5
            ):
                self.effects.explosion(drone.pos, 1.2)
                self.hud.show_message("DRONE CRASHED", 1.5)
                self.remove_drone(drone)

    def impact(self, drone):
        self.integrity = max(0.0, self.integrity - drone.damage)
        self.world.flash_core()
        self.effects.explosion(self.world.core_target, 1.8)
        self.hud.show_message("BASE HIT!", 1.2)
        self.audio.play("base_warning", 0.75)
        self.remove_drone(drone)

    def remove_drone(self, drone):
        if drone in self.drones:
            self.drones.remove(drone)
        if drone.controlled:
            self.audio.stop_hum()
        drone.destroy()
        self.on_drone_removed(drone)

    def on_drone_removed(self, drone):
        pass

    def on_drone_destroyed(self, drone, by):
        self.effects.explosion(drone.pos, 0.8 + drone.radius * 0.4)
        self.audio.play("drone_pop", 0.6)
        if by == "player":
            self.score += SCORE_VALUES.get(drone.kind, 0)
        self.remove_drone(drone)

    def spawn_drone(self, kind, controlled=False):
        spawn = random.choice(self.world.spawn_points)
        pos = Vec3(
            spawn.x + random.uniform(-3, 3),
            spawn.y + random.uniform(-3, 3),
            2.0,
        )
        drone = Drone(
            self.root, kind, pos,
            target=self.world.core_target, controlled=controlled,
        )
        self.drones.append(drone)
        if controlled:
            self.audio.start_hum()
        return drone

    def destroy(self):
        self.hud.destroy()
        self.projectiles.destroy()
        self.audio.destroy()
        self.root.removeNode()


# ======================================================================
class DefenderSession(Session):
    """Игрок стреляет по дронам, которых запускает ИИ волнами."""

    side = "defender"

    def __init__(self, base, controls, map_def):
        Session.__init__(self, base, controls, map_def)

        self.soldier = Soldier(
            self.root, self.world, controls, Vec3(0, -14, 0)
        )
        controls.reset_view(0.0, 5.0)

        self.wave = 0
        self.total_waves = DEFENDER_WAVES
        self.state = "break"
        self.timer = 3.0
        self.queue = []
        self.spawn_timer = 0.0
        self.shots = 0
        self.kills = 0

        self.hud.show_message("GET READY", 2.5)

    # ------------------------------------------------------------------
    def update_mode(self, dt):
        c = self.controls
        firing = c.fire_down()

        self.soldier.update(dt, firing)

        if c.camera_mode == 1:
            self.soldier.model.hide()
        else:
            self.soldier.model.show()

        cam_pos, direction = self.soldier.update_camera()

        if c.take("reload"):
            if self.soldier.start_reload():
                self.audio.play("reload", 0.55)
        self.soldier.update_weapon(dt)

        if firing and self.soldier.can_fire():
            self.shoot(cam_pos, direction)

        self.update_waves(dt)

    def find_aim_point(self, cam_pos, direction):
        """Точка прицеливания: луч камеры, с небольшой помощью по дронам."""
        best_t = None
        best_drone = None
        for drone in self.drones:
            if not drone.alive:
                continue
            v = drone.pos - cam_pos
            t = v.dot(direction)
            if t < 1.0 or t > 180.0:
                continue
            miss = (v - direction * t).length()
            if miss < drone.radius * 2.0 and (best_t is None or t < best_t):
                best_t = t
                best_drone = drone

        if best_drone is None:
            return cam_pos + direction * 150.0

        # упреждение: пуля летит не мгновенно
        flight = best_t / BULLET_SPEED * 0.9
        return best_drone.pos + best_drone.vel * flight

    def shoot(self, cam_pos, direction):
        muzzle = self.soldier.muzzle_position()
        aim = self.find_aim_point(cam_pos, direction)

        shot_dir = aim - muzzle
        if shot_dir.length() < 0.1:
            shot_dir = Vec3(direction)
        shot_dir.normalize()

        self.projectiles.fire(
            "player", muzzle, shot_dir, BULLET_SPEED, BULLET_DAMAGE, BULLET_LIFE
        )
        self.audio.play("energy_pulse", 0.35)
        self.soldier.consume_shot()
        self.shots += 1

        # лёгкая отдача
        self.controls.pitch = min(self.controls.pitch + 0.12, LOOK_MAX_PITCH)

    # ------------------------------------------------------------------
    def build_queue(self, wave):
        queue = ["standard"] * (2 + wave)
        queue += ["scout"] * (2 * (wave - 1))
        queue += ["heavy"] * (wave // 2)
        random.shuffle(queue)
        return queue

    def update_waves(self, dt):
        if self.state == "break":
            self.timer -= dt
            if self.timer <= 0.0:
                self.wave += 1
                self.queue = self.build_queue(self.wave)
                self.spawn_timer = 0.5
                self.state = "wave"
                self.hud.show_message(
                    "WAVE %d / %d" % (self.wave, self.total_waves), 2.5
                )
            return

        self.spawn_timer -= dt
        if self.queue and self.spawn_timer <= 0.0:
            self.spawn_drone(self.queue.pop())
            self.spawn_timer = random.uniform(1.0, 2.0)

        if not self.queue and not self.drones:
            if self.wave >= self.total_waves:
                self.finish("win")
            else:
                self.state = "break"
                self.timer = 5.0
                self.hud.show_message("WAVE %d CLEARED" % self.wave, 2.5)

    def on_drone_destroyed(self, drone, by):
        Session.on_drone_destroyed(self, drone, by)
        self.kills += 1

    def update_hud(self):
        self.hud.set_info(
            "WAVE %d/%d    SCORE %d    DRONES %d" % (
                max(1, self.wave), self.total_waves, self.score,
                len(self.drones) + len(self.queue),
            )
        )
        if self.soldier.reload_t > 0.0:
            self.hud.set_status("RELOADING...")
        else:
            self.hud.set_status(
                "AMMO %d / %d" % (self.soldier.ammo, GUN_MAGAZINE)
            )

    def summary(self):
        accuracy = 0
        if self.shots > 0:
            accuracy = int(100.0 * self.kills / max(1, self.shots))
        return [
            "Waves reached: %d / %d" % (max(1, self.wave), self.total_waves),
            "Drones shot down: %d" % self.kills,
            "Score: %d" % self.score,
            "Base integrity left: %d%%" % int(
                100.0 * self.integrity / BASE_INTEGRITY
            ),
        ]

    def destroy(self):
        self.soldier.destroy()
        Session.destroy(self)


# ======================================================================
class AttackerSession(Session):
    """Игрок пилотирует дрон и запускает ещё; турели базы стреляют по ним."""

    side = "attacker"

    def __init__(self, base, controls, map_def):
        Session.__init__(self, base, controls, map_def)

        self.budget = ATTACKER_BUDGET
        self.pilot = None
        self.respawn_time = 0.5
        self.launch_cooldown = 0.0
        self.launched = 0

        self.turrets = []
        for point in self.world.turret_points[:TURRET_COUNT]:
            self.turrets.append(Turret(self.root, point, self.audio))
            self.world.obstacles.append((point.x, point.y, 1.3, 1.3, 2.2))

        controls.reset_view(0.0, -8.0)
        self.hud.show_message("LAUNCH!", 2.0)

    # ------------------------------------------------------------------
    def spawn_pilot(self):
        if self.budget <= 0:
            return
        self.budget -= 1

        pilot = self.spawn_drone("player", controlled=True)
        self.pilot = pilot

        core = self.world.core_target
        dx = core.x - pilot.pos.x
        dy = core.y - pilot.pos.y
        self.controls.reset_view(math.degrees(math.atan2(-dx, dy)), -8.0)
        pilot.heading = self.controls.heading

    def on_drone_removed(self, drone):
        if drone is self.pilot:
            self.pilot = None
            self.respawn_time = 2.5
            if self.budget > 0:
                self.hud.show_message("DRONE LOST - RESPAWNING", 2.0)

    def launch_ai(self, kind, cost):
        if self.launch_cooldown > 0.0:
            return
        if self.budget < cost:
            self.hud.show_message("NOT ENOUGH DRONES", 1.5)
            return
        self.budget -= cost
        self.launched += 1
        self.launch_cooldown = LAUNCH_COOLDOWN
        self.spawn_drone(kind)

    # ------------------------------------------------------------------
    def update_mode(self, dt):
        c = self.controls
        self.launch_cooldown = max(0.0, self.launch_cooldown - dt)

        if c.take("launch1"):
            self.launch_ai("standard", 1)
        if c.take("launch2"):
            self.launch_ai("heavy", 2)

        if self.pilot is None:
            self.respawn_time -= dt
            if self.respawn_time <= 0.0 and self.budget > 0:
                self.spawn_pilot()
        else:
            forward, sideways = c.move_axes()
            vertical = 0
            if c.is_down("space"):
                vertical += 1
            if c.is_down("c"):
                vertical -= 1

            self.pilot.fly(
                dt, forward, sideways, vertical,
                c.heading, c.is_down("shift"),
            )

            if c.camera_mode == 1:
                self.pilot.node.hide()
            else:
                self.pilot.node.show()

            pos = self.pilot.pos
            c.update_camera(
                Vec3(pos.x, pos.y, pos.z + 0.7),
                Vec3(pos.x, pos.y, pos.z + 0.25),
            )

        for turret in self.turrets:
            turret.update(dt, self.drones, self.projectiles)

    def check_end(self):
        Session.check_end(self)
        if (not self.finished and self.budget <= 0
                and self.pilot is None and not self.drones):
            self.finish("lose")

    def update_hud(self):
        self.hud.set_info(
            "DRONES LEFT %d    BASE %d%%" % (
                self.budget,
                int(100.0 * self.integrity / BASE_INTEGRITY),
            )
        )
        if self.launch_cooldown > 0.0:
            self.hud.set_status("LAUNCH READY IN %.1f" % self.launch_cooldown)
        else:
            self.hud.set_status("LAUNCH READY")

        if self.pilot is not None:
            self.hud.set_hp(self.pilot.hp / self.pilot.max_hp)
        else:
            self.hud.set_hp(None)

    def summary(self):
        return [
            "Base integrity left: %d%%" % int(
                100.0 * self.integrity / BASE_INTEGRITY
            ),
            "Drones left: %d" % self.budget,
            "Drones launched: %d" % self.launched,
        ]

    def destroy(self):
        for turret in self.turrets:
            turret.destroy()
        Session.destroy(self)
