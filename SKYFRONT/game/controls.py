import math

from direct.showbase.DirectObject import DirectObject
from panda3d.core import KeyboardButton, MouseButton, Vec3, WindowProperties

from settings import (
    CAMERA_DISTANCE,
    CAMERA_MIN_DISTANCE,
    CAMERA_MAX_DISTANCE,
    MOUSE_SENSITIVITY,
    MOUSE_MAX_DELTA,
    LOOK_MIN_PITCH,
    LOOK_MAX_PITCH,
    PLAYER_ROTATION_SPEED,
)

# Соглашение Panda3D: heading растёт против часовой стрелки,
# вперёд = (-sin H, cos H), вправо = (cos H, sin H), pitch вверх = плюс.


def clamp(value, low, high):
    return max(low, min(high, value))


class Controls(DirectObject):
    """Клавиатура, мышь и положение камеры. Общие для обеих сторон."""

    def __init__(self, base, on_escape=None, on_focus_lost=None):
        DirectObject.__init__(self)

        self.base = base
        self.on_escape = on_escape
        self.on_focus_lost = on_focus_lost

        self.enabled = False
        self.mouse_active = False
        self.skip_mouse_frame = False
        self.fire_block = False

        self.heading = 0.0
        self.pitch = 0.0
        self.camera_mode = 3
        self.distance = CAMERA_DISTANCE
        self.sensitivity = MOUSE_SENSITIVITY

        self.pending = set()
        self._buttons = {}
        self.device_mode = "pc"
        self.touch_down = set()

        self.accept("v", self.toggle_camera)
        self.accept("r", self.push, ["reload"])
        self.accept("1", self.push, ["launch1"])
        self.accept("2", self.push, ["launch2"])
        self.accept("escape", self.on_esc)
        self.accept("mouse1", self.on_click)
        self.accept("wheel_up", self.zoom, [-1.0])
        self.accept("wheel_down", self.zoom, [1.0])
        self.accept("window-event", self.on_window_event)

    # ------------------------------------------------------------------
    # Опрос клавиш (работает и при зажатом Shift)
    def _button(self, name):
        button = self._buttons.get(name)
        if button is None:
            if name == "space":
                button = KeyboardButton.space()
            elif name == "shift":
                button = KeyboardButton.shift()
            elif name == "mouse1":
                button = MouseButton.one()
            else:
                try:
                    button = KeyboardButton.asciiKey(name)
                except TypeError:
                    button = KeyboardButton.asciiKey(name.encode("ascii"))
            self._buttons[name] = button
        return button

    def is_down(self, name):
        if self.device_mode == "mobile" and name in (
                "turn_left", "turn_right", "look_up", "look_down",
                "fire", "w", "a", "s", "d", "space", "c", "shift"):
            return name in self.touch_down
        watcher = self.base.mouseWatcherNode
        if watcher is None:
            return False
        return watcher.isButtonDown(self._button(name))

    def set_device_mode(self, mode):
        self.device_mode = "mobile" if mode == "mobile" else "pc"
        self.touch_down.clear()
        if self.device_mode == "mobile":
            self.release_mouse()

    def set_touch(self, name, pressed):
        if not self.enabled or self.device_mode != "mobile":
            return
        if pressed:
            self.touch_down.add(name)
        else:
            self.touch_down.discard(name)

    def move_axes(self):
        forward = int(self.is_down("w")) - int(self.is_down("s"))
        sideways = int(self.is_down("d")) - int(self.is_down("a"))
        return forward, sideways

    def fire_down(self):
        if self.device_mode == "mobile":
            return self.enabled and "fire" in self.touch_down
        return (self.mouse_active and not self.fire_block
                and self.is_down("mouse1"))

    # ------------------------------------------------------------------
    # События
    def push(self, name):
        if self.enabled:
            self.pending.add(name)

    def take(self, name):
        if name in self.pending:
            self.pending.discard(name)
            return True
        return False

    def toggle_camera(self):
        if not self.enabled:
            return
        self.camera_mode = 1 if self.camera_mode == 3 else 3

    def zoom(self, direction):
        if self.enabled and self.camera_mode == 3:
            self.distance = clamp(
                self.distance + direction,
                CAMERA_MIN_DISTANCE,
                CAMERA_MAX_DISTANCE,
            )

    def on_esc(self):
        if not self.enabled:
            return
        self.release_mouse()
        if self.on_escape:
            self.on_escape()

    def on_click(self):
        if (self.enabled and self.device_mode == "pc"
                and not self.mouse_active):
            self.capture_mouse()

    def on_window_event(self, window=None):
        win = self.base.win
        if not win or not self.enabled:
            return
        props = win.getProperties()
        if not props.getForeground() or props.getMinimized():
            self.release_mouse()
            if self.on_focus_lost:
                self.on_focus_lost()

    # ------------------------------------------------------------------
    # Мышь
    def capture_mouse(self):
        win = self.base.win
        if not win:
            return

        self.mouse_active = True
        self.fire_block = True
        self.skip_mouse_frame = True

        props = WindowProperties()
        props.setCursorHidden(True)
        props.setMouseMode(WindowProperties.M_confined)
        win.requestProperties(props)

        self.center_mouse()

    def release_mouse(self):
        self.mouse_active = False

        win = self.base.win
        if not win:
            return

        props = WindowProperties()
        props.setCursorHidden(False)
        props.setMouseMode(WindowProperties.M_absolute)
        win.requestProperties(props)

    def center_mouse(self):
        win = self.base.win
        if win:
            win.movePointer(0, win.getXSize() // 2, win.getYSize() // 2)

    def reset_view(self, heading, pitch):
        self.heading = heading % 360.0
        self.pitch = clamp(pitch, LOOK_MIN_PITCH, LOOK_MAX_PITCH)
        self.camera_mode = 3
        self.distance = CAMERA_DISTANCE
        self.pending.clear()
        self.touch_down.clear()

    def update(self, dt):
        if not self.enabled:
            return

        if self.fire_block and not self.is_down("mouse1"):
            self.fire_block = False

        if self.is_down("q") or self.is_down("turn_left"):
            self.heading = (
                self.heading + PLAYER_ROTATION_SPEED * dt
            ) % 360.0
        if self.is_down("e") or self.is_down("turn_right"):
            self.heading = (
                self.heading - PLAYER_ROTATION_SPEED * dt
            ) % 360.0
        if self.is_down("look_up"):
            self.pitch = clamp(self.pitch + 65.0 * dt, LOOK_MIN_PITCH, LOOK_MAX_PITCH)
        if self.is_down("look_down"):
            self.pitch = clamp(self.pitch - 65.0 * dt, LOOK_MIN_PITCH, LOOK_MAX_PITCH)

        self.update_mouse()

    def update_mouse(self):
        win = self.base.win
        if not self.mouse_active or not win:
            return

        if self.skip_mouse_frame:
            self.skip_mouse_frame = False
            self.center_mouse()
            return

        pointer = win.getPointer(0)
        dx = pointer.getX() - win.getXSize() // 2
        dy = pointer.getY() - win.getYSize() // 2

        if dx == 0 and dy == 0:
            return

        dx = clamp(dx, -MOUSE_MAX_DELTA, MOUSE_MAX_DELTA)
        dy = clamp(dy, -MOUSE_MAX_DELTA, MOUSE_MAX_DELTA)

        # мышь вправо - поворот вправо; мышь вверх - взгляд вверх
        self.heading = (self.heading - dx * self.sensitivity) % 360.0
        self.pitch = clamp(
            self.pitch - dy * self.sensitivity,
            LOOK_MIN_PITCH,
            LOOK_MAX_PITCH,
        )

        self.center_mouse()

    # ------------------------------------------------------------------
    # Камера
    def view_direction(self):
        h = math.radians(self.heading)
        p = math.radians(self.pitch)
        return Vec3(
            -math.sin(h) * math.cos(p),
            math.cos(h) * math.cos(p),
            math.sin(p),
        )

    def update_camera(self, pivot, eye, shoulder=0.0):
        """Ставит камеру. Возвращает (позиция камеры, направление взгляда)."""
        direction = self.view_direction()

        if self.camera_mode == 1:
            position = Vec3(eye)
        else:
            h = math.radians(self.heading)
            right = Vec3(math.cos(h), math.sin(h), 0)
            position = Vec3(pivot) + right * shoulder - direction * self.distance
            if position.z < 0.4:
                position.z = 0.4     # камера не уходит под землю

        camera = self.base.camera
        camera.setPos(position)
        camera.setHpr(self.heading, self.pitch, 0)
        return position, direction

    def destroy(self):
        self.ignoreAll()
