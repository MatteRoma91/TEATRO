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
        if getattr(self, "_use_sound", False):
            self._sound.play()
        elif self._path:
            pygame.mixer.music.play()

    def pause(self) -> None:
        pygame.mixer.music.pause()

    def unpause(self) -> None:
        pygame.mixer.music.unpause()

    def stop(self) -> None:
        pygame.mixer.music.stop()
        if hasattr(self, "_sound"):
            try:
                self._sound.stop()
            except Exception:
                pass

    def is_playing(self) -> bool:
        if getattr(self, "_use_sound", False):
            return pygame.mixer.get_busy()
        return pygame.mixer.music.get_busy()
