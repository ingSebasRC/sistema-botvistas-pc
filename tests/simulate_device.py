"""Simulated Android Client to test WebSocket communication with the PC server."""

import asyncio
import json
import random
import sys


async def simulate_android_client(device_id: str = "DEV-TEST-001", name: str = "Samsung Galaxy S23 (Test)"):
    import websockets

    uri = f"ws://127.0.0.1:8000/ws/{device_id}"
    print(f"Connecting to PC server at {uri}...")

    try:
        async with websockets.connect(uri) as ws:
            print(f"Connected as {name} ({device_id})!")

            # 1. Send Registration
            register_msg = {
                "type": "REGISTER",
                "device_id": device_id,
                "payload": {
                    "name": name,
                    "ip_address": "192.168.1.55",
                    "battery_level": 85,
                    "app_version": "1.0.0-apk"
                }
            }
            await ws.send(json.dumps(register_msg))
            print(f"Sent registration: {register_msg}")

            # 2. Background Heartbeat task
            async def heartbeat_loop():
                battery = 85
                while True:
                    await asyncio.sleep(10)
                    battery = max(10, battery - 1)
                    hb = {
                        "type": "HEARTBEAT",
                        "device_id": device_id,
                        "payload": {"battery_level": battery}
                    }
                    await ws.send(json.dumps(hb))
                    print(f"[{device_id}] Sent heartbeat (Battery: {battery}%)")

            asyncio.create_task(heartbeat_loop())

            # 3. Listen for commands from PC
            while True:
                raw = await ws.recv()
                msg = json.loads(raw)
                msg_type = msg.get("type")
                print(f"[{device_id}] Received from server: {msg_type}")

                if msg_type == "TASK_START":
                    task_id = msg.get("task_id")
                    payload = msg.get("payload", {})
                    platform = payload.get("platform")
                    profile = payload.get("target_profile")
                    duration = payload.get("duration_per_video_seconds")
                    print(f"[{device_id}] STARTING TASK: Platform={platform}, Profile={profile}, Duration={duration}s")

                    # Send status update: Running
                    await ws.send(json.dumps({
                        "type": "TASK_STATUS",
                        "device_id": device_id,
                        "payload": {"status": "running", "task_id": task_id}
                    }))

                    # Simulate video navigation logs
                    await asyncio.sleep(1)
                    await ws.send(json.dumps({
                        "type": "LOG",
                        "device_id": device_id,
                        "payload": {"message": f"Opening {platform.title()} and searching for '{profile}'..."}
                    }))

                elif msg_type == "TASK_STOP":
                    task_id = msg.get("task_id")
                    print(f"[{device_id}] STOPPING TASK {task_id}")
                    await ws.send(json.dumps({
                        "type": "TASK_STATUS",
                        "device_id": device_id,
                        "payload": {"status": "stopped", "task_id": task_id}
                    }))
                    await ws.send(json.dumps({
                        "type": "LOG",
                        "device_id": device_id,
                        "payload": {"message": "Automation stopped by PC operator."}
                    }))

    except Exception as e:
        print(f"Connection error or closed: {e}")


if __name__ == "__main__":
    dev_id = sys.argv[1] if len(sys.argv) > 1 else f"DEV-{random.randint(100, 999)}"
    dev_name = sys.argv[2] if len(sys.argv) > 2 else f"Android Phone ({dev_id})"
    asyncio.run(simulate_android_client(dev_id, dev_name))
