# 🚀 BotVistas - Servidor PC y Panel de Control

Panel de control de escritorio y servidor centralizado en tiempo real desarrollado en **Python**, **FastAPI**, **WebSockets** y **PySide6 (Qt)** para la administración, supervisión y orquestación de tareas de automatización en múltiples dispositivos Android conectados mediante red local Wi-Fi/LAN.

---

## 🏗️ Arquitectura del Proyecto

```
pc/
├── src/
│   ├── core/                        # Núcleo del sistema y configuración
│   │   ├── __init__.py
│   │   ├── config.py                # Configuración global, detección de IP LAN
│   │   ├── events.py                # EventBridge con Señales Qt (Thread-Safe)
│   │   └── logger.py                # Sistema de logging integrado con la interfaz
│   │
│   ├── models/                      # Modelos de datos y esquemas Pydantic
│   │   ├── __init__.py
│   │   ├── device.py                # Modelo de dispositivo y estados (Connected, Running, etc.)
│   │   ├── task.py                  # Modelo de configuración de tareas (YouTube/TikTok)
│   │   └── ws_messages.py           # Protocolo de mensajería WebSocket (PC ↔ Android)
│   │
│   ├── server/                      # Servidor FastAPI & WebSocket
│   │   ├── __init__.py
│   │   ├── app.py                   # Instancia FastAPI, CORS y endpoints
│   │   ├── ws_manager.py            # Gestor de conexiones WebSocket activas
│   │   ├── server_thread.py         # Hilo background para ejecutar Uvicorn
│   │   └── routes/                  # Rutas REST API
│   │       ├── __init__.py
│   │       ├── devices.py           # API de consulta y registro de dispositivos
│   │       └── tasks.py             # API de control de tareas
│   │
│   ├── services/                    # Lógica de negocio
│   │   ├── __init__.py
│   │   ├── device_service.py        # Registro de dispositivos y monitoreo
│   │   └── task_service.py          # Orquestación y envío de comandos a dispositivos
│   │
│   ├── ui/                          # Interfaz Gráfica de Usuario (PySide6)
│   │   ├── __init__.py
│   │   ├── main_window.py           # Ventana principal
│   │   ├── components/              # Widgets modulares
│   │   │   ├── __init__.py
│   │   │   ├── server_status.py     # Barra superior con IP LAN, estado y conexiones
│   │   │   ├── device_table.py      # Tabla interactiva con badges y selección
│   │   │   ├── task_panel.py        # Panel de configuración y despacho de tareas
│   │   │   └── log_viewer.py        # Consola de logs en tiempo real
│   │   └── styles/                  # Estilos y temas
│   │       ├── __init__.py
│   │       └── theme.py             # Tema oscuro moderno (QSS)
│   │
│   └── main.py                      # Punto de entrada de la aplicación
│
├── tests/                           # Herramientas de prueba y simulación
│   ├── __init__.py
│   └── simulate_device.py           # Simulador de cliente Android para pruebas
│
├── requirements.txt                 # Dependencias del proyecto
├── .gitignore                       # Filtros de control de versiones
└── README.md                        # Documentación técnica
```

---

## ⚡ Requisitos y Dependencias

- **Python**: 3.10 o superior (compatible con Python 3.14)
- **Bibliotecas**:
  - `fastapi`
  - `uvicorn[standard]`
  - `pydantic`
  - `PySide6`
  - `websockets`

Para instalar las dependencias en el entorno virtual:
```bash
.\venv\Scripts\pip install -r requirements.txt
```

---

## ▶️ Ejecución de la Aplicación

Para iniciar el panel de control y el servidor local:

```bash
.\venv\Scripts\python src/main.py
```

Al iniciar:
1. Detecta automáticamente la **IP local de tu red Wi-Fi/LAN** (ej. `192.168.1.X`).
2. Inicia el servidor **FastAPI / WebSocket** en segundo plano en el puerto `8000`.
3. Despliega la interfaz moderna de **PySide6**.

---

## 📡 Protocolo de Comunicación WebSocket (PC ↔ Android)

Endpoint de conexión para cada teléfono Android:
```
ws://<IP_DEL_PC>:8000/ws/<DEVICE_ID>
```

### 1. Registro del Dispositivo (Android ➔ PC)
```json
{
  "type": "REGISTER",
  "device_id": "DEVICE_UUID_123",
  "payload": {
    "name": "Samsung Galaxy S21",
    "ip_address": "192.168.1.45",
    "battery_level": 90,
    "app_version": "1.0.0"
  }
}
```

### 2. Heartbeat Periódico (Android ➔ PC)
```json
{
  "type": "HEARTBEAT",
  "device_id": "DEVICE_UUID_123",
  "payload": {
    "battery_level": 88
  }
}
```

### 3. Iniciar Tarea (PC ➔ Android)
```json
{
  "type": "TASK_START",
  "task_id": "task_abc123",
  "payload": {
    "platform": "youtube",
    "target_profile": "@MrBeast",
    "duration_per_video_seconds": 180
  }
}
```

### 4. Detener Tarea (PC ➔ Android)
```json
{
  "type": "TASK_STOP",
  "task_id": "task_abc123",
  "payload": {
    "reason": "Manual stop requested from PC panel"
  }
}
```

### 5. Estado y Logs (Android ➔ PC)
```json
{
  "type": "TASK_STATUS",
  "device_id": "DEVICE_UUID_123",
  "payload": {
    "status": "running",
    "task_id": "task_abc123"
  }
}
```

---

## 🧪 Cómo Probar la Comunicación

Puedes simular dispositivos Android conectados ejecutando el simulador incluido en otra terminal mientras la aplicación de PC está abierta:

```bash
# Simular dispositivo 1
.\venv\Scripts\python tests/simulate_device.py DEV-001 "Xiaomi Redmi Note 10"

# Simular dispositivo 2
.\venv\Scripts\python tests/simulate_device.py DEV-002 "Samsung Galaxy A52"
```

Los dispositivos aparecerán inmediatamente en tiempo real en la tabla del panel PC, reportarán su batería y podrás asignarles tareas y detenerlas.
