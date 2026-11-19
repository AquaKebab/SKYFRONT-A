import math

from panda3d.core import TextureStage

from game.geometry import make_box, make_cylinder
from game.materials import get_surface_texture


def _add(parent, node, x=0.0, y=0.0, z=0.0, h=0.0):
    node.reparentTo(parent)
    node.setPos(x, y, z)
    if h:
        node.setH(h)
    return node


def build_soldier(parent):
    """Низкополигональный солдат с винтовкой. Лицо направлено в +Y.

    Возвращает (корень, [левая нога, правая нога], левая рука).
    """
    root = parent.attachNewNode("soldier")

    skin = (0.85, 0.68, 0.55, 1)
    vest = (0.15, 0.42, 0.72, 1)
    pants = (0.16, 0.18, 0.22, 1)
    olive = (0.25, 0.32, 0.22, 1)
    dark = (0.10, 0.10, 0.12, 1)
    visor = (0.30, 0.85, 0.95, 1)

    legs = []
    for sx in (-0.17, 0.17):
        hip = root.attachNewNode("leg")
        hip.setPos(sx, 0, 0.85)
        _add(hip, make_box("leg", 0.28, 0.30, 0.85, pants), 0, 0, -0.85)
        _add(hip, make_box("boot", 0.30, 0.42, 0.18, dark), 0, 0.04, -0.85)
        hip.flattenStrong()
        legs.append(hip)

    left_arm = root.attachNewNode("left_arm")
    left_arm.setPos(-0.46, 0, 1.55)
    _add(left_arm, make_box("arm", 0.20, 0.22, 0.65, vest), 0, 0, -0.65)
    left_arm.flattenStrong()

    right_arm = root.attachNewNode("right_arm")
    right_arm.setPos(0.46, 0, 1.55)
    right_arm.setP(80)
    _add(right_arm, make_box("arm", 0.20, 0.22, 0.65, vest), 0, 0, -0.65)
    right_arm.flattenStrong()

    body = root.attachNewNode("body")
    _add(body, make_box("torso", 0.72, 0.42, 0.78, vest), 0, 0, 0.85)
    _add(body, make_box("belt", 0.74, 0.44, 0.10, dark), 0, 0, 0.85)
    _add(body, make_box("pack", 0.50, 0.22, 0.55, olive), 0, -0.30, 0.95)
    _add(body, make_box("head", 0.36, 0.36, 0.34, skin), 0, 0, 1.63)
    _add(body, make_box("helmet", 0.46, 0.46, 0.20, olive), 0, 0, 1.84)
    _add(body, make_box("visor", 0.30, 0.06, 0.10, visor), 0, 0.21, 1.74)
    # винтовка
    _add(body, make_box("gun", 0.12, 0.90, 0.16, dark), 0.44, 0.25, 1.40)
    _add(body, make_box("barrel", 0.06, 0.50, 0.06, dark), 0.44, 0.95, 1.46)
    _add(body, make_box("sight", 0.06, 0.20, 0.07, dark), 0.44, 0.20, 1.56)
    body.flattenStrong()

    return root, legs, left_arm


