"""Task scheduling and dispatching service."""

import asyncio
from typing import Dict, List, Optional
from src.core.events import event_bridge
from src.core.logger import logger
from src.models.device import DeviceStatus
from src.models.task import Platform, TaskConfig, TaskStatus
from src.models.ws_messages import CommandType, WSServerMessage
from src.server.ws_manager import ws_manager
from src.services.device_service import device_service


class TaskService:
    """Manages automation tasks and commands dispatched to Android devices."""

    def __init__(self):
        self._tasks: Dict[str, TaskConfig] = {}

    async def start_task(
        self,
        device_ids: List[str],
        platform: Platform,
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
            if not device or device.status == DeviceStatus.DISCONNECTED:
                logger.warning(f"Cannot start task: Device {device_id} is disconnected.")
                results[device_id] = False
                continue

            task = TaskConfig(
                platform=platform,
                target_profile=target_profile,
                duration_per_video_seconds=duration_per_video,
                status=TaskStatus.RUNNING
            )
            self._tasks[task.task_id] = task

            msg = WSServerMessage(
                type=CommandType.TASK_START,
                task_id=task.task_id,
                payload={
                    "platform": platform.value,
                    "target_profile": target_profile,
                    "duration_per_video_seconds": duration_per_video
                }
            )

            success = await ws_manager.send_to_device(device_id, msg)
            if success:
                device_service.update_status(device_id, DeviceStatus.RUNNING, task_id=task.task_id)
                logger.info(
                    f"Started task [{task.task_id}] on {device.name} ({device_id}): "
                    f"{platform.value} -> '{target_profile}' ({duration_per_video}s/video)"
                )
            else:
                task.status = TaskStatus.ERROR
                task.error_message = "Failed to transmit task to device"

            results[device_id] = success

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

            msg = WSServerMessage(
                type=CommandType.TASK_STOP,
                task_id=device.current_task_id,
                payload={"reason": "Manual stop requested from PC panel"}
            )

            success = await ws_manager.send_to_device(device_id, msg)
            if success:
                device_service.update_status(device_id, DeviceStatus.STOPPED)
                logger.info(f"Stopped task on device {device.name} ({device_id})")
            results[device_id] = success

        return results

    def get_task(self, task_id: str) -> Optional[TaskConfig]:
        """Retrieve task by ID."""
        return self._tasks.get(task_id)


task_service = TaskService()
