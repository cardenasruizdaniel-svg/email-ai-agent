# 🚀 GUÍA MAESTRA DE INSTALACIÓN TURN-KEY - EMAIL AI AGENT

Esta guía consolida los **4 métodos de instalación llave en mano (Turn-key)** para desplegar el **Agente Autónomo de Gestión Inteligente de Correos (`email-ai-agent`)** en cualquier entorno (Linux, Docker, Servidor en la Nube o Windows).

---

## ⚡ OPCIÓN 1: Instalación 1-Comando en Linux (Ubuntu / Debian / RHEL / CentOS / Fedora)

Esta opción realiza **todo de forma automática** en tu servidor Linux (instala dependencias, crea la base de datos PostgreSQL, instala Python, configura el entorno virtual y activa el servicio systemd 24/7 en segundo plano):

```bash
cd email-ai-agent
chmod +x setup_linux.sh
./setup_linux.sh
```

El script finalizará mostrando la dirección IP de tu servidor y la URL del Dashboard:
👉 **`http://TU_IP_LINUX:8005`**

---

## 🐳 OPCIÓN 2: Despliegue con Docker Compose + PostgreSQL (Cualquier Sistema Operativo)

Para servidores que tengan instalado Docker y Docker Compose (Linux, Windows Server o macOS):

```bash
cd email-ai-agent
docker-compose -f docker-compose.postgres.yml up -d --build
```

Esto levantará automáticamente en segundo plano:
- Contenedor de la Base de Datos **PostgreSQL 15**.
- Contenedor de la Aplicación **FastAPI + Dashboard Web** en el puerto `8005`.

---

## ☁️ OPCIÓN 3: Despliegue 100% Gratuito en la Nube (Render.com)

Ideal para computadores restringidos o cuando no se desea dejar equipos locales encendidos:

1. Subir la carpeta del proyecto a **GitHub**.
2. En **[Render.com](https://render.com)** crear un **New Web Service** conectado al repositorio.
3. Configurar:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python -m uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
4. Render te entregará tu enlace HTTPS seguro (ej: `https://agente-correo-ia.onrender.com`).

---

## 🖥️ OPCIÓN 4: Ejecución Local en Windows

Para desarrollo o servidor local Windows:

```powershell
cd D:\PROGRAMAS\DEACorreos\email-ai-agent
python -m pip install -r requirements.txt
python -m uvicorn backend.main:app --port 8005
```

Acceder desde tu navegador a: **`http://localhost:8005`**

---

## ⚙️ CONFIGURACIÓN DINÁMICA DE CUALQUIER CORREO E IA

Independientemente del método de instalación que elijas, una vez abierto el Dashboard Web en el puerto `8005` (o en la URL de Render):

1. Ve a la pestaña **`⚙️ Configuración del Sistema`**.
2. Selecciona tu proveedor de correo (`Gmail`, `Outlook / Office 365`, `Yahoo` o `Personalizado`).
3. Ingresa la cuenta de correo y contraseña (o clave de aplicación de 16 caracteres).
4. Elige el motor de IA (**Google Gemini API Gratuita $0** o **Motor Heurístico $0**).
5. Haz clic en **`Guardar Configuración e Iniciar Sincronización`**.