def build_drone(parent, s=1.0, player=False):
    """Квадрокоптер. Возвращает (корень, список винтов)."""
    root = parent.attachNewNode("drone")
    body = root.attachNewNode("drone_body")

    dark = (0.13, 0.14, 0.17, 1)
    if player:
        shell = (0.16, 0.28, 0.55, 1)
        accent = (0.20, 0.85, 1.00, 1)
    else:
        shell = (0.28, 0.30, 0.34, 1)
        accent = (0.90, 0.15, 0.12, 1)

    _add(body, make_box("shell", 0.9 * s, 1.3 * s, 0.32 * s, shell))
    _add(body, make_box("top", 0.55 * s, 0.8 * s, 0.16 * s, dark),
         0, -0.05 * s, 0.32 * s)
    _add(body, make_box("eye", 0.32 * s, 0.12 * s, 0.14 * s, (1, 0.85, 0.2, 1)),
         0, 0.66 * s, 0.08 * s)
    _add(body, make_box("tail", 0.14 * s, 0.14 * s, 0.14 * s, accent),
         0, -0.70 * s, 0.10 * s)
    # Дополнительные панели корпуса и световые метки — стилизованный игровой БПЛА.
    _add(body, make_box("front_sensor", 0.42 * s, 0.10 * s, 0.12 * s,
                        (0.18, 0.85, 0.95, 1)), 0, 0.72 * s, 0.12 * s)
    _add(body, make_box("left_panel", 0.10 * s, 0.48 * s, 0.18 * s,
                        (0.34, 0.38, 0.43, 1)), -0.48 * s, -0.10 * s, 0.02 * s)
    _add(body, make_box("right_panel", 0.10 * s, 0.48 * s, 0.18 * s,
                        (0.34, 0.38, 0.43, 1)), 0.48 * s, -0.10 * s, 0.02 * s)
    _add(body, make_box("arm_a", 2.5 * s, 0.16 * s, 0.08 * s, dark),
         0, 0, 0.14 * s, 45)
    _add(body, make_box("arm_b", 2.5 * s, 0.16 * s, 0.08 * s, dark),
         0, 0, 0.14 * s, -45)

    rotors = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            px = sx * 0.88 * s
            py = sy * 0.88 * s
            _add(body, make_cylinder("motor", 0.13 * s, 0.24 * s, dark, 8),
                 px, py, 0.10 * s)

            rotor = root.attachNewNode("rotor")
            rotor.setPos(px, py, 0.36 * s)
            blade = (0.75, 0.75, 0.78, 1)
            _add(rotor, make_box("blade", 1.15 * s, 0.08 * s, 0.02 * s, blade))
            _add(rotor, make_box("blade", 0.08 * s, 1.15 * s, 0.02 * s, blade))
            rotor.flattenStrong()
            rotors.append(rotor)

    body.flattenStrong()
    body.setTexture(get_surface_texture("metal" if player else "camo"), 1)
    body.setTexScale(TextureStage.getDefault(), 2.0, 2.0)
    return root, rotors


def build_turret(parent):
    """Фантазийная энергетическая турель базы с декоративными панелями."""
    root = parent.attachNewNode("turret")

    base_col = (0.22, 0.27, 0.31, 1)
    head_col = (0.34, 0.42, 0.46, 1)
    dark = (0.08, 0.11, 0.14, 1)
    glow = (0.10, 0.78, 0.95, 1)
    metal_texture = get_surface_texture("metal")

    base = root.attachNewNode("turret_base")
    _add(base, make_cylinder("base", 1.7, 0.65, base_col, 16))
    _add(base, make_cylinder("lower_ring", 1.82, 0.12, dark, 16), 0, 0, 0.12)
    _add(base, make_cylinder("rotation_ring", 1.35, 0.22, glow, 16), 0, 0, 0.65)
    for i in range(8):
        angle = math.radians(i * 45.0)
        _add(base, make_box("base_bolt", 0.18, 0.18, 0.12,
                            (0.70, 0.76, 0.78, 1)),
             math.cos(angle) * 1.48, math.sin(angle) * 1.48, 0.30)
    base.flattenStrong()
    base.setTexture(metal_texture, 1)

    head = root.attachNewNode("turret_head")
    head.setZ(0.82)
    _add(head, make_box("head", 1.45, 1.65, 0.72, head_col))
    _add(head, make_box("front_display", 0.78, 0.10, 0.30, glow),
         0, 0.84, 0.18)
    _add(head, make_box("top_armor", 1.12, 1.05, 0.22, dark),
         0, -0.12, 0.52)
    _add(head, make_box("left_armor", 0.18, 1.10, 0.48, base_col),
         -0.78, -0.10, 0.05)
    _add(head, make_box("right_armor", 0.18, 1.10, 0.48, base_col),
         0.78, -0.10, 0.05)

    pitch = head.attachNewNode("turret_pitch")
    pitch.setZ(0.48)
    # Условный световой излучатель вместо реалистичной оружейной конструкции.
    emitter = make_cylinder("emitter", 0.22, 2.15, dark, 10)
    emitter.setP(-90)
    _add(pitch, emitter, 0, 0.25, 0)
    emitter_ring = make_cylinder("emitter_ring", 0.30, 0.16, glow, 12)
    emitter_ring.setP(-90)
    _add(pitch, emitter_ring, 0, 1.65, 0)
    _add(pitch, make_box("emitter_mount", 0.72, 0.72, 0.48, base_col),
         0, 0.05, -0.22)
    pitch.flattenStrong()
    head.setTexture(metal_texture, 1)
    root.setTexture(metal_texture, 1)
    root.setTexScale(TextureStage.getDefault(), 1.5, 1.5)

    return root, head, pitch
