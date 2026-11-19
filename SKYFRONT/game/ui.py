from direct.gui.DirectGui import DirectFrame, DGG
from direct.gui.OnscreenText import OnscreenText
from panda3d.core import TextNode


class Bar(object):
    """Полоса (здоровье, целостность базы)."""

    def __init__(self, parent, pos, width, height, color):
        self.width = width
        self.height = height
        self.bg = DirectFrame(
            parent=parent,
            frameColor=(0, 0, 0, 0.55),
            frameSize=(0, width, 0, height),
            pos=(pos[0], 0, pos[1]),
            relief=DGG.FLAT,
        )
        self.fg = DirectFrame(
            parent=self.bg,
            frameColor=color,
            frameSize=(0, width, 0, height),
            pos=(0, 0, 0),
            relief=DGG.FLAT,
        )

    def set(self, fraction):
        f = max(0.0, min(1.0, fraction))
        self.fg["frameSize"] = (0, max(0.0001, self.width * f), 0, self.height)

    def show(self):
        self.bg.show()

    def hide(self):
        self.bg.hide()

    def destroy(self):
        self.fg.destroy()
        self.bg.destroy()


HELP_DEFENDER = (
    "WASD move   SHIFT sprint   SPACE jump\n"
    "MOUSE aim   LMB fire   R reload\n"
    "V camera   WHEEL zoom   ESC pause"
)
HELP_ATTACKER = (
    "WASD fly   SPACE up   C down   SHIFT boost\n"
    "MOUSE look   V camera   WHEEL zoom\n"
    "1 launch drone   2 launch heavy   ESC pause"
)


class Hud(object):
    def __init__(self, base, side):
        white = (1, 1, 1, 1)
        shadow = (0, 0, 0, 1)

        self.crosshair = OnscreenText(
            text="+", pos=(0, -0.03), scale=0.09,
            fg=(1, 1, 1, 0.9), shadow=shadow, mayChange=False,
        )
        self.core_label = OnscreenText(
            text="BASE INTEGRITY", parent=base.a2dTopCenter,
            pos=(0, -0.08), scale=0.04, fg=white, shadow=shadow,
            mayChange=False,
        )
        self.core_bar = Bar(
            base.a2dTopCenter, (-0.45, -0.14), 0.9, 0.035, (0.2, 0.85, 0.4, 1)
        )
        self.info = OnscreenText(
            text="", parent=base.a2dTopLeft, pos=(0.05, -0.08),
            scale=0.05, align=TextNode.ALeft, fg=white, shadow=shadow,
            mayChange=True,
        )
        self.help = OnscreenText(
            text=HELP_DEFENDER if side == "defender" else HELP_ATTACKER,
            parent=base.a2dBottomLeft, pos=(0.05, 0.16), scale=0.038,
            align=TextNode.ALeft, fg=(1, 1, 1, 0.8), shadow=shadow,
            mayChange=False,
        )
        self.status = OnscreenText(
            text="", parent=base.a2dBottomRight, pos=(-0.05, 0.08),
            scale=0.06, align=TextNode.ARight, fg=white, shadow=shadow,
            mayChange=True,
        )
        self.hp_label = OnscreenText(
            text="DRONE HULL", parent=base.a2dBottomCenter,
            pos=(0, 0.11), scale=0.035, fg=white, shadow=shadow,
            mayChange=False,
        )
        self.hp_bar = Bar(
            base.a2dBottomCenter, (-0.25, 0.05), 0.5, 0.03, (0.9, 0.3, 0.2, 1)
        )
        self.message = OnscreenText(
            text="", pos=(0, 0.55), scale=0.09, fg=(1, 0.9, 0.4, 1),
            shadow=shadow, mayChange=True,
        )
        self.message_time = 0.0

        if side == "defender":
            self.hp_label.hide()
            self.hp_bar.hide()

        self.last_info = None
        self.last_status = None

    def set_integrity(self, fraction):
        self.core_bar.set(fraction)

    def set_hp(self, fraction):
        if fraction is None:
            self.hp_bar.set(0.0)
        else:
            self.hp_bar.set(fraction)

    def set_info(self, text):
        if text != self.last_info:
            self.last_info = text
            self.info.setText(text)

    def set_status(self, text):
        if text != self.last_status:
            self.last_status = text
            self.status.setText(text)

    def show_message(self, text, seconds=2.5):
        self.message.setText(text)
        self.message_time = seconds

    def update(self, dt):
        if self.message_time > 0.0:
            self.message_time -= dt
            if self.message_time <= 0.0:
                self.message.setText("")

    def destroy(self):
        for widget in (
            self.crosshair, self.core_label, self.info, self.help,
            self.status, self.hp_label, self.message,
        ):
            widget.destroy()
        self.core_bar.destroy()
        self.hp_bar.destroy()
