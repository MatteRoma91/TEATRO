"""Riproduzione tracce audio (mp3/wav/...)."""

from __future__ import annotations

from pathlib import Path

import numpy as np

try:
    import soundfile as sf
except ImportError:
    sf = None

import pygame


class MusicPlayer:
    def __init__(self) -> None:
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
        self._path: Path | None = None
        self._duration = 0.0
        self._t0 = 0.0
        self._offset = 0.0
        self._paused_at: float | None = None

    @property
    def duration(self) -> float:
        return self._duration

    def load(self, path: Path) -> bool:
        self.stop()
        if not path.is_file():
            return False
        try:
            if path.suffix.lower() == ".mp3":
                pygame.mixer.music.load(str(path))
                if sf:
                    with sf.SoundFile(str(path)) as f:
                        self._duration = len(f) / float(f.samplerate)
                else:
                    self._duration = 0.0
            else:
                if sf is None:
                    pygame.mixer.music.load(str(path))
                    self._duration = 0.0
                else:
                    data, rate = sf.read(str(path), dtype="float32")
                    if data.ndim == 1:
                        data = np.column_stack([data, data])
                    pcm = (np.clip(data, -1, 1) * 32767).astype(np.int16)
                    sound = pygame.sndarray.make_sound(pcm)
                    self._sound = sound
                    self._duration = len(data) / rate
                    self._use_sound = True
                    self._path = path
                    return True
            self._use_sound = False
            self._path = path
            return True
        except Exception:
            return False

    def play(self) -> None:
        if self._paused_at is not None:
            self._offset = self._paused_at
            self._paused_at = None
        import time

        self._t0 = time.monotonic() - self._offset
        if getattr(self, "_use_sound", False):
            self._sound.play(start=int(self._offset * 44100))
        elif self._path:
            pygame.mixer.music.play(start=float(self._offset))

    def pause(self) -> None:
        self._paused_at = self.current_time
        pygame.mixer.music.pause()
        if getattr(self, "_use_sound", False) and hasattr(self, "_sound"):
            self._sound.stop()

    def unpause(self) -> None:
        pygame.mixer.music.unpause()

    def stop(self) -> None:
        self._offset = 0.0
        self._paused_at = None
        pygame.mixer.music.stop()
        if hasattr(self, "_sound"):
            try:
                self._sound.stop()
            except Exception:
                pass

    @property
    def current_time(self) -> float:
        if not self.is_playing() and self._paused_at is not None:
            return self._paused_at
        if not self.is_playing():
            return self._offset
        import time

        return time.monotonic() - self._t0

    def is_playing(self) -> bool:
        if getattr(self, "_use_sound", False):
            return pygame.mixer.get_busy()
        return pygame.mixer.music.get_busy()

    def seek(self, t: float) -> None:
        t = max(0.0, t)
        self._offset = t
        self._paused_at = None
        was = self.is_playing()
        if getattr(self, "_use_sound", False) and hasattr(self, "_sound"):
            self._sound.stop()
            if was:
                import time

                self._t0 = time.monotonic() - t
                self._sound.play(start=int(t * 44100))
        elif self._path:
            if was:
                import time

                self._t0 = time.monotonic() - t
                pygame.mixer.music.play(start=float(t))
