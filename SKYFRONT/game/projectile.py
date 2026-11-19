from panda3d.core import NodePath, Point3, Vec3

from game.geometry import make_box


def segment_hits_sphere(p0, p1, center, radius):
    """Проверка пересечения отрезка движения пули со сферой дрона."""
    d = p1 - p0
    dd = d.dot(d)
    if dd < 1e-9:
        t = 0.0
    else:
        t = (center - p0).dot(d) / dd
        t = max(0.0, min(1.0, t))
    closest = p0 + d * t
    return (closest - center).lengthSquared() <= radius * radius


class Bullet(object):
    def __init__(self, owner, node, pos, vel, life, damage):
        self.owner = owner
        self.node = node
        self.pos = Vec3(pos)
        self.vel = Vec3(vel)
        self.life = life
        self.damage = damage


class Projectiles(object):
    """Пули игрока и турелей. Летят по-настоящему, а не мгновенно."""

    def __init__(self, session):
        self.session = session
        self.root = session.root.attachNewNode("bullets")
        self.templates = {
            "player": self._template((1.0, 0.90, 0.30, 1)),
            "turret": self._template((1.0, 0.35, 0.20, 1)),
        }
        self.bullets = []

    def _template(self, color):
        holder = NodePath("bullet_template")
        box = make_box("bullet", 0.10, 0.70, 0.10, color)
        box.reparentTo(holder)
        box.setZ(-0.05)
        holder.setLightOff()
        return holder

    def fire(self, owner, pos, direction, speed, damage, life):
        direction = Vec3(direction)
        direction.normalize()

        node = self.templates[owner].copyTo(self.root)
        node.setPos(pos)
        node.lookAt(Point3(pos.x + direction.x, pos.y + direction.y,
                           pos.z + direction.z))

        self.bullets.append(
            Bullet(owner, node, pos, direction * speed, life, damage)
        )

    def update(self, dt):
        session = self.session
        for bullet in list(self.bullets):
            p0 = Vec3(bullet.pos)
            bullet.pos += bullet.vel * dt
            bullet.life -= dt

            hit = False
            for drone in session.drones:
                if not drone.alive:
                    continue
                if segment_hits_sphere(
                    p0, bullet.pos, drone.pos, drone.radius * 1.15
                ):
                    session.effects.spark(bullet.pos)
                    session.audio.play("drone_hit", 0.32)
                    if drone.hit(bullet.damage):
                        session.on_drone_destroyed(drone, bullet.owner)
                    hit = True
                    break

            if not hit:
                pos = bullet.pos
                if pos.z < 0.0 or session.world.point_in_obstacle(
                    pos.x, pos.y, pos.z
                ):
                    session.effects.spark(bullet.pos)
                    hit = True

            if hit or bullet.life <= 0.0:
                bullet.node.removeNode()
                self.bullets.remove(bullet)
            else:
                bullet.node.setPos(bullet.pos)

    def destroy(self):
        self.root.removeNode()
        self.bullets = []
