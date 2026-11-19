"""Крупные сенсорные кнопки для мобильного режима."""
from direct.gui.DirectGui import DirectButton, DGG


class MobileControlsUI(object):
    def __init__(self, base, controls, side):
        self.base = base
        self.controls = controls
        self.widgets = []
        self._hold_button("▲", -1.35, -0.60, "w")
        self._hold_button("▼", -1.35, -0.88, "s")
        self._hold_button("◀", -1.63, -0.74, "a")
        self._hold_button("▶", -1.07, -0.74, "d")

        self._hold_button("⟲", -0.55, -0.76, "turn_left")
        self._hold_button("⟳", -0.22, -0.76, "turn_right")
        self._hold_button("RUN", -0.55, -0.48, "shift", scale=0.047)
        self._hold_button("LOOK +", 0.18, -0.58, "look_up", scale=0.047)
        self._hold_button("LOOK -", 0.18, -0.86, "look_down", scale=0.047)

        if side == "defender":
            self._hold_button("FIRE", 1.25, -0.67, "fire", scale=0.065, width=0.34)
            self._tap_button("JUMP", 1.25, -0.91, lambda: controls.set_touch("space", True),
                             lambda: controls.set_touch("space", False))
            self._tap_button("RELOAD", 0.82, -0.91, lambda: controls.push("reload"))
        else:
            self._hold_button("UP", 1.25, -0.60, "space")
            self._hold_button("DOWN", 1.25, -0.88, "c")
            self._tap_button("LAUNCH 1", 0.82, -0.61, lambda: controls.push("launch1"), scale=0.045)
            self._tap_button("LAUNCH 2", 0.82, -0.88, lambda: controls.push("launch2"), scale=0.045)

        self._tap_button("CAM", 0.52, -0.76, controls.toggle_camera, scale=0.05)
        self._tap_button("PAUSE", 0.0, 0.88, base.on_escape, scale=0.05)

    def _button(self, text, x, z, scale=0.055, width=0.25):
        button = DirectButton(
            parent=self.base.aspect2d, text=text, text_scale=scale,
            text_fg=(1, 1, 1, 1), text_pos=(0, -scale * 0.30),
            frameSize=(-width / 2, width / 2, -0.105, 0.105),
            frameColor=(0.04, 0.15, 0.24, 0.78),
            relief=DGG.FLAT, pos=(x, 0, z),
            rolloverSound=None, clickSound=None,
        )
        self.widgets.append(button)
        return button

    def _hold_button(self, text, x, z, action, scale=0.055, width=0.25):
        button = self._button(text, x, z, scale, width)
        button.bind(DGG.B1PRESS, self.controls.set_touch, [action, True])
        button.bind(DGG.B1RELEASE, self.controls.set_touch, [action, False])
        return button

    def _tap_button(self, text, x, z, command, release=None, scale=0.05):
        button = self._button(text, x, z, scale, 0.31)
        if release is None:
            button["command"] = command
        else:
            button.bind(DGG.B1PRESS, command)
            button.bind(DGG.B1RELEASE, release)
        return button

    def destroy(self):
        for widget in self.widgets:
            widget.destroy()
        self.widgets = []
        self.controls.touch_down.clear()
