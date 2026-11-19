import math

from panda3d.core import loadPrcFileData, ClockObject, TextNode
from direct.showbase.ShowBase import ShowBase
from direct.gui.DirectGui import DirectButton, DirectFrame, DGG
from direct.gui.OnscreenText import OnscreenText

from settings import (
    GAME_TITLE,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    CAMERA_FOV,
    CAMERA_NEAR,
    CAMERA_FAR,
)

# Настройки Panda3D нужно задать до создания ShowBase
loadPrcFileData("", "window-title " + GAME_TITLE)
loadPrcFileData("", "win-size {} {}".format(WINDOW_WIDTH, WINDOW_HEIGHT))
loadPrcFileData("", "framebuffer-multisample 0")
loadPrcFileData("", "sync-video true")

from game.controls import Controls          # noqa: E402
from game.mobile_ui import MobileControlsUI # noqa: E402
from game.maps import MAPS                  # noqa: E402
from game.session import DefenderSession, AttackerSession   # noqa: E402
from game.world import World                # noqa: E402

SIDE_INFO = {
    "defender": (
        "DEFENDER",
        "Shoot incoming drones with your rifle.\n"
        "Survive 5 waves and protect the base core.",
    ),
    "attacker": (
        "DRONE OPERATOR",
        "Pilot a drone and launch more. Avoid base turrets.\n"
        "Bring the base integrity to zero with 12 drones.",
    ),
}


