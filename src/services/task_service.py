"""Task scheduling and dispatching service."""

import asyncio
import threading
from dataclasses import dataclass
from typing import Dict, List, Optional, Union
from src.core.events import event_bridge
from src.core.logger import logger
from src.models.device import DeviceStatus
from src.models.task import Platform, TaskConfig, TaskStatus
from src.services.device_service import device_service
from adb_manager import AdbError, adb_manager


@dataclass(frozen=True)
class YouTubeCoordinates:
    """Validated portrait 1080x2400 coordinate profile; tune per device family."""
    search: tuple[int, int] = (1000, 145)
    first_channel_result: tuple[int, int] = (320, 560)
    videos_tab: tuple[int, int] = (430, 430)
    first_video: tuple[int, int] = (320, 720)


YOUTUBE_COORDINATES = YouTubeCoordinates()


class TaskService:
    """Manages automation tasks and commands dispatched to Android devices."""

    def __init__(self):
        self._tasks: Dict[str, TaskConfig] = {}
        self._cancel_events: Dict[str, threading.Event] = {}

    async def start_task(
        self,
        device_ids: List[str],
        platform: Union[Platform, str],
        target_profile: str,
        duration_per_video: int
    ) -> Dict[str, bool]:
        """
        Dispatch a start task command to the specified device(s).
        Returns a mapping of device_id to success boolean.
        """
        results = {}

        for device_id in device_ids:
            device = device_service.get_device(device_id)
            if not device or device.status not in (DeviceStatus.CONNECTED, DeviceStatus.IDLE):
                logger.warning(f"No se puede iniciar la tarea: {device_id} no está Disponible/Conectado.")
                results[device_id] = False
                continue

            task = TaskConfig(
                platform=platform,
                target_profile=target_profile,
                duration_per_video_seconds=duration_per_video,
                status=TaskStatus.RUNNING
            )
            self._tasks[task.task_id] = task

            # TaskConfig normalises the UI's platform string to Platform.
            if task.platform != Platform.YOUTUBE:
                task.status = TaskStatus.ERROR
                task.error_message = "La automatización USB actual solo implementa YouTube."
                results[device_id] = False
                continue
            cancel_event = threading.Event()
            self._cancel_events[task.task_id] = cancel_event
            device_service.update_status(device_id, DeviceStatus.RUNNING, task_id=task.task_id)
            asyncio.create_task(self._run_youtube_task(task, device_id, cancel_event))
            logger.info(f"Tarea ADB iniciada en {device_id} para {target_profile}.")
            results[device_id] = True

        return results

    async def stop_task(self, device_ids: List[str]) -> Dict[str, bool]:
        """
        Dispatch a stop task command to the specified device(s).
        Returns a mapping of device_id to success boolean.
        """
        results = {}

        for device_id in device_ids:
            device = device_service.get_device(device_id)
            if not device or device.status == DeviceStatus.DISCONNECTED:
                results[device_id] = False
                continue

            task_id = device.current_task_id
            cancel_event = self._cancel_events.get(task_id or "")
            if cancel_event:
                cancel_event.set()
            device_service.clear_current_task(device_id)
            device_service.update_status(device_id, DeviceStatus.STOPPED)
            logger.info(f"Detenida tarea USB en {device.name} ({device_id})")
            results[device_id] = True

        return results

    def get_task(self, task_id: str) -> Optional[TaskConfig]:
        """Retrieve task by ID."""
        return self._tasks.get(task_id)

    async def _run_youtube_task(self, task: TaskConfig, device_id: str, cancel_event: threading.Event) -> None:
        try:
            await asyncio.to_thread(self._navigate_youtube, task, device_id, cancel_event)
            if cancel_event.is_set():
                task.status = TaskStatus.STOPPED
                device_service.clear_current_task(device_id)
                device_service.update_status(device_id, DeviceStatus.STOPPED)
            else:
                task.status = TaskStatus.COMPLETED
                device_service.clear_current_task(device_id)
                device_service.update_status(device_id, DeviceStatus.CONNECTED)
        except (AdbError, ValueError) as exc:
            task.status = TaskStatus.ERROR
            task.error_message = str(exc)
            device_service.update_status(device_id, DeviceStatus.ERROR, task_id=task.task_id)
            logger.error(f"Tarea USB [{task.task_id}] falló en {device_id}: {exc}")
        finally:
            self._cancel_events.pop(task.task_id, None)

    @staticmethod
    def _pause(seconds: float, cancel_event: threading.Event) -> bool:
        return cancel_event.wait(seconds)

    def _navigate_youtube(self, task: TaskConfig, device_id: str, cancel_event: threading.Event) -> None:
        """Search -> channel -> Videos -> first regular video. Never taps Shorts."""
        c = YOUTUBE_COORDINATES
        adb_manager.open_youtube(device_id)
        if self._pause(2.5, cancel_event): return
        adb_manager.tap(device_id, *c.search)
        if self._pause(0.8, cancel_event): return
        adb_manager.input_text(device_id, task.target_profile)
        adb_manager.press_enter(device_id)
        if self._pause(3.0, cancel_event): return
        adb_manager.tap(device_id, *c.first_channel_result)
        if self._pause(2.5, cancel_event): return
        # Explicit Videos coordinate is to the left of the Shorts tab in this profile.
        adb_manager.tap(device_id, *c.videos_tab)
        if self._pause(1.8, cancel_event): return
        adb_manager.tap(device_id, *c.first_video)
        if self._pause(task.duration_per_video_seconds, cancel_event): return


task_service = TaskService()
