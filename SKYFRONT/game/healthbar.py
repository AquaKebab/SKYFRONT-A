from game.geometry import make_box


class WorldHealthBar(object):
    """Компактная плавающая полоска здоровья для игровых объектов."""

    def __init__(self, parent, width=2.0, z=2.5):
        self.width = width
        self.root = parent.attachNewNode("world_health_bar")
        self.root.setPos(0, 0, z)
        self.root.setBillboardPointEye()
        self.root.setLightOff()
        self.back = make_box("hp_back", width, 0.10, 0.16, (0.04, 0.05, 0.06, 0.92))
        self.back.reparentTo(self.root)
        self.fill = make_box("hp_fill", width * 0.96, 0.055, 0.105,
                             (0.20, 0.88, 0.35, 1))
        self.fill.reparentTo(self.root)
        self.fill.setPos(0, -0.012, 0.025)
        self.set(1.0)

    def set(self, fraction):
        f = max(0.0, min(1.0, float(fraction)))
        self.fill.setScale(max(0.001, f), 1, 1)
        self.fill.setX(-self.width * 0.48 * (1.0 - f))
        if f > 0.55:
            color = (0.18, 0.88, 0.32, 1)
        elif f > 0.25:
            color = (1.0, 0.68, 0.12, 1)
        else:
            color = (0.95, 0.20, 0.16, 1)
        self.fill.setColor(*color)

    def destroy(self):
        self.root.removeNode()