class SkyfrontGame(ShowBase):

    def __init__(self):
        ShowBase.__init__(self)

        self.disableMouse()
        self.clock = ClockObject.getGlobalClock()

        self.camLens.setFov(CAMERA_FOV)
        self.camLens.setNearFar(CAMERA_NEAR, CAMERA_FAR)

        self.controls = Controls(
            self, on_escape=self.on_escape, on_focus_lost=self.on_escape
        )

        self.map_index = 0
        self.side = "defender"
        self.device_mode = "pc"
        self.mobile_ui = None
        self.state = "menu"

        self.ui = []
        self.session = None
        self.preview_root = None
        self.preview_world = None
        self.preview_angle = 0.0

        self.show_main_menu()
        self.taskMgr.add(self.update_game, "update_game")

    # ------------------------------------------------------------------
    # Помощники интерфейса
    def clear_ui(self):
        for widget in self.ui:
            widget.destroy()
        self.ui = []

    def add_text(self, text, pos, scale=0.06, align=TextNode.ACenter,
                 fg=(1, 1, 1, 1), wordwrap=None):
        widget = OnscreenText(
            text=text, pos=pos, scale=scale, align=align, fg=fg,
            shadow=(0, 0, 0, 1), wordwrap=wordwrap, mayChange=False,
        )
        self.ui.append(widget)
        return widget

    def add_button(self, text, pos, command, width=0.9, selected=False,
                   scale=0.055):
        normal = (0.15, 0.45, 0.75, 1) if selected else (0.12, 0.16, 0.22, 0.92)
        widget = DirectButton(
            text=text,
            text_scale=scale,
            text_fg=(1, 1, 1, 1),
            text_pos=(0, -scale * 0.3),
            frameSize=(-width / 2.0, width / 2.0, -0.055, 0.075),
            frameColor=(
                normal,
                (0.25, 0.60, 0.90, 1),
                (0.20, 0.50, 0.80, 1),
                (0.30, 0.30, 0.30, 1),
            ),
            relief=DGG.FLAT,
            pos=(pos[0], 0, pos[1]),
            command=command,
            rolloverSound=None,
            clickSound=None,
        )
        self.ui.append(widget)
        return widget

    def add_overlay(self):
        frame = DirectFrame(
            frameColor=(0, 0, 0, 0.6),
            frameSize=(-3, 3, -1, 1),
            relief=DGG.FLAT,
        )
        self.ui.append(frame)

    # ------------------------------------------------------------------
    # Превью карты на заднем плане меню
    def sky_color(self):
        sky = MAPS[self.map_index]["palette"]["sky"]
        self.setBackgroundColor(sky[0], sky[1], sky[2], 1)

    def build_preview(self):
        self.destroy_preview()
        self.sky_color()
        self.preview_root = self.render.attachNewNode("preview")
        self.preview_world = World(
            self, self.preview_root, MAPS[self.map_index]
        )

    def destroy_preview(self):
        if self.preview_root is not None:
            self.preview_root.removeNode()
            self.preview_root = None
            self.preview_world = None

    def update_preview(self, dt):
        if self.preview_world is None:
            return
        self.preview_angle = (self.preview_angle + 6.0 * dt) % 360.0
        a = math.radians(self.preview_angle)
        self.camera.setPos(math.cos(a) * 130.0, math.sin(a) * 130.0, 35.0)
        self.camera.lookAt(0, 0, 6)
        self.preview_world.update(dt)

    # ------------------------------------------------------------------
    # Экраны
    def show_main_menu(self):
        self.state = "menu"
        self.controls.enabled = False
        self.clear_ui()
        self.destroy_session()
        if self.preview_world is None:
            self.build_preview()

        self.add_text("SKYFRONT", (0, 0.55), scale=0.22)
        self.add_text("DRONE DEFENSE", (0, 0.42), scale=0.07,
                      fg=(0.6, 0.85, 1, 1))
        self.add_text("DEVICE: " + ("PHONE / TOUCH" if self.device_mode == "mobile" else "PC / KEYBOARD + MOUSE"),
                      (0, 0.23), scale=0.045, fg=(0.65, 0.9, 1, 1))
        self.add_button("CHANGE DEVICE: " + ("PHONE" if self.device_mode == "pc" else "PC"),
                        (0, 0.02), self.toggle_device, width=1.15, scale=0.045)
        self.add_button("PLAY", (0, -0.16), self.show_select)
        self.add_button("QUIT", (0, -0.36), self.userExit)

    def toggle_device(self):
        self.device_mode = "mobile" if self.device_mode == "pc" else "pc"
        self.controls.set_device_mode(self.device_mode)
        self.show_main_menu()

    def show_select(self):
        self.state = "select"
        self.controls.enabled = False
        self.clear_ui()

        self.add_text("SELECT SIDE", (0, 0.82), scale=0.07)
        self.add_button(
            SIDE_INFO["defender"][0], (-0.55, 0.68),
            lambda: self.set_side("defender"), width=1.0,
            selected=(self.side == "defender"),
        )
        self.add_button(
            SIDE_INFO["attacker"][0], (0.55, 0.68),
            lambda: self.set_side("attacker"), width=1.0,
            selected=(self.side == "attacker"),
        )
        self.add_text(SIDE_INFO[self.side][1], (0, 0.52), scale=0.045,
                      wordwrap=40)

        self.add_text("SELECT MAP", (0, 0.28), scale=0.07)
        for index, map_def in enumerate(MAPS):
            self.add_button(
                map_def["name"], (-0.75 + index * 0.75, 0.14),
                lambda i=index: self.set_map(i), width=0.7, scale=0.045,
                selected=(index == self.map_index),
            )
        self.add_text(MAPS[self.map_index]["desc"], (0, 0.0), scale=0.045,
                      wordwrap=40)

        self.add_button("START", (0, -0.25), self.start_game, width=0.8)
        self.add_button("BACK", (0, -0.45), self.show_main_menu, width=0.8)

    def set_side(self, side):
        self.side = side
        self.show_select()

    def set_map(self, index):
        self.map_index = index
        self.build_preview()
        self.show_select()

    # ------------------------------------------------------------------
    # Игра
    def destroy_session(self):
        if self.session is not None:
            self.session.destroy()
            self.session = None

    def start_game(self):
        self.destroy_mobile_ui()
        self.clear_ui()
        self.destroy_preview()
        self.destroy_session()
        self.sky_color()

        map_def = MAPS[self.map_index]
        if self.side == "defender":
            self.session = DefenderSession(self, self.controls, map_def)
        else:
            self.session = AttackerSession(self, self.controls, map_def)

        self.controls.set_device_mode(self.device_mode)
        self.controls.enabled = True
        if self.device_mode == "pc":
            self.controls.capture_mouse()
        else:
            self.controls.release_mouse()
            self.mobile_ui = MobileControlsUI(self, self.controls, self.side)
        self.state = "play"

    def on_escape(self):
        """Esc или потеря фокуса окна: пауза, мышь освобождена."""
        if self.state != "play":
            return
        self.state = "pause"
        self.controls.enabled = False
        self.controls.release_mouse()
        self.destroy_mobile_ui()
        if self.session is not None:
            self.session.audio.stop_hum()

        self.clear_ui()
        self.add_overlay()
        self.add_text("PAUSED", (0, 0.4), scale=0.14)
        self.add_button("RESUME", (0, 0.1), self.resume_game)
        self.add_button("MAIN MENU", (0, -0.1), self.go_menu)

    def resume_game(self):
        self.clear_ui()
        self.state = "play"
        self.controls.enabled = True
        if self.device_mode == "pc":
            self.controls.capture_mouse()
        else:
            self.mobile_ui = MobileControlsUI(self, self.controls, self.side)
        if self.session is not None and getattr(self.session, "pilot", None) is not None:
            self.session.audio.start_hum()

    def destroy_mobile_ui(self):
        if self.mobile_ui is not None:
            self.mobile_ui.destroy()
            self.mobile_ui = None

    def go_menu(self):
        self.controls.enabled = False
        self.controls.release_mouse()
        self.destroy_mobile_ui()
        self.clear_ui()
        self.destroy_session()
        self.build_preview()
        self.show_main_menu()

    def show_game_over(self):
        self.state = "over"
        self.controls.enabled = False
        self.controls.release_mouse()
        self.destroy_mobile_ui()

        won = self.session.result == "win"
        self.clear_ui()
        self.add_overlay()
        self.add_text(
            "VICTORY" if won else "DEFEAT", (0, 0.55), scale=0.18,
            fg=(0.4, 1, 0.5, 1) if won else (1, 0.4, 0.4, 1),
        )
        y = 0.35
        for line in self.session.summary():
            self.add_text(line, (0, y), scale=0.055)
            y -= 0.09
        self.add_button("PLAY AGAIN", (0, -0.15), self.start_game)
        self.add_button("MAIN MENU", (0, -0.35), self.go_menu)

    # ------------------------------------------------------------------
    def update_game(self, task):
        dt = min(self.clock.getDt(), 0.05)

        if self.state in ("menu", "select"):
            self.update_preview(dt)
        elif self.state == "play" and self.session is not None:
            self.session.update(dt)
            if self.session.finished:
                self.show_game_over()

        return task.cont


if __name__ == "__main__":
    game = SkyfrontGame()
    game.run()
