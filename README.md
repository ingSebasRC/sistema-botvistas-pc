# BotVistas USB

El panel controla teléfonos por cable USB. ADB descubre los seriales y envía las
acciones de YouTube; scrcpy proporciona vídeo local. No hay registro Android
por Wi-Fi, WebSocket de comandos ni MediaProjection.

## Requisitos

- Python 3.10+ y las dependencias de `requirements.txt`.
- Android platform-tools: se descargan automáticamente desde Google a
  `pc/tools/platform-tools` cuando no hay ADB en `PATH`; autoriza la depuración USB en cada teléfono.
- `scrcpy` y `ffmpeg` en `PATH` para vídeo en vivo. Usa `ADB_PATH`,
  `SCRCPY_PATH` y `FFMPEG_PATH` si están instalados en otra ubicación.

## Uso

```powershell
cd pc
python main.py
adb devices -l
```

`GET /api/devices` refresca los teléfonos USB. La vista MJPEG de un equipo es
`http://127.0.0.1:8000/api/stream/<SERIAL_ADB>.mjpg`. Se inicia bajo demanda y
se detiene con `DELETE /api/stream/<SERIAL_ADB>` o al cerrar el servidor.

## YouTube

La tarea ejecuta: abrir YouTube, Buscar, escribir el canal, Enter, primer canal,
**Videos** y primer vídeo. Los retardos son cancelables. El perfil de
coordenadas 1080×2400 está en `src/services/task_service.py`; adapta sus cuatro
coordenadas antes de usar dispositivos con otra resolución.
