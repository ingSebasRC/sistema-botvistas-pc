"""USB screen streaming with scrcpy and an MJPEG FastAPI response.

scrcpy writes an H.264 elementary stream to stdout in headless mode. ffmpeg
decodes it to JPEG frames, which browsers and Qt web views can display with very
little buffering through the ``mjpeg_frames`` generator.
"""

from __future__ import annotations

import os
import subprocess
import threading
from dataclasses import dataclass
from typing import Iterator


class StreamError(RuntimeError):
    pass


@dataclass
class _Pipeline:
    scrcpy: subprocess.Popen[bytes]
    ffmpeg: subprocess.Popen[bytes]


class ScrcpyStreamManager:
    boundary = "frame"

    def __init__(self, scrcpy_path: str | None = None, ffmpeg_path: str | None = None):
        self.scrcpy_path = scrcpy_path or os.environ.get("SCRCPY_PATH", "scrcpy")
        self.ffmpeg_path = ffmpeg_path or os.environ.get("FFMPEG_PATH", "ffmpeg")
        self._streams: dict[str, _Pipeline] = {}
        self._lock = threading.Lock()

    def start(self, serial: str) -> None:
        with self._lock:
            if serial in self._streams:
                return
            try:
                scrcpy = subprocess.Popen(
                    [self.scrcpy_path, "--serial", serial, "--no-window", "--raw-video-stream", "--video-bit-rate=8M", "--max-fps=60"],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                )
                ffmpeg = subprocess.Popen(
                    [self.ffmpeg_path, "-loglevel", "error", "-fflags", "nobuffer", "-flags", "low_delay", "-f", "h264", "-i", "pipe:0", "-f", "image2pipe", "-vcodec", "mjpeg", "-q:v", "5", "pipe:1"],
                    stdin=scrcpy.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                )
            except FileNotFoundError as exc:
                raise StreamError("scrcpy y ffmpeg deben estar instalados y disponibles en PATH.") from exc
            self._streams[serial] = _Pipeline(scrcpy=scrcpy, ffmpeg=ffmpeg)

    def stop(self, serial: str) -> None:
        with self._lock:
            pipeline = self._streams.pop(serial, None)
        if not pipeline:
            return
        for process in (pipeline.ffmpeg, pipeline.scrcpy):
            if process.poll() is None:
                process.terminate()
        for process in (pipeline.ffmpeg, pipeline.scrcpy):
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()

    def stop_all(self) -> None:
        for serial in list(self._streams):
            self.stop(serial)

    def mjpeg_frames(self, serial: str) -> Iterator[bytes]:
        """Yield complete JPEG images as multipart/x-mixed-replace chunks."""
        self.start(serial)
        pipeline = self._streams[serial]
        assert pipeline.ffmpeg.stdout is not None
        buffer = bytearray()
        while pipeline.ffmpeg.poll() is None:
            data = pipeline.ffmpeg.stdout.read(4096)
            if not data:
                break
            buffer.extend(data)
            while True:
                start, end = buffer.find(b"\xff\xd8"), buffer.find(b"\xff\xd9")
                if start < 0 or end < 0 or end < start:
                    if len(buffer) > 2_000_000:
                        buffer.clear()
                    break
                jpeg = bytes(buffer[start:end + 2])
                del buffer[:end + 2]
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"


stream_manager = ScrcpyStreamManager()
