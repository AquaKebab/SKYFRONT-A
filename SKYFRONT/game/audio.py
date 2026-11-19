"""Загрузка и воспроизведение локальных звуков игры."""
import os


class AudioManager(object):
    FILES = {
        "energy_pulse": "energy_pulse.wav",
        "drone_hit": "drone_hit.wav",
        "drone_pop": "drone_pop.wav",
        "base_warning": "base_warning.wav",
        "drone_hum": "drone_hum.wav",
        "reload": "reload.wav",
        "turret_pulse": "turret_pulse.wav",
    }

    def __init__(self, base):
        self.base = base
        self.sounds = {}
        self.looping = None
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.sound_dir = os.path.join(self.project_root, "assets", "sounds")

        # Включаем микшер Panda3D и поднимаем общую громкость SFX.
        try:
            base.enableSound()
        except Exception as exc:
            print("[AUDIO] enableSound failed:", exc)
        for manager in getattr(base, "sfxManagerList", []):
            try:
                manager.setVolume(1.0)
            except Exception:
                pass

        for name, filename in self.FILES.items():
            path = os.path.join(self.sound_dir, filename)
            if not os.path.isfile(path):
                print("[AUDIO] Missing sound:", path)
                continue
            try:
                sound = base.loader.loadSfx(path)
                if sound is not None:
                    sound.setVolume(1.0)
                    self.sounds[name] = sound
                    print("[AUDIO] Loaded:", filename)
                else:
                    print("[AUDIO] Panda3D could not load:", filename)
            except Exception as exc:
                print("[AUDIO] Load error for %s: %s" % (filename, exc))

    def play(self, name, volume=0.65):
        sound = self.sounds.get(name)
        if sound is None:
            return
        try:
            sound.stop()
            sound.setLoop(False)
            sound.setTime(0.0)
            sound.setVolume(max(0.0, min(1.0, volume)))
            sound.play()
        except Exception as exc:
            print("[AUDIO] Playback error for %s: %s" % (name, exc))

    def start_hum(self):
        if self.looping == "drone_hum":
            return
        self.stop_hum()
        sound = self.sounds.get("drone_hum")
        if sound is not None:
            try:
                sound.setVolume(0.20)
                sound.setLoop(True)
                sound.play()
                self.looping = "drone_hum"
            except Exception as exc:
                print("[AUDIO] Hum playback error:", exc)
                self.looping = None

    def stop_hum(self):
        if self.looping:
            sound = self.sounds.get(self.looping)
            if sound is not None:
                try:
                    sound.stop()
                except Exception:
                    pass
        self.looping = None

    def destroy(self):
        self.stop_hum()
        for sound in self.sounds.values():
            try:
                sound.stop()
            except Exception:
                pass
        self.sounds = {}
