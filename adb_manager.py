"""Small, safe wrapper around the local Android Debug Bridge executable.

Every command is addressed to one USB serial explicitly.  This is important in a
multi-phone setup: ADB's implicit target selection becomes ambiguous as soon as
two devices are connected.
"""

from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import tempfile
import threading
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


class AdbError(RuntimeError):
    """Raised when ADB cannot execute a command successfully."""


@dataclass(frozen=True)
class AdbDevice:
    serial: str
    state: str
    model: str = "Android USB"
    battery_level: int | None = None


class AdbManager:
    """Execute USB-only ADB operations without invoking a shell on the PC."""

    _install_lock = threading.Lock()
    _download_urls = {
        "Windows": "https://dl.google.com/android/repository/platform-tools-latest-windows.zip",
        "Linux": "https://dl.google.com/android/repository/platform-tools-latest-linux.zip",
        "Darwin": "https://dl.google.com/android/repository/platform-tools-latest-darwin.zip",
    }

    def __init__(self, adb_path: str | None = None, timeout: float = 15.0):
        self.adb_path = adb_path or os.environ.get("ADB_PATH")
        self.timeout = timeout

    @property
    def _binary_name(self) -> str:
        return "adb.exe" if os.name == "nt" else "adb"

    @property
    def _bundled_adb(self) -> Path:
        return Path(__file__).resolve().parent / "tools" / "platform-tools" / self._binary_name

    def ensure_adb(self) -> str:
        """Resolve ADB or install official platform-tools into this project once."""
        if self.adb_path and Path(self.adb_path).is_file():
            return self.adb_path
        for candidate in (
            shutil.which("adb"),
            os.path.join(os.environ.get("ANDROID_SDK_ROOT", ""), "platform-tools", self._binary_name),
            os.path.join(os.environ.get("ANDROID_HOME", ""), "platform-tools", self._binary_name),
            str(self._bundled_adb),
        ):
            if candidate and Path(candidate).is_file():
                self.adb_path = candidate
                return candidate

        with self._install_lock:
            if self._bundled_adb.is_file():
                self.adb_path = str(self._bundled_adb)
                return self.adb_path
            system = platform.system()
            url = self._download_urls.get(system)
            if not url:
                raise AdbError(f"No existe descarga automática de platform-tools para {system}.")
            target = self._bundled_adb.parent
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as archive:
                    archive_path = Path(archive.name)
                    with urllib.request.urlopen(url, timeout=60) as response:
                        shutil.copyfileobj(response, archive)
                with zipfile.ZipFile(archive_path) as package:
                    for member in package.infolist():
                        # Official archive is expected to contain platform-tools/.
                        member_path = Path(member.filename)
                        if member_path.is_absolute() or ".." in member_path.parts:
                            raise AdbError("El archivo platform-tools contiene una ruta insegura.")
                    package.extractall(target.parent)
            except (OSError, urllib.error.URLError, zipfile.BadZipFile) as exc:
                raise AdbError(
                    "No se pudo instalar platform-tools automáticamente. "
                    "Comprueba la conexión o define ADB_PATH."
                ) from exc
            finally:
                if "archive_path" in locals():
                    archive_path.unlink(missing_ok=True)
            if not self._bundled_adb.is_file():
                raise AdbError("La descarga de platform-tools no incluyó el ejecutable ADB esperado.")
            if os.name != "nt":
                self._bundled_adb.chmod(self._bundled_adb.stat().st_mode | 0o111)
            self.adb_path = str(self._bundled_adb)
            return self.adb_path

    def _run(self, args: Iterable[str], timeout: float | None = None) -> str:
        command = [self.ensure_adb(), *args]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout or self.timeout,
                check=False,
            )
        except FileNotFoundError as exc:
            raise AdbError("ADB no está disponible. Instala platform-tools o define ADB_PATH.") from exc
        except subprocess.TimeoutExpired as exc:
            raise AdbError(f"ADB agotó el tiempo de espera: {' '.join(command)}") from exc
        if result.returncode:
            detail = (result.stderr or result.stdout).strip()
            raise AdbError(detail or f"ADB finalizó con código {result.returncode}")
        return result.stdout.strip()

    def devices(self) -> list[AdbDevice]:
        """Return physical USB devices reported by ``adb devices -l``.

        Unauthorized/offline devices are returned too so the control panel can
        show why they cannot receive a task.
        """
        self._run(["start-server"], timeout=30)
        output = self._run(["devices", "-l"])
        devices: list[AdbDevice] = []
        for line in output.splitlines():
            if not line or line.startswith("List of devices") or line.startswith("*"):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            serial, state = parts[0], parts[1]
            model_match = re.search(r"model:([^\s]+)", line)
            model = (model_match.group(1).replace("_", " ") if model_match else "Android USB")
            battery = self.battery_level(serial) if state == "device" else None
            devices.append(AdbDevice(serial=serial, state=state, model=model, battery_level=battery))
        return devices

    def battery_level(self, serial: str) -> int | None:
        try:
            output = self.shell(serial, "dumpsys", "battery")
        except AdbError:
            return None
        match = re.search(r"^\s*level:\s*(\d+)", output, re.MULTILINE)
        return int(match.group(1)) if match else None

    def shell(self, serial: str, *args: str) -> str:
        return self._run(["-s", serial, "shell", *args])

    def open_youtube(self, serial: str) -> None:
        self.shell(serial, "am", "start", "-n", "com.google.android.youtube/com.google.android.apps.youtube.app.watchwhile.WatchWhileActivity")

    def tap(self, serial: str, x: int, y: int) -> None:
        if x < 0 or y < 0:
            raise ValueError("Las coordenadas ADB no pueden ser negativas")
        self.shell(serial, "input", "tap", str(x), str(y))

    def press_enter(self, serial: str) -> None:
        self.shell(serial, "input", "keyevent", "66")

    def input_text(self, serial: str, value: str) -> None:
        if not value.strip():
            raise ValueError("El texto a escribir no puede estar vacío")
        # Android's input command expects %s for whitespace. Avoid a PC shell so
        # quotes or punctuation in a channel name are never interpreted locally.
        escaped = value.replace(" ", "%s").replace("&", "\\&").replace("<", "\\<").replace(">", "\\>")
        self.shell(serial, "input", "text", escaped)


adb_manager = AdbManager()
